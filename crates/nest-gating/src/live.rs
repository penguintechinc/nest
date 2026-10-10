//! Default, network-backed [`FlagProvider`]/[`TierProvider`] implementations.
//! Gated behind the `posthog-client` cargo feature so `cargo test -p
//! nest-gating` never requires network access and consumers supplying their
//! own providers never pull in an HTTP client.

use std::env;
use std::time::Duration;

use anyhow::{Context, Result};
use serde::Deserialize;

use crate::{FlagProvider, TierProvider};

/// Request timeout for both default providers — a gate check must never
/// hang the caller indefinitely when the backend is slow, only fail fast
/// into the existing fail-safe fallback.
const REQUEST_TIMEOUT: Duration = Duration::from_secs(5);

fn build_agent() -> ureq::Agent {
    let config = ureq::Agent::config_builder()
        .timeout_global(Some(REQUEST_TIMEOUT))
        .build();
    config.into()
}

/// Default production [`FlagProvider`]: calls the PostHog `/decide` API,
/// configured via the `POSTHOG_API_KEY`/`POSTHOG_HOST` env vars per the
/// `integrating-license-server` skill. Any failure (missing env var,
/// network error, bad response) returns `Err` — [`crate::Gate`] owns the
/// fail-safe fallback to a cached value, mirroring Python's
/// `_flag_or_cached`.
pub struct PostHogFlagProvider {
    agent: ureq::Agent,
    api_key: String,
    host: String,
}

impl PostHogFlagProvider {
    /// Builds a provider from `POSTHOG_API_KEY` (required) and
    /// `POSTHOG_HOST` (defaults to `https://us.i.posthog.com`).
    pub fn from_env() -> Result<Self> {
        let api_key = env::var("POSTHOG_API_KEY").context("POSTHOG_API_KEY is not set")?;
        let host =
            env::var("POSTHOG_HOST").unwrap_or_else(|_| "https://us.i.posthog.com".to_string());
        Ok(Self {
            agent: build_agent(),
            api_key,
            host,
        })
    }
}

#[derive(Deserialize, Default)]
struct DecideResponse {
    #[serde(default, rename = "featureFlags")]
    feature_flags: std::collections::HashMap<String, serde_json::Value>,
}

impl FlagProvider for PostHogFlagProvider {
    fn flag_enabled(&self, flag_key: &str, tenant: &str) -> Result<bool> {
        let url = format!("{}/decide/?v=3", self.host.trim_end_matches('/'));
        let request_body = serde_json::json!({
            "api_key": self.api_key,
            "distinct_id": tenant,
        });
        let decoded: DecideResponse = self
            .agent
            .post(&url)
            .send_json(&request_body)
            .context("PostHog /decide request failed")?
            .body_mut()
            .read_json()
            .context("PostHog /decide response was not valid JSON")?;
        let enabled = decoded
            .feature_flags
            .get(flag_key)
            .is_some_and(|value| value.as_bool().unwrap_or(!value.is_null()));
        Ok(enabled)
    }
}

/// Default production [`TierProvider`]: calls the license server configured
/// via `LICENSE_SERVER_URL` (defaults to `https://license.penguintech.io`)
/// and an optional `LICENSE_API_KEY` bearer token.
pub struct LicenseTierProvider {
    agent: ureq::Agent,
    base_url: String,
    api_key: Option<String>,
}

impl LicenseTierProvider {
    /// Builds a provider from `LICENSE_SERVER_URL` (optional, defaults to
    /// `https://license.penguintech.io`) and `LICENSE_API_KEY` (optional).
    pub fn from_env() -> Result<Self> {
        let base_url = env::var("LICENSE_SERVER_URL")
            .unwrap_or_else(|_| "https://license.penguintech.io".to_string());
        let api_key = env::var("LICENSE_API_KEY").ok();
        Ok(Self {
            agent: build_agent(),
            base_url,
            api_key,
        })
    }
}

#[derive(Deserialize)]
struct TierResponse {
    tier: String,
}

impl TierProvider for LicenseTierProvider {
    fn tier(&self, tenant: &str) -> Result<String> {
        let url = format!(
            "{}/api/v1/tenants/{tenant}/tier",
            self.base_url.trim_end_matches('/')
        );
        let mut request = self.agent.get(&url);
        if let Some(api_key) = &self.api_key {
            request = request.header("Authorization", format!("Bearer {api_key}"));
        }
        let decoded: TierResponse = request
            .call()
            .context("license server tier request failed")?
            .body_mut()
            .read_json()
            .context("license server tier response was not valid JSON")?;
        Ok(decoded.tier)
    }
}
