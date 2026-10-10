# Phase 1: `svc-streaming` (Rust) — Valkey Streams + strangler-fig — Design

**Date:** 2026-10-10
**Status:** Design (approved in chat; building)
**Author:** justin@penguintech.io (with Claude)
**Umbrella design:** `docs/superpowers/specs/2026-09-22-modular-categories-design.md` · **Tracking:** issue #37
**Scope:** The first Rust `svc-*` module of the modular re-architecture. One vertical slice, reconcile-only.

---

## 1. Problem & Goal

Continue the Go→Rust phase-out (made urgent by Go **stdlib** CVEs — GO-2026-6605/6607/6608/6613 + `x/net` — fixed only in go1.26.9 while the org standard is Go 1.25.x, effectively security-EOL). Phase 1 proves the Rust module pattern end-to-end on the smallest clean slice and yields two reusable foundations: the **Valkey reconcile** logic (reused by `svc-database`'s keyvalue later) and the **Rust PostHog/license gating crate** (reused by every later module).

**Deliverable:** a Rust `svc-streaming` service that owns a **new** `valkey-stream` engine under `category=streaming`, reconcile-only, gated, coexisting with the untouched Go controller via a strangler-fig type-ownership flag.

---

## 2. Scope

**In Phase 1:**

- New engine **`type: valkey-stream`** in `category: streaming` (SSOT addition). It is net-new — the Go controller has no path for it, so no reconcile conflict.
- Rust `svc-streaming` binary: a **kube-rs controller** reconciling `valkey-stream` DataResources into a stream-profiled Valkey StatefulSet (modeled on the Go `keyvalue_reconciler.go`), **reconcile-only** (clients connect direct to the Valkey Service; no proxy — db-proxy's RESP path was never implemented).
- The net-new **Rust gating crate** (PostHog flag `nest.streaming` + license tier, fail-safe) enforced at reconcile.
- **Strangler ownership:** a `rust-owned` type set; the Go controller skips types in it (surgical change); Phase 1 set = `{valkey-stream}`.
- Rust plumbing: multi-stage Dockerfile (rootless), Helm chart, `cargo` CI (build/test/clippy/deny), `tracing`+OTel, Prometheus `/metrics`.

**Offered but deferred (fast-follow, NOT Phase 1 delivery):** `type: kafka` Rust reconciler (ported from Go `kafka_reconciler.go`/Strimzi). Until then, the Go controller keeps reconciling `kafka`; the full per-category flip happens when the Rust kafka reconciler ships.

**Out of scope:** any data-path/RESP proxy; migrating existing `keyvalue` (database category) to Rust (that's `svc-database`); the other svc-\* modules.

---

## 3. Architecture

```
DataResource{category=streaming, type=valkey-stream}
      │  (admission: CRD CEL validates type∈category — Phase 0 contract)
      ▼
 svc-streaming (Rust, kube-rs)         Go k8s-controller
   watch category=streaming              dispatch switch
   AND type ∈ rust-owned                   SKIP types ∈ rust-owned  ← strangler
      │                                     (keeps kafka for now)
      ├─ gate: nest-gating crate (PostHog nest.streaming + license tier; fail-safe)
      │     deny → status Blocked + condition, NO provisioning
      ▼
   reconcile (stream-profiled Valkey):
     Secret(auth) · ConfigMap(valkey.conf) · headless Service :6379 · StatefulSet(valkey:8-bookworm, PVC) · PDB
      ▼
   status: phase + conditions + endpoint (<svc>.<ns>.svc:6379)
      ▼
   client connects DIRECT (RESP: XADD/XREAD/XREADGROUP)
```

### 3.1 Crates / binaries (workspace)

- **`crates/nest-gating`** (lib) — `evaluate_category_gate(category, tier, tenant) -> GateDecision`. Layer 1 PostHog flag `nest.{category}` (default OFF; on-disk + in-mem cache, TTL refresh; backend error → last-known-cached else OFF; never panics). Layer 2 license tier (reuse the existing license entitlement; tier from the DataResource's tenant/claims context). Returns `allowed/code/message`. Mirrors the Python `gating.py` semantics.
- **`services/svc-streaming`** (bin) — kube-rs controller + minimal Axum server (`/healthz`, `/readyz`, `:9090/metrics`) + OTel init.

### 3.2 Reconciler (`valkey-stream`)

Ports the object set from `services/k8s-controller/controllers/keyvalue_reconciler.go`, stream-profiled:

- **Secret** — generated auth password.
- **ConfigMap `valkey.conf`** — `appendonly yes`; **`maxmemory-policy noeviction`** (streams must not be evicted); `maxmemory` unset or generous; optional default stream `MAXLEN`/retention guidance as annotations (documented namespace). (Differs from keyvalue, which uses 80%-maxmemory eviction.)
- **headless Service** — ClusterIP None, port 6379.
- **StatefulSet** — `docker.io/valkey/valkey:8-bookworm`, `valkey-server /etc/valkey/valkey.conf`; busybox init writes `replicaof`/`masterauth` for pod ordinals >0; replicas = `Spec.Replicas.Write.Default` (default 1); PVC RWO sized from `Spec.Size.Storage` (default 1Gi), storageClass `nest-rbd`.
- **PodDisruptionBudget** — minAvailable 1 when replicas>1.
- **Status** — `phase` (Pending→Provisioning→Ready / Blocked / Failed) + `conditions` (`Validated`, `Gated`, `Ready`) + `endpoint`.
- Owner references on all created objects; kube-rs `Controller` with owned-object watches; requeue with backoff on transient errors; idempotent apply (server-side apply / create-or-patch).

### 3.3 Strangler ownership

- `rust-owned` = a set of `spec.type` values claimed by Rust services, sourced from a ConfigMap (`nest-rust-owned-types`) or env, read by both controllers. **Phase 1: `{valkey-stream}`.**
- **Go controller change (surgical):** before the dispatch `switch`, if `dr.Spec.Type ∈ rust-owned`, return without error (no-op/skip) so it never hits the `default: unsupported type`. This is the only Go edit in Phase 1.
- **svc-streaming:** its controller stream filters to `category=streaming AND type ∈ rust-owned` (so it ignores `kafka` until kafka is added to the set + its Rust reconciler ships).
- Rollback: remove `valkey-stream` from `rust-owned` (and scale down svc-streaming) → the type is simply unserved (it's net-new, so nothing regresses).

### 3.4 SSOT / contract update

- `apis/v1/categories.yaml`: `streaming: [kafka, valkey-stream]`.
- Flows to the Go embed, Python bundled copy, and CRD CEL via the Phase-0 drift tests; CRD `ResourceType` enum gains `valkey-stream`. (Small edits; drift tests enforce consistency.)

---

## 4. Stack & conventions (PenguinTech Rust)

- Rust latest stable; `tokio` async; **kube-rs** (`kube`, `k8s-openapi`) for the controller; **Axum** for the health/metrics surface; `tracing` + `opentelemetry` + OTLP exporter (env-configured endpoint); `serde`; `thiserror`/`anyhow` at the edges. `Result<T,E>` everywhere — no `.unwrap()`/`.expect()` outside tests. `cargo clippy -D warnings` + `cargo deny` (licenses + advisories) in CI.
- **Multi-stage Dockerfile:** `rust:1-bookworm` builder → `debian:bookworm-slim` runtime, non-root `USER`, pinned base digests, multi-arch (amd64/arm64).
- **Helm chart `k8s/helm/nest-svc-streaming`:** controller Deployment (1–2 replicas, **leader election**), RBAC (DataResource get/list/watch/update-status + Secret/ConfigMap/Service/StatefulSet/PDB manage), ServiceMonitor, default-deny CiliumNetworkPolicy + egress allowlist (kube-apiserver, OTLP, PostHog/license, DNS), PodSecurityAdmission `restricted`, SPIFFE-ready.
- **CI:** a `rust-test` job (cargo build/test/clippy/`cargo deny`) added to `ci.yml`; `trivy fs` already covers Cargo.lock. **Note:** Rust has no penguin-logging crate yet → use `tracing` + OTel (per `testing.md` Rust exception).

---

## 5. Error handling & resilience

- Gate fail-safe: PostHog/license unreachable → cached/OFF; `nest-gating` never panics, returns a decision.
- Reconcile: typed errors; transient → kube-rs requeue (exponential backoff); permanent (e.g. invalid spec) → `phase=Failed` + condition, no requeue storm.
- Gate deny → `phase=Blocked` + `Gated=False` condition; re-evaluated on requeue (so turning the flag on unblocks).
- Graceful shutdown (SIGTERM → drain controller), leader-election lease release.
- No secrets/PII in logs/spans (tracing auto-fields reviewed); tenant id only.

---

## 6. Testing

- **`nest-gating` unit tests:** flag on/off, tier allow/deny (streaming = Free so tier always allows; include an analytics-style case to prove the tier path), backend-error → cached/OFF fail-safe, never-seen → OFF. Mock the flag backend behind a trait seam (like the Python `_flag_enabled` seam).
- **Reconciler unit tests:** construct a `valkey-stream` DataResource, run the reconcile against a **fake kube client** (`kube::Client` test double / `tower-test`), assert the emitted objects (StatefulSet image/replicas/PVC size, ConfigMap `noeviction`, Service headless :6379, Secret present, owner refs) and status transitions. Edge cases: default size/replicas, gate-denied → Blocked (no objects), type not owned → ignored.
- **Contract test:** `valkey-stream` ∈ streaming in `categories.yaml`; CRD CEL accepts `{streaming, valkey-stream}` and rejects `{database, valkey-stream}` (extend the Phase-0 drift test).
- **Go-side test:** the Go controller skips a `valkey-stream` DataResource (no `unsupported type` error) — fake-client test in the controller package.
- Coverage ≥90% (cargo-llvm-cov) on `nest-gating` + `svc-streaming`. `cargo clippy -D warnings`, `cargo fmt --check` clean.

---

## 7. Rollout (strangler)

1. Land `svc-streaming` + `nest-gating` + the SSOT/CRD update + the Go skip-change (one PR, or a small stack).
2. Deploy `svc-streaming`; set `rust-owned={valkey-stream}` ConfigMap; Go controller skips it.
3. `nest.streaming` PostHog flag OFF by default → turn ON per environment once validated (flag-gated rollout per standard).
4. Kafka remains Go-reconciled; the Rust kafka reconciler + the per-category flip are a fast-follow (own spec/plan).

---

## 8. Known interim constraint (not solved by Phase 1)

Phase 1's PR targets `v1.2.x`, whose CI **govulncheck gate is currently red** from the Go stdlib CVEs in the _existing_ Go services (unchanged by Phase 1). So Phase 1 can be built and reviewed, but **merging it hits the same red Go gate** as PRs #27/#28/#29. Resolving that (Go 1.26.9 toolchain bump, a tracked govulncheck exception, or accepting it during the migration) is a **separate decision** (issue #37 / the parked gate question) and gates the _merge_, not the build. Phase 1 itself adds no Go CVE surface (it's Rust).

---

## 9. Open items (confirm at plan/build time)

1. Reuse vs fork the Valkey object templates — Phase 1 writes them in Rust fresh (no shared Go↔Rust codegen); `svc-database` later extracts a shared Rust `valkey` module from svc-streaming's reconciler.
2. License-tier source inside the controller (the Rust gating crate needs the tenant's tier) — via the license entitlement client keyed by tenant, cached; confirm the exact client/endpoint against `integrating-license-server` at build time.
3. Workspace layout — a top-level `Cargo.toml` workspace (`crates/nest-gating`, `services/svc-streaming`) vs per-service crates; pick at plan time to match any existing Rust layout (none exists yet — this is the first Rust in the repo).
