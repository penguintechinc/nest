//! `nest-gating`: fail-safe two-layer category gate shared by Nest's Rust
//! services (`svc-streaming` and friends). Mirrors the semantics of
//! `apps/api/gating.py` — a PostHog rollout flag (layer 1) gated behind a
//! license-tier floor (layer 2) — so the Python and Rust strangler paths stay
//! consistent while svc-streaming migrates off the Quart API.
//!
//! Both layers degrade gracefully rather than ever raising into the caller's
//! request/reconcile path: [`Gate::evaluate`] never returns `Err` and never
//! panics.

use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use anyhow::Result;
use tracing::{info, warn};

#[cfg(feature = "posthog-client")]
mod live;

#[cfg(feature = "posthog-client")]
pub use live::{LicenseTierProvider, PostHogFlagProvider};

/// Machine-readable code returned when layer 1 (the rollout flag) denies.
pub const FLAG_DISABLED_CODE: &str = "nest.gate.flag_disabled";
/// Machine-readable code returned when layer 2 (the license tier) denies.
pub const TIER_REQUIRED_CODE: &str = "nest.gate.tier_required";

/// Default TTL for a cached flag value before it's treated as stale. Bounds
/// how long a gate keeps serving a last-known value once the flag backend
/// goes unreachable, rather than trusting it indefinitely.
const DEFAULT_CACHE_TTL: Duration = Duration::from_secs(300);

/// Outcome of a category gate check: whether `category` is allowed for
/// `tenant`, plus a machine-readable `code` and human-readable `message`
/// to surface to the caller when it isn't. `code`/`message` are empty when
/// `allowed` is `true`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateDecision {
    pub allowed: bool,
    pub code: String,
    pub message: String,
}

impl GateDecision {
    fn allow() -> Self {
        Self {
            allowed: true,
            code: String::new(),
            message: String::new(),
        }
    }

    fn deny(code: &str, message: impl Into<String>) -> Self {
        Self {
            allowed: false,
            code: code.to_string(),
            message: message.into(),
        }
    }
}

/// Resolves whether a PostHog-style rollout flag is enabled for a tenant.
/// Implemented by [`PostHogFlagProvider`] in production; tests supply a fake.
/// Any backend failure (network, auth, bad response) MUST return `Err` — the
/// fail-safe fallback to a cached value is [`Gate`]'s job, not the
/// provider's, mirroring Python's `_flag_or_cached`.
pub trait FlagProvider: Send + Sync {
    fn flag_enabled(&self, flag_key: &str, tenant: &str) -> Result<bool>;
}

/// Resolves a tenant's license tier (`"free"`, `"professional"`/`"pro"`, or
/// `"enterprise"`). Implemented by [`LicenseTierProvider`] in production;
/// tests supply a fake. A backend failure MUST return `Err` — [`Gate`] fails
/// safe by denying rather than guessing an entitlement.
pub trait TierProvider: Send + Sync {
    fn tier(&self, tenant: &str) -> Result<String>;
}

/// Tier ranking for entitlement comparison — mirrors `_TIER_RANK` in
/// `apps/api/gating.py`. `"pro"` is an alias for `"professional"`; an
/// unrecognized tier ranks as `"free"` (the most restrictive known tier),
/// never as something more privileged.
fn tier_rank(tier: &str) -> u8 {
    match tier {
        "professional" | "pro" => 1,
        "enterprise" => 2,
        _ => 0,
    }
}

/// Phase 0 entitlement floor per category — mirrors `_MIN_TIER`. `None` means
/// the category has no tier floor (Free always allowed, subject to layer 1).
fn min_tier(category: &str) -> Option<&'static str> {
    match category {
        "analytics" => Some("professional"),
        _ => None,
    }
}

/// A single cached flag value plus the instant it was captured, so a stale
/// entry (older than the configured TTL) is never trusted indefinitely.
struct CacheEntry {
    value: bool,
    cached_at: Instant,
}

/// Last-known flag values, keyed by `(flag_key, tenant)`, used for graceful
/// degradation when the flag backend is unreachable. Mirrors `_flag_cache` in
/// `apps/api/gating.py`, plus a TTL so an unreachable backend doesn't let a
/// value drift arbitrarily stale.
#[derive(Default)]
struct FlagCache {
    entries: Mutex<HashMap<(String, String), CacheEntry>>,
}

impl FlagCache {
    /// Records the latest known-good value for `key`. A poisoned mutex (a
    /// prior panic while holding the lock) is recovered rather than
    /// propagated — the cache is best-effort, never a reason to panic.
    fn record(&self, key: (String, String), value: bool) {
        let mut entries = self
            .entries
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        entries.insert(
            key,
            CacheEntry {
                value,
                cached_at: Instant::now(),
            },
        );
    }

