# Phase 1: svc-streaming (Rust) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. **Rust tasks are built by the `penguin-rust-dev` specialist and the single Go task by `penguin-go-dev`** — this plan pins the exact _what_ (field values, object set, gating semantics, SSOT edits); the specialist supplies idiomatic Rust (error types, module layout, kube-rs/Axum wiring) per `backend-rust.md` / the `building-rust-services` skill.

**Goal:** Ship the first Rust `svc-*` service — `svc-streaming` — owning a new `valkey-stream` engine under `category=streaming`, reconcile-only, gated by a net-new Rust PostHog/license crate, coexisting with the Go controller via a rust-owned type set.

**Architecture:** A Cargo workspace at repo root with `crates/nest-gating` (fail-safe PostHog-flag + license-tier gate) and `services/svc-streaming` (kube-rs controller reconciling a stream-profiled Valkey StatefulSet, ported from the Go `keyvalue_reconciler.go`). The Go `k8s-controller` skips types in a `NEST_RUST_OWNED_TYPES` set so `valkey-stream` is served only by Rust; `kafka` stays Go.

**Tech Stack:** Rust (stable, pinned via `rust-toolchain.toml`), tokio, kube-rs (`kube` + `k8s-openapi`), Axum, tracing + opentelemetry-otlp, serde; `cargo clippy -D warnings`, `cargo deny`, `cargo llvm-cov`.

**Spec:** `docs/superpowers/specs/2026-10-10-phase1-svc-streaming-design.md`

## Global Constraints