    /// Returns the cached value for `key` if present and younger than `ttl`.
    fn last_known(&self, key: &(String, String), ttl: Duration) -> Option<bool> {
        let entries = self
            .entries
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        entries
            .get(key)
            .filter(|entry| entry.cached_at.elapsed() <= ttl)
            .map(|entry| entry.value)
    }
}

/// Two-layer category gate: a rollout flag (layer 1) gated behind a license
/// tier floor (layer 2). [`Gate::evaluate`] never returns `Err` and never
/// panics — any provider failure degrades to a deny decision (flag: falls
/// back to the last-known-cached value, else OFF; tier: denies outright,
/// since an unconfirmed entitlement can't be trusted) rather than ever
/// breaking the caller's request/reconcile path.
pub struct Gate {
    flags: Box<dyn FlagProvider>,
    tiers: Box<dyn TierProvider>,
    cache: FlagCache,
    cache_ttl: Duration,
}

impl Gate {
    /// Builds a gate from a flag provider and a tier provider. Use
    /// [`Gate::with_cache_ttl`] to override the default 300s cache TTL.
    pub fn new(flags: impl FlagProvider + 'static, tiers: impl TierProvider + 'static) -> Self {
        Self {
            flags: Box::new(flags),
            tiers: Box::new(tiers),
            cache: FlagCache::default(),
            cache_ttl: DEFAULT_CACHE_TTL,
        }
    }

    /// Overrides the last-known-flag-value cache TTL (default 300s).
    #[must_use]
    pub fn with_cache_ttl(mut self, ttl: Duration) -> Self {
        self.cache_ttl = ttl;
        self
    }

    /// Runs the two-layer gate for `category`/`tenant`. Never returns `Err`,
    /// never panics: see the type-level doc for the fail-safe fallback rules.
    pub fn evaluate(&self, category: &str, tenant: &str) -> GateDecision {
        let flag_key = format!("nest.{category}");
        if !self.flag_or_cached(&flag_key, tenant) {
            info!(
                category,
                tenant,
                code = FLAG_DISABLED_CODE,
                "category gate denied"
            );
            return GateDecision::deny(
                FLAG_DISABLED_CODE,
                format!("The '{category}' module is not enabled in this environment."),
            );
        }

        let Some(required) = min_tier(category) else {
            return GateDecision::allow();
        };

        let tier = match self.tiers.tier(tenant) {
            Ok(tier) => tier,
            Err(err) => {
                warn!(
                    category,
                    tenant,
                    error = %err,
                    "tier provider unavailable; denying category fail-safe"
                );
                return GateDecision::deny(
                    TIER_REQUIRED_CODE,
                    format!("The '{category}' module requires the {required} tier."),
                );
            }
        };

        if tier_rank(&tier) < tier_rank(required) {
            info!(
                category,
                tenant,
                tier,
                required,
                code = TIER_REQUIRED_CODE,
                "category gate denied"
            );
            return GateDecision::deny(
                TIER_REQUIRED_CODE,
                format!("The '{category}' module requires the {required} tier."),
            );
        }

        GateDecision::allow()
    }

    /// Evaluates `flag_key` for `tenant`, falling back to the last-known
    /// cached value (else `false`) if the provider errors. Mirrors
    /// `_flag_or_cached` in `apps/api/gating.py`.
    fn flag_or_cached(&self, flag_key: &str, tenant: &str) -> bool {
        let key = (flag_key.to_string(), tenant.to_string());
        match self.flags.flag_enabled(flag_key, tenant) {
            Ok(value) => {
                self.cache.record(key, value);
                value
            }
            Err(err) => {
                let cached = self.cache.last_known(&key, self.cache_ttl).unwrap_or(false);
                warn!(
                    flag_key,
                    tenant,
                    cached,
                    error = %err,
                    "flag backend unreachable; falling back to cached value"
                );
                cached
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    /// Fake [`FlagProvider`] that returns `Ok(ok_value)` for a fixed number
    /// of calls, then `Err` on every call after that — models a flag backend
    /// that is up for a while and then goes unreachable.
    struct FakeFlagProvider {
        ok_value: bool,
        ok_calls_remaining: AtomicUsize,
    }

    impl FakeFlagProvider {
        fn always(value: bool) -> Self {
            Self {
                ok_value: value,
                ok_calls_remaining: AtomicUsize::new(usize::MAX),
            }
        }

        fn always_err() -> Self {
            Self {
                ok_value: false,
                ok_calls_remaining: AtomicUsize::new(0),
            }
        }

        fn ok_once_then_err(value: bool) -> Self {
            Self {
                ok_value: value,
                ok_calls_remaining: AtomicUsize::new(1),
            }
        }
    }

    impl FlagProvider for FakeFlagProvider {
        fn flag_enabled(&self, _flag_key: &str, _tenant: &str) -> Result<bool> {
            let had_call_left = self
                .ok_calls_remaining
                .fetch_update(Ordering::SeqCst, Ordering::SeqCst, |remaining| {
                    remaining.checked_sub(1)
                })
                .is_ok();
            if had_call_left {
                Ok(self.ok_value)
            } else {
                Err(anyhow::anyhow!("flag backend unreachable"))
            }
        }
    }

    /// Fake [`TierProvider`] returning a fixed tier, or `Err` when `None`.
    struct FakeTierProvider(Option<&'static str>);

    impl TierProvider for FakeTierProvider {
        fn tier(&self, _tenant: &str) -> Result<String> {
            self.0
                .map(str::to_string)
                .ok_or_else(|| anyhow::anyhow!("tier backend unreachable"))
        }
    }

    #[test]
    fn flag_on_allows_free_category() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("free")),
        );
        let decision = gate.evaluate("streaming", "tenant-a");
        assert!(decision.allowed);
        assert_eq!(decision.code, "");
    }

    #[test]
    fn flag_off_denies_with_flag_disabled_code() {
        let gate = Gate::new(
            FakeFlagProvider::always(false),
            FakeTierProvider(Some("free")),
        );
        let decision = gate.evaluate("streaming", "tenant-a");
        assert!(!decision.allowed);
        assert_eq!(decision.code, FLAG_DISABLED_CODE);
    }

    #[test]
    fn flag_provider_error_with_no_cache_denies_fail_safe_without_panicking() {
        let gate = Gate::new(
            FakeFlagProvider::always_err(),
            FakeTierProvider(Some("free")),
        );
        let decision = gate.evaluate("streaming", "tenant-a");
        assert!(!decision.allowed);
        assert_eq!(decision.code, FLAG_DISABLED_CODE);
    }

    #[test]
    fn flag_provider_error_falls_back_to_last_known_cached_on_value() {
        let gate = Gate::new(
            FakeFlagProvider::ok_once_then_err(true),
            FakeTierProvider(Some("free")),
        );
        let first = gate.evaluate("streaming", "tenant-a");
        assert!(
            first.allowed,
            "first call should succeed and populate the cache"
        );

        let second = gate.evaluate("streaming", "tenant-a");
        assert!(
            second.allowed,
            "provider error should fall back to the cached ON value, not deny"
        );
    }

    #[test]
    fn stale_cache_entry_beyond_ttl_denies_fail_safe() {
        let gate = Gate::new(
            FakeFlagProvider::ok_once_then_err(true),
            FakeTierProvider(Some("free")),
        )
        .with_cache_ttl(Duration::from_millis(0));
        let first = gate.evaluate("streaming", "tenant-a");
        assert!(first.allowed);

        std::thread::sleep(Duration::from_millis(5));
        let second = gate.evaluate("streaming", "tenant-a");
        assert!(
            !second.allowed,
            "a cache entry older than ttl=0 must be treated as stale, not trusted"
        );
        assert_eq!(second.code, FLAG_DISABLED_CODE);
    }

    #[test]
    fn analytics_at_free_tier_denies_with_tier_required_code() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("free")),
        );
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(!decision.allowed);
        assert_eq!(decision.code, TIER_REQUIRED_CODE);
    }

    #[test]
    fn analytics_at_professional_tier_is_allowed() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("professional")),
        );
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(decision.allowed);
    }

    #[test]
    fn analytics_at_pro_alias_is_allowed() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("pro")),
        );
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(decision.allowed);
    }

    #[test]
    fn analytics_at_enterprise_tier_is_allowed() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("enterprise")),
        );
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(decision.allowed);
    }

    #[test]
    fn unrecognized_tier_ranks_as_free_and_denies_analytics() {
        let gate = Gate::new(
            FakeFlagProvider::always(true),
            FakeTierProvider(Some("mystery-tier")),
        );
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(!decision.allowed);
        assert_eq!(decision.code, TIER_REQUIRED_CODE);
    }

    #[test]
    fn tier_provider_error_denies_fail_safe_without_panicking() {
        let gate = Gate::new(FakeFlagProvider::always(true), FakeTierProvider(None));
        let decision = gate.evaluate("analytics", "tenant-a");
        assert!(!decision.allowed);
        assert_eq!(decision.code, TIER_REQUIRED_CODE);
    }

    #[test]
    fn cache_is_scoped_per_flag_key_and_tenant() {
        let gate = Gate::new(
            FakeFlagProvider::ok_once_then_err(true),
            FakeTierProvider(Some("free")),
        );
        // Consumes the fake provider's single Ok call for `streaming`.
        let streaming = gate.evaluate("streaming", "tenant-a");
        assert!(streaming.allowed);

        // A different category (distinct flag key) never populated the
        // cache, and the fake provider is now exhausted, so this must fail
        // safe to OFF rather than reusing the `streaming` cache entry.
        let other = gate.evaluate("other-category", "tenant-a");
        assert!(!other.allowed);
        assert_eq!(other.code, FLAG_DISABLED_CODE);
    }
}