- **First Rust _service_ in the repo.** A non-service SDK crate exists at `pkg/sdk/rust` — **`exclude` it** from the new workspace (don't absorb/modify it).
- **No `.unwrap()`/`.expect()`/`panic!` outside `#[cfg(test)]`.** `Result<T,E>` everywhere; `cargo clippy -D warnings` + `cargo fmt --check` clean; `cargo deny check` (advisories + licenses) clean.
- **Dependency pinning:** exact versions in every `Cargo.toml` (no bare `*`/`^` for new deps — caret is allowed per Cargo norms but pin majors deliberately); commit `Cargo.lock`. Docker base images pinned by `@sha256:` digest. No `latest`.
- **Coverage ≥90%** (`cargo llvm-cov`) on `nest-gating` + `svc-streaming`.
- **Gate is fail-safe:** PostHog/license unreachable → last-known cached value, never-seen flag → OFF, **never panics**. Flag key `nest.{category}`. (Mirrors `apps/api/gating.py`.)
- **Status phase enum is fixed** (`apis/v1/dataresource_types.go:183`): Unknown/Pending/Provisioning/Ready/Degraded/Failed/Deleting — **no "Blocked"**. Gate-denied → `Pending` + a `Gated=False` condition.
- **Valkey object fidelity:** port `services/k8s-controller/controllers/keyvalue_reconciler.go` exactly, changing only the stream profile (`maxmemory-policy noeviction`, no forced `maxmemory`) and labels/category.
- **SSOT:** `apis/v1/categories.yaml` is the only hand-edited type→category map; the Go embed, `apps/api/categories.yaml` copy, and CRD CEL are drift-tested against it.
- **Telemetry:** `tracing` + OTLP (env `OTEL_EXPORTER_OTLP_ENDPOINT`), Prometheus `/metrics` on :9090. No secrets/PII in logs (tenant id only).
- **Rootless** container + K8s `securityContext` (runAsNonRoot, drop caps).

---

## File Structure

```
Cargo.toml                      # [workspace] members=[crates/*, services/svc-streaming], exclude=["pkg/sdk/rust"]
Cargo.lock                      # committed
rust-toolchain.toml             # pin channel = "1.<stable>"
deny.toml                       # cargo-deny: advisories + license allowlist (MIT/Apache-2.0/BSD/ISC)
crates/nest-gating/
  Cargo.toml
  src/lib.rs                    # GateDecision, evaluate_category_gate, FlagProvider trait seam, TierProvider, fail-safe cache
services/svc-streaming/
  Cargo.toml
  src/main.rs                   # tokio main: OTel init, Axum health/metrics, kube Controller, leader election, graceful shutdown
  src/crd.rs                    # Rust DataResource (kube CustomResource) mirroring apis/v1 fields used
  src/reconcile.rs              # valkey-stream reconciler: object builders + status
  src/gate.rs                   # adapts nest-gating to the controller (flag + tier for a DataResource)
  src/error.rs                  # typed errors (thiserror)
  Dockerfile                    # multi-stage rust->debian-slim, rootless
k8s/helm/nest-svc-streaming/    # Chart.yaml, values.yaml, templates/{deployment,serviceaccount,rbac,servicemonitor,networkpolicy,_helpers}.yaml
```

Modified (SSOT + strangler + CI):

```
apis/v1/categories.yaml                                   # streaming: [kafka, valkey-stream]
apps/api/categories.yaml                                  # bundled copy (drift-tested) — same edit
k8s/kustomize/base/crds/dataresource.yaml                 # CEL streaming clause: ['kafka','valkey-stream']
openapi/v1.yaml                                           # ResourceType enum: + valkey-stream
apis/v1/crd_cel_test.go                                   # (auto-covers via SSOT; add explicit valkey-stream∈streaming case)
apps/api/tests/test_categories_sync.py                    # (auto-covers; add valkey-stream mapping assertion)
services/k8s-controller/controllers/dataresource_controller.go  # skip NEST_RUST_OWNED_TYPES before dispatch (create+delete)
services/k8s-controller/controllers/controllers_test.go   # test: valkey-stream skipped, no error
k8s/.../nest-k8s-controller deployment                    # env NEST_RUST_OWNED_TYPES=valkey-stream (strangler toggle)
.github/workflows/ci.yml                                  # changes.rust filter + rust-test job + test-summary needs
```

---

## Task 1: Cargo workspace scaffold

**Files:** Create `Cargo.toml`, `rust-toolchain.toml`, `deny.toml`, update root `.gitignore` (add `/target`).

**Interfaces:** Produces the workspace that Tasks 2–5/8 build in.

- [ ] **Step 1:** Create root `Cargo.toml`:

```toml
[workspace]
resolver = "2"
members = ["crates/nest-gating", "services/svc-streaming"]
exclude = ["pkg/sdk/rust"]

[workspace.package]
edition = "2021"
license = "PROPRIETARY"

[workspace.dependencies]
tokio = { version = "1", features = ["macros", "rt-multi-thread", "signal"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tracing = "0.1"
```

(penguin-rust-dev: pick exact patch versions, add kube/k8s-openapi/axum/opentelemetry to `[workspace.dependencies]` as Tasks 2–5 need them, keeping one version per crate.)

- [ ] **Step 2:** `rust-toolchain.toml` → `[toolchain]\nchannel = "1.<current-stable>"\ncomponents = ["clippy","rustfmt","llvm-tools-preview"]`. `deny.toml` → advisories `deny`, licenses allow `[MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unicode-DFS-2016]`. `.gitignore` += `/target`.

- [ ] **Step 3:** Verify: `cargo metadata --format-version=1 >/dev/null` succeeds; `cargo build` on the empty workspace is clean; `cargo deny check` runs (may have 0 members yet). Confirm `pkg/sdk/rust` is NOT a member (`cargo metadata` doesn't list `nest` SDK).

- [ ] **Step 4:** Commit: `git add Cargo.toml Cargo.lock rust-toolchain.toml deny.toml .gitignore && git commit -m "build(rust): add Cargo workspace (nest-gating, svc-streaming)"`

---

## Task 2: `nest-gating` crate (fail-safe two-layer gate)

**Files:** Create `crates/nest-gating/Cargo.toml`, `crates/nest-gating/src/lib.rs`.

**Interfaces:**

- Produces: `pub struct GateDecision { pub allowed: bool, pub code: String, pub message: String }`; `pub trait FlagProvider { fn flag_enabled(&self, flag_key: &str, tenant: &str) -> anyhow::Result<bool>; }`; `pub trait TierProvider { fn tier(&self, tenant: &str) -> anyhow::Result<String>; }`; `pub struct Gate { .. }` with `pub fn evaluate(&self, category: &str, tenant: &str) -> GateDecision` (never returns Err — fail-safe). A default `PostHogFlagProvider` + `LicenseTierProvider` (env-configured) and an in-memory TTL cache.

Semantics mirror `apps/api/gating.py`: Layer 1 flag `nest.{category}` (default OFF; provider error → last-known-cached else OFF); Layer 2 tier (`analytics`→professional; others Free→always allowed). Codes: `nest.gate.flag_disabled`, `nest.gate.tier_required`.

- [ ] **Step 1 (RED):** Write unit tests in `src/lib.rs` `#[cfg(test)]` using fake providers:
  - flag ON + Free category (`streaming`) → `allowed`.
  - flag OFF → `!allowed`, code `nest.gate.flag_disabled`.
  - flag provider returns `Err` with no cache → `!allowed` (fail-safe OFF), no panic.
  - flag provider `Err` after a prior ON → uses cached ON → `allowed` (last-known-cached).
  - `analytics` + tier `free` → `!allowed` code `nest.gate.tier_required`; `analytics` + `professional` → allowed.
- [ ] **Step 2:** `cargo test -p nest-gating` → FAIL (types missing).
- [ ] **Step 3:** Implement `Gate::evaluate` + the traits + default providers + TTL cache. `PostHogFlagProvider` reads `POSTHOG_API_KEY`/`POSTHOG_HOST`; on any error returns `Err` (the cache/OFF logic lives in `Gate`, matching the Python `_flag_or_cached`). Lazy/feature-gate the HTTP client so tests don't need it. Tier map: `{"analytics":"professional"}`, rank `free<professional<enterprise` (alias `pro`→professional). **Never panic.**
- [ ] **Step 4:** `cargo test -p nest-gating` PASS; `cargo clippy -p nest-gating -- -D warnings` clean; `cargo llvm-cov -p nest-gating` ≥90%.
- [ ] **Step 5:** Commit `feat(nest-gating): fail-safe PostHog flag + license tier gate`.

---

## Task 3: `svc-streaming` CRD type

**Files:** Create `services/svc-streaming/Cargo.toml`, `src/crd.rs`, `src/error.rs`.

**Interfaces:**

- Produces: `#[derive(CustomResource, ...)] #[kube(group="nest.penguintech.io", version="v1", kind="DataResource", namespaced, status="DataResourceStatus")] pub struct DataResourceSpec { pub r#type: String, pub category: Option<String>, pub tenant: String, pub size: Option<ResourceSize>, pub replicas: Option<ReplicaConfig>, .. }` + `ResourceSize{ storage: Option<String>, iops: Option<i64> }`, `ReplicaConfig{ write: Option<ReplicaCountSpec>, read: Option<ReplicaCountSpec> }`, `ReplicaCountSpec{ min,max,default,count: i32 }`, `DataResourceStatus{ phase: Option<String>, conditions: Option<Vec<Condition>>, endpoints: Option<ResourceEndpoints>, observed_generation: Option<i64>, .. }`, `ResourceEndpoints{ native, grpc, rest: Option<String> }`. Field names/json match `apis/v1/dataresource_types.go` EXACTLY (serde `rename`/`rename_all="camelCase"`). Only include the fields the reconciler reads/writes (type, category, tenant, size, replicas, status phase/conditions/endpoints/observedGeneration) — YAGNI on the rest.

- [ ] **Step 1 (RED):** Test: deserialize a sample `valkey-stream` DataResource YAML (category=streaming, type=valkey-stream, tenant=t1, size.storage=2Gi, replicas.write.default=1) into the Rust type; assert fields. Serialize a `DataResourceStatus` and assert the camelCase JSON (`observedGeneration`, `endpoints.native`).
- [ ] **Step 2:** `cargo test -p svc-streaming crd` → FAIL.
- [ ] **Step 3:** Implement `src/crd.rs` with the kube `CustomResource` derive (use the GVK above; do NOT generate/install the CRD — the Go `apis/v1` + kustomize own it; this Rust type just (de)serializes the same schema). `src/error.rs`: `thiserror` enum `Error` (Kube, Serialize, Config, …).
- [ ] **Step 4:** `cargo test -p svc-streaming crd` PASS; clippy clean.
- [ ] **Step 5:** Commit `feat(svc-streaming): DataResource CRD type (kube-rs)`.

---

## Task 4: `valkey-stream` reconciler (object builders + status)

**Files:** Create `services/svc-streaming/src/reconcile.rs`, `src/gate.rs`.

**Interfaces:**

- Consumes: `crd::*` (Task 3), `nest_gating::Gate` (Task 2).
- Produces: `pub async fn reconcile(dr: Arc<DataResource>, ctx: Arc<Context>) -> Result<Action, Error>` (kube-rs controller fn) and pure object-builders: `fn build_secret`, `fn build_configmap`, `fn build_service`, `fn build_statefulset`, `fn build_pdb`, `fn desired_replicas(&DataResourceSpec)->i32`, `fn storage_size(&DataResourceSpec)->String`, `fn endpoint(name,ns,replicas)->String`. `Context{ client: kube::Client, gate: Gate }`.

**Port target (match exactly, stream-profiled):** `services/k8s-controller/controllers/keyvalue_reconciler.go`.

- **Secret** `<tenant>-<name>-valkey-auth`: `password` = 32-char alphanumeric from a CSPRNG (`rand`/`getrandom`); **fail closed** if RNG errors (return Error, no weak fallback); `auth.conf` = `requirepass <pw>\n`.
- **ConfigMap** `valkey.conf` (STREAM profile — differs from keyvalue's `allkeys-lru`):
  ```
  # Valkey stream configuration for <tenant>/<name>
  maxmemory-policy noeviction
  appendonly yes
  appendfsync everysec
  include /etc/valkey-auth/auth.conf
  ```
  (No forced `maxmemory` — streams must not be evicted.)
- **headless Service**: `ClusterIP: None`, port `valkey` 6379/TCP, selector `{nest.penguintech.io/dataresource: <name>, app: valkey}`.
- **StatefulSet**: image `docker.io/valkey/valkey:8-bookworm`; main cmd `["valkey-server","/etc/valkey-work/valkey.conf"]`; busybox:latest init `configure-replicaof` running the ordinal>0 replicaof+masterauth script (port `keyvalueReplicaofScript`, lines 538-549); volumes config-work(RW→/etc/valkey-work), config(RO→/etc/valkey), auth(RO→/etc/valkey-auth, from Secret), data(→/data); PVC template `data` RWO, `resources.requests.storage = storage_size()`, **no storageClassName** (match the Go reconciler — cluster default); probes exec `[valkey-cli, ping]`; pod securityContext runAsNonRoot/runAsUser=999/fsGroup=999; replicas = `desired_replicas()`. Owner-reference all objects to the DataResource.
- **PDB**: minAvailable 1 when replicas>1.
- `storage_size`: `spec.size.storage` or `"1Gi"`. `desired_replicas`: 1, or `spec.replicas.write.default` (if write set and default>0; if default<=0 → caller sets Failed).
- **Status**: first apply → `phase=Provisioning` ("Valkey StatefulSet created"). On requeue: if `ss.status.ready_replicas >= replicas` → `endpoints.native = endpoint(...)`, `phase=Ready`, `observed_generation=dr.metadata.generation`; else `phase=Provisioning` ("Waiting for Valkey replicas (r/R ready)"). `endpoint()`: single → `<svc>.<ns>.svc.cluster.local:6379`; multi → `primary: <svc>-0...; replicas: ...` (port `keyvalueEndpoints`).
- **Gate (src/gate.rs):** before building any object, `ctx.gate.evaluate("streaming", &dr.spec.tenant)`; if `!allowed` → set `phase=Pending` + condition `{type:"Gated",status:"False",reason:"GateDenied",message:decision.message}`, patch status, return `Action::requeue(Duration::from_secs(60))` (no objects created; re-checked next requeue so enabling the flag unblocks).
- Idempotent apply: server-side apply or create-or-patch for each object. Transient kube errors → `Err` (controller requeues with backoff).

- [ ] **Step 1 (RED):** Unit tests (no live cluster — test the pure builders + a reconcile with a faked gate/client):
  - `build_configmap` contains `maxmemory-policy noeviction` and `appendonly yes`, NOT `allkeys-lru`.
  - `build_statefulset`: image `valkey:8-bookworm`, replicas from spec (default 1), PVC storage from spec (default 1Gi), no storageClassName, securityContext runAsUser 999, init container present.
  - `build_service`: headless (ClusterIP None), port 6379.
  - `build_secret`: 32-char password, `auth.conf` = `requirepass …`.
  - `desired_replicas`/`storage_size` defaults + spec values; `endpoint()` single vs multi format.
  - gate-denied path → status Pending + Gated=False condition, zero objects built.
- [ ] **Step 2:** `cargo test -p svc-streaming reconcile` → FAIL.
- [ ] **Step 3:** Implement the builders + `reconcile` + `src/gate.rs`. (penguin-rust-dev: use `k8s-openapi` types; a fake `kube::Client` via `tower-test`/`kube::Client::new` with a mock service for the reconcile-level test, or factor the object-apply behind a trait so the reconcile test asserts intended objects without a live API.)
- [ ] **Step 4:** `cargo test -p svc-streaming reconcile` PASS; clippy clean; coverage counts toward ≥90%.
- [ ] **Step 5:** Commit `feat(svc-streaming): valkey-stream reconciler (stream-profiled Valkey)`.

---

## Task 5: controller main — Axum, OTel, leader election, graceful shutdown

**Files:** Create `services/svc-streaming/src/main.rs`.

**Interfaces:** Consumes `crd`, `reconcile`, `gate`, `nest_gating`. Binary entrypoint.

- [ ] **Step 1:** Implement `#[tokio::main]`: init `tracing` + OTLP exporter (env `OTEL_EXPORTER_OTLP_ENDPOINT`, service name `svc-streaming`); build `kube::Client`; construct `Context{ client, gate }` (gate from env-configured providers); start a kube-rs `Controller::new(Api::<DataResource>::all(client), ...)` with a **predicate/filter** so it reconciles only `category=="streaming" && type ∈ NEST_RUST_OWNED_TYPES` (read the env set; Phase 1 = `{valkey-stream}`), `.owns` StatefulSet/Service/Secret/ConfigMap/PDB, `run`ning with `reconcile` + an `error_policy` (requeue w/ backoff). **Leader election** via a Lease (`kube::runtime` lease or a documented single-replica note if lease wiring is deferred — prefer the Lease). Axum server on `:9090` serving `/healthz`, `/readyz`, `/metrics` (Prometheus). SIGTERM → graceful shutdown (stop controller, release lease).
- [ ] **Step 2:** Build: `cargo build -p svc-streaming` clean; `cargo clippy -p svc-streaming -- -D warnings` clean. Smoke: `cargo run -p svc-streaming` against an unreachable cluster fails fast with a clear error (no panic) — OR a unit test for the filter predicate (category/type selection) if main is hard to unit-test. Add a predicate unit test: `should_reconcile(category, type, owned_set)` returns true only for streaming+owned.
- [ ] **Step 3:** `cargo test -p svc-streaming` PASS (predicate test); build clean.
- [ ] **Step 4:** Commit `feat(svc-streaming): controller runtime (kube-rs + Axum + OTel + leader election)`.

---

## Task 6: SSOT + contract — add `valkey-stream` to `streaming`

**Files:** Modify `apis/v1/categories.yaml`, `apps/api/categories.yaml`, `k8s/kustomize/base/crds/dataresource.yaml`, `openapi/v1.yaml`; extend `apis/v1/crd_cel_test.go`, `apps/api/tests/test_categories_sync.py`.

**Interfaces:** Produces the `valkey-stream ∈ streaming` contract that Tasks 4/5 (Rust) and Task 7 (Go) rely on.

- [ ] **Step 1 (RED):** In `apis/v1/crd_cel_test.go`, add/extend a case asserting `TypesForCategory(CategoryStreaming)` == `["kafka","valkey-stream"]` (sorted) and that the CRD CEL streaming clause matches. In `apps/api/tests/test_categories_sync.py`, assert `category_for_type("valkey-stream") == "streaming"`. Run both → FAIL (valkey-stream not yet in SSOT).
- [ ] **Step 2:** Edit `apis/v1/categories.yaml` → under `streaming:` add `- valkey-stream`. Copy to `apps/api/categories.yaml` (byte-identical — the drift test enforces it: `cp apis/v1/categories.yaml apps/api/categories.yaml`). In `k8s/kustomize/base/crds/dataresource.yaml` CEL, change `self.type in ['kafka']` → `self.type in ['kafka','valkey-stream']`. In `openapi/v1.yaml` `ResourceType` enum, add `valkey-stream`.
- [ ] **Step 3:** Run `go test ./apis/v1/ -run 'Category|CRDCEL'` and `python -m pytest apps/api/tests/test_categories_sync.py -q` → PASS. (The Go embed + Python copy are drift-tested; both must agree.)
- [ ] **Step 4:** Commit `feat(apis): add valkey-stream engine to the streaming category`.

---

## Task 7: Go strangler — skip `NEST_RUST_OWNED_TYPES` (penguin-go-dev)

**Files:** Modify `services/k8s-controller/controllers/dataresource_controller.go`; test `services/k8s-controller/controllers/controllers_test.go`; set env on the k8s-controller Deployment (its kustomize/helm).

**Interfaces:** Consumes nothing new; makes the Go controller ignore Rust-owned types.

- [ ] **Step 1 (RED):** Add `controllers_test.go` test: a DataResource `{category:streaming, type:valkey-stream}` with `NEST_RUST_OWNED_TYPES=valkey-stream` in env → `reconcileCreate` returns `(ctrl.Result{}, nil)` and does **not** hit the `default: unsupported type` error and sets no provisioning. (Also: with the env unset, behavior is unchanged.) Run → FAIL.
- [ ] **Step 2:** In `dataresource_controller.go`: add a package helper `rustOwnedTypes()` reading `NEST_RUST_OWNED_TYPES` (comma-separated) into a `map[string]bool` (parsed once/cached). In `reconcileCreate`, **immediately before** `switch dr.Spec.Type` (line ~142, after the category-validation block), add: `if rustOwnedTypes()[dr.Spec.Type] { log.Info("skipping rust-owned type", "type", dr.Spec.Type); return ctrl.Result{}, nil }`. Mirror the same early-return in `reconcileDelete` before its switch (line ~210) so deletes of rust-owned types are no-ops for Go (the finalizer handling for those is the Rust svc's concern; for Phase 1 valkey-stream is net-new so Go has no finalizer on it).
- [ ] **Step 3:** `go test ./services/k8s-controller/controllers/ -run RustOwned -v` PASS; full package green; `gofmt`/build clean.
- [ ] **Step 4:** Set `NEST_RUST_OWNED_TYPES=valkey-stream` in the k8s-controller Deployment env (its kustomize base/helm values) so the toggle is active where svc-streaming is deployed.
- [ ] **Step 5:** Commit `feat(controller): skip rust-owned DataResource types (strangler)`.

---

## Task 8: Dockerfile (rootless multi-stage)

**Files:** Create `services/svc-streaming/Dockerfile`.

- [ ] **Step 1:** Multi-stage, modeled on `services/k8s-controller/Dockerfile`: builder `rust:1-slim-bookworm@sha256:<pinned>` (`cargo build --release -p svc-streaming` from the workspace root, copying the whole workspace so path deps resolve), runtime `debian:bookworm-slim@sha256:<pinned>` with `groupadd/useradd appuser uid 1000`, copy the release binary, `USER appuser`, `EXPOSE 9090`, `CMD ["/svc-streaming"]`. Pin both digests (use `pinning-dependency-digests` skill). Multi-arch amd64/arm64.
- [ ] **Step 2:** Verify it builds: `docker build -f services/svc-streaming/Dockerfile -t svc-streaming:dev .` (from repo root) succeeds; final image runs as non-root (`docker run --rm svc-streaming:dev id` → uid 1000 / or the binary starts and fails fast on no-kubeconfig without panicking).
- [ ] **Step 3:** Commit `build(svc-streaming): rootless multi-stage Dockerfile`.

---

## Task 9: Helm chart `nest-svc-streaming` (k8s-manifest-builder)

**Files:** Create `k8s/helm/nest-svc-streaming/{Chart.yaml,values.yaml,templates/*}`.

- [ ] **Step 1:** Scaffold per PenguinTech Helm standards: controller **Deployment** (replicas 1, leader-election-ready; image repo/tag from values; resources; `securityContext` runAsNonRoot/readOnlyRootFilesystem/drop ALL caps; probes → `:9090/healthz` `/readyz`; env OTEL*\* + POSTHOG*\* + license + `NEST_RUST_OWNED_TYPES=valkey-stream`); **ServiceAccount**; **RBAC** ClusterRole/Binding (DataResource get/list/watch/patch + status; Secret/ConfigMap/Service/StatefulSet/PersistentVolumeClaim/PodDisruptionBudget create/get/list/watch/update/patch/delete; Lease create/get/update for leader election; Events create); **ServiceMonitor** (:9090 /metrics); **CiliumNetworkPolicy** default-deny + egress allowlist (kube-apiserver, DNS, OTLP, PostHog/license hosts); PodSecurityAdmission `restricted` labels. alpha/beta/gamma/production values files per the five-tier convention.
- [ ] **Step 2:** Verify: `helm lint k8s/helm/nest-svc-streaming` clean; `helm template nest-svc-streaming k8s/helm/nest-svc-streaming --values <alpha>` renders; pipe to `kubeconform`/`checkov` if available (no HIGH/CRITICAL).
- [ ] **Step 3:** Commit `feat(helm): nest-svc-streaming chart (RBAC, ServiceMonitor, NetworkPolicy, PSA)`.

---

## Task 10: CI `rust-test` job

**Files:** Modify `.github/workflows/ci.yml`.

- [ ] **Step 1:** In the `changes` job's paths-filter add a `rust` output matching `Cargo.toml`, `Cargo.lock`, `crates/**`, `services/svc-streaming/**`, `rust-toolchain.toml`, `deny.toml`. Add a `rust-test` job (`if: needs.changes.outputs.rust == 'true'`, `needs: changes`): checkout → install the pinned Rust toolchain (`dtolnay/rust-toolchain` pinned by SHA, channel from `rust-toolchain.toml`) + `cargo-deny` + `cargo-llvm-cov` → `cargo fmt --check` → `cargo clippy --workspace -- -D warnings` → `cargo test --workspace` → `cargo deny check` → `cargo llvm-cov --workspace --fail-under-lines 90`. Append `rust-test` to `test-summary`'s `needs:` list (line 625) and add a `Rust Tests: ${{ needs.rust-test.result }}` line to the summary + the "fail if any required job failed" condition.
- [ ] **Step 2:** Verify YAML parses (`python3 -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'))"`); `actionlint`/`zizmor .github/workflows/ci.yml` clean. (Full validation is the PR's CI run.)
- [ ] **Step 3:** Commit `ci: add rust-test job (build/clippy/test/deny/llvm-cov) + changes filter`.

---

## Self-Review

**Spec coverage:** §2 scope → T2–T10; §3.1 crates → T1/T2/T5; §3.2 reconciler → T4; §3.3 strangler → T7 (+T5 predicate, +T9 env); §3.4 SSOT → T6; §4 stack/Docker/Helm/CI → T1/T8/T9/T10; §5 error/resilience → T2/T4/T5; §6 testing → each task's RED steps + T10 coverage gate. All covered.

**Corrections vs spec (apply as written here):** gate-denied uses `Pending`+`Gated=False` condition (no "Blocked" phase); CRD `type` has **no enum** — the SSOT update touches the CEL clause + `openapi/v1.yaml` `ResourceType` enum (not a CRD type-enum); StatefulSet omits `storageClassName` (match the Go reconciler, not the spec's "nest-rbd"); `apps/api/categories.yaml` copy + its drift test are part of T6.

**Placeholder scan:** `<pinned>` digests in T8 and `1.<stable>`/`1.<current-stable>` in T1 are deliberate lookups (penguin-rust-dev resolves via `pinning-dependency-digests`), not vague requirements. No TBD/TODO.

**Type consistency:** `GateDecision`/`Gate::evaluate` (T2) used by `src/gate.rs` (T4); `DataResourceSpec`/`DataResourceStatus`/`ResourceEndpoints` (T3) used by T4/T5; `desired_replicas`/`storage_size`/`endpoint` consistent across T4 steps; `rustOwnedTypes()`/`NEST_RUST_OWNED_TYPES` consistent across T5 (Rust predicate), T7 (Go), T9 (Helm env).

**Open items (confirm at build time, per spec §9):** license-tier provider wiring (T2 `LicenseTierProvider` — confirm the entitlement client/endpoint vs `integrating-license-server`); leader-election lease wiring vs single-replica (T5). Neither blocks the vertical slice.

**Merge note:** this branch targets `v1.2.x`, whose govulncheck gate is red from pre-existing Go CVEs — the build/review proceed, but the _merge_ is gated on the separate Go-CVE decision (issue #37). Phase 1 adds no Go CVE surface.
