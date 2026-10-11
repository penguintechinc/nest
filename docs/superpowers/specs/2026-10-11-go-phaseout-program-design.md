# Go Phase-Out Program (Zero-Go) — Program-Level Design

**Date:** 2026-10-11
**Status:** Design (decisions locked in chat; each phase/track gets its own spec → plan later)
**Author:** justin@penguintech.io (with Claude)
**Supersedes/extends:** `docs/superpowers/specs/2026-09-22-modular-categories-design.md` (umbrella) · **Reference phase:** `docs/superpowers/specs/2026-10-10-phase1-svc-streaming-design.md` · **Tracking:** issue #37
**Inputs:** `.superpowers/go-phaseout-inventory.md` (service inventory), `.superpowers/go-phaseout-wasm-waddles-notes.md` (Waddles WASM study)
**Scope:** Program shape only — the what/why, ordering and cross-cutting rules. Not an implementation plan.

---

## 1. Problem & Goal

**Goal: TRUE ZERO-GO.** Every Go unit in nest becomes Rust, Python, or React. No documented Go exception, no "tiny Go island".

**Why the 2026-09-22 design is too narrow.** It assumed ~8 images and mapped only 5 Go units (gateway, k8s-controller, db-proxy, nfs-gateway, iscsi-gateway); it also deferred csi + node-agent as "stay Go". Discovery found:

| Fact                                      | Value                                                                                                                              |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Go modules                                | 3 (root, `services/k8s-controller`, `services/db-proxy`)                                                                           |
| Go service dirs                           | 25 under `services/` + `apps/api`, `apis/`, `pkg/*`, `tools/nestctl`, `shared/*`                                                   |
| Real Go LoC (excl. tests/generated)       | ~123k (inventory table sum; wc reports ~493k, inflated by tests + `zz_generated`)                                                  |
| Units owned by NO phase in the old design | ~18 ("orphans") — 12 batch/API services, ldap-sync, scim-server, scheduler, injector, federation-controller, pkg/provider, nestctl |
| Units the old design put out of scope     | csi + node-agent (~9.2k), terraform-provider                                                                                       |

Drivers: Go stdlib CVEs (issue #37) with the org on Go 1.25.x (effectively security-EOL), the org Go phase-out rule (`critical-rules.md`), and the security-sensitive-language rule (Rust/Python only, never Go). Phase 1 (svc-streaming) is DONE and proved the pattern; this program generalizes it to everything.

**Method (unchanged from Phase 1):** strangler-fig throughout — both stacks run during each module's cutover, exactly one owner per type/category at any time, clean rollback by flipping ownership. Same subagent-driven build + review discipline Phase 1 used (Sonnet-minimum for code, adversarial final review, fix-before-merge).

---

## 2. Target End-State & Language Split

### 2.1 Language-split rule (locked)

| Workload shape                                                                | Language                 |
| ----------------------------------------------------------------------------- | ------------------------ |
| In-line-of-traffic, agents, CLIs, security-sensitive, reconcilers/controllers | **Rust**                 |
| API / control-plane / background-batch / ML                                   | **Python 3.13 (Quart)**  |
| Frontend                                                                      | **React 18 + Vite + TS** |

**Language-assignment PRECEDENCE** (apply in priority order; first match wins):

| #   | Condition                                                                     | Language                                                       |
| --- | ----------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 1   | In-line-of-traffic / runtime / live data path                                 | **Rust** — always, even if the logic is intelligence/inference |
| 2   | DaemonSet / per-node                                                          | **Rust** — always                                              |
| 3   | Brain (ML/analytics/forecast/anomaly/recommendation/classification/inference) | **hub-api (Python)**                                           |
| 4   | Otherwise                                                                     | base split above                                               |

The brain→hub-api rule (§2.2) is scoped to **control-plane/batch brain only**. Any brain in the live traffic path or on a node is Rust, not hub-api.

### 2.2 End-state images

```
RUST                                                PYTHON                      REACT
 svc-streaming  (P1, DONE)  controller+dataplane     hub-api  (Track A + brain mods; hub-webui (Track B)
 svc-storage    (P2a/P2b)  object+volume+nfs/iscsi            as modules/workers)
 svc-database   (P3)        database + db-proxy      nest-ansible collection
 svc-query      (P4)        search+analytics           (chore; not an image)
 nest-node      (P6)        ONE DaemonSet, 2 containers
 nest-csi-controller (P6)   central Deployment
 nest-control   (Track C4)  scheduler + injector(webhooks) + federation-controller
 nestctl        (Track C5)  CLI, static binary
 [optional] nest-wasm-host  (§5.3, spike-gated)
```

**Brain principle (program-wide):** all intelligence/ML/analytics/decision ("brain") logic — ML, analytics, forecasting, anomaly detection, recommendation, classification, inference — is hosted IN hub-api (Python) as in-process modules + worker entrypoints of the hub-api image, never as standalone services. hub-api is also the integration point for WaddleAI (enterprise AI service, tier-gated) for heavier AI. This applies only to control-plane/batch brain (precedence row 3); it is consistent with the language-split rule since none of it is in-line of traffic or per-node. Non-brain batch (C3 data lifecycle) may still ship as small separate Python images, decided per sub-batch spec.

All operator-vendored data engines (CNPG, Valkey, Strimzi, OpenSearch-op, Trino, Ceph/RGW, MariaDB-op) are unchanged (Layer 3 of the umbrella design).

---

## 3. Inventory → Phase/Track Map

Every inventory unit maps to exactly one owner (dual-owners are data-indexer — brain half Track A, query-plane half P4 — and policy-engine — management half Track A, live-path enforcement half Rust data-plane). **Row count: 39 = 36 inventory units + 3 non-inventory reference rows (svc-streaming already Rust, `web/` React, `pkg/pulumi-provider-nest` stub).** LoC are Go LoC being retired (verify at plan time).

| Unit                           | Role                                                                | Target                                                                                                                                                                                                                                                   | Owner                                                                                                                                                | ~LoC                          | Depends on                                                                                                              |
| ------------------------------ | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| svc-streaming (already Rust)   | streaming reconciler                                                | Rust                                                                                                                                                                                                                                                     | **P1 DONE**                                                                                                                                          | —                             | —                                                                                                                       |
| services/nfs-gateway           | in-line NFS gateway                                                 | Rust                                                                                                                                                                                                                                                     | P2b                                                                                                                                                  | 1.2k                          | P2a; protocol conformance tests                                                                                         |
| services/iscsi-gateway         | in-line iSCSI gateway                                               | Rust                                                                                                                                                                                                                                                     | P2b                                                                                                                                                  | 1.5k                          | P2a; protocol conformance tests                                                                                         |
| pkg/provider                   | cloud storage providers lib                                         | Rust crate                                                                                                                                                                                                                                               | P2a                                                                                                                                                  | 6.3k                          | consumers (object/volume reconcilers)                                                                                   |
| services/db-proxy              | in-line DB proxy                                                    | Rust                                                                                                                                                                                                                                                     | P3                                                                                                                                                   | 17.1k                         | P1 gating crate; shared valkey module                                                                                   |
| services/iceberg-catalog       | Iceberg catalog API                                                 | Python default; Rust if query-plane in-line (P4 spec decides)                                                                                                                                                                                            | P4                                                                                                                                                   | 1.9k                          | svc-query reconciler                                                                                                    |
| services/data-indexer          | catalog/classifier background — **split ownership**                 | **classifier/PII-detection (brain) half → Python hub-api brain module (Track A) if background scan; Rust data-plane module (P4) if in-line — decided at P4 spec**; catalog/indexing (query-plane) half → Python default, Rust only if in-line (P4 spec)  | Track A (brain half) + P4 (query-plane half)                                                                                                         | 2.7k (split sized at P4 spec) | svc-query reconciler (P4 half)                                                                                          |
| services/k8s-controller        | monolithic reconciler + webhook                                     | Rust (split into svc-\*), then **deleted** (empty shell)                                                                                                                                                                                                 | P5 (slices ported in P2a–P4)                                                                                                                         | 18.8k                         | **P2a + P2b + P3 + P4 + P1-kafka-follow-up + C4-injector** (all six categories Rust-owned + admission webhooks in Rust) |
| apis/                          | CRD Go types + deepcopy (generated)                                 | Rust CRD types (exist in svc-streaming)                                                                                                                                                                                                                  | P5                                                                                                                                                   | 5.0k                          | P5 controller deletion                                                                                                  |
| services/csi                   | CSI driver                                                          | Rust (node half → `nest-node`; controller half → central Deployment)                                                                                                                                                                                     | P6                                                                                                                                                   | 3.9k                          | P2a (volume semantics) AND P5 (CSI controller split out of the monolith) — both hard                                    |
| services/node-agent            | node agent/inventory/adopter                                        | Rust (→ `nest-node`)                                                                                                                                                                                                                                     | P6                                                                                                                                                   | 5.3k                          | — (P6 as a whole waits on P2a + P5)                                                                                     |
| services/gateway               | client-facing API gateway                                           | Python/Quart                                                                                                                                                                                                                                             | Track A                                                                                                                                              | 19.4k                         | category contract (P0, done)                                                                                            |
| apps/api (Go)                  | Go API controllers/models                                           | Python/Quart                                                                                                                                                                                                                                             | Track A                                                                                                                                              | 3.1k                          | —                                                                                                                       |
| pkg/auth                       | auth library                                                        | Python (hub-api)                                                                                                                                                                                                                                         | Track A                                                                                                                                              | 1.5k                          | —                                                                                                                       |
| web/, apps/web                 | frontend (already React)                                            | React                                                                                                                                                                                                                                                    | Track B                                                                                                                                              | 0 Go                          | Track A endpoints                                                                                                       |
| services/audit-service         | audit-log API                                                       | Python                                                                                                                                                                                                                                                   | C1                                                                                                                                                   | 2.5k                          | Track A auth                                                                                                            |
| services/policy-engine         | policy API — **split ownership; dissolves as a standalone service** | **management half (authoring/updates/CRUD, writes PRIMARY control DB) → Python hub-api (Track A)**; **live-path enforcement half → Rust data-plane, embedded in in-line components (db-proxy / gateways), reading policy from a DB READ REPLICA (§5.8)** | Track A (management half) + Rust data-plane, embedded in P3 db-proxy / P2b gateways (enforcement half; exact enforcement points per-phase spec-time) | 1.2k (split sized at spec)    | Track A auth; control-DB read replica (§5.8)                                                                            |
| services/scim-server           | SCIM API                                                            | Python                                                                                                                                                                                                                                                   | C1                                                                                                                                                   | 1.1k                          | Track A auth                                                                                                            |
| services/ldap-sync             | LDAP _client_ sync (skauswatch)                                     | Python                                                                                                                                                                                                                                                   | C1                                                                                                                                                   | 1.9k                          | Track A auth                                                                                                            |
| services/schema-service        | schema introspection/cache                                          | Python                                                                                                                                                                                                                                                   | C1                                                                                                                                                   | 2.2k                          | —                                                                                                                       |
| services/predictive-drive      | drive-failure prediction                                            | Python (hub-api brain module/worker)                                                                                                                                                                                                                     | Track A / hub-api (brain module)                                                                                                                     | 1.3k                          | Track A hub-api scaffold                                                                                                |
| services/predictor             | capacity forecaster                                                 | Python (hub-api brain module/worker)                                                                                                                                                                                                                     | Track A / hub-api (brain module)                                                                                                                     | 1.9k                          | Track A hub-api scaffold                                                                                                |
| services/anomaly-detector      | anomaly detection                                                   | Python (hub-api brain module/worker)                                                                                                                                                                                                                     | Track A / hub-api (brain module)                                                                                                                     | 1.4k                          | Track A hub-api scaffold                                                                                                |
| services/intelligence-engine   | classifier; also recommendations / `/api/v1/intelligence/*`         | Python (hub-api brain module)                                                                                                                                                                                                                            | Track A / hub-api (brain module)                                                                                                                     | 1.8k                          | Track A hub-api scaffold                                                                                                |
| services/cost-calculator       | cost computation                                                    | Python (hub-api brain worker — CONFIRMED brain)                                                                                                                                                                                                          | Track A / hub-api (brain worker)                                                                                                                     | 1.5k                          | Track A hub-api scaffold                                                                                                |
| services/erasure-engine        | erasure + GDPR                                                      | Python                                                                                                                                                                                                                                                   | C3                                                                                                                                                   | 2.0k                          | Track A auth; audit (C1)                                                                                                |
| services/saga-engine           | saga orchestrator                                                   | Python                                                                                                                                                                                                                                                   | C3                                                                                                                                                   | 2.0k                          | —                                                                                                                       |
| services/lineage-collector     | lineage collection                                                  | Python (Rust only if measured high-volume)                                                                                                                                                                                                               | C3                                                                                                                                                   | 1.0k                          | —                                                                                                                       |
| services/scheduler             | placement scheduler                                                 | Rust                                                                                                                                                                                                                                                     | C4                                                                                                                                                   | 1.4k                          | —                                                                                                                       |
| services/injector              | admission webhooks                                                  | Rust                                                                                                                                                                                                                                                     | C4                                                                                                                                                   | 2.2k                          | Wave 2 (parallel with P4); must complete before P5 (P5 prerequisite)                                                    |
| services/federation-controller | cross-cluster replicator                                            | Rust                                                                                                                                                                                                                                                     | C4                                                                                                                                                   | 1.9k                          | CRD types                                                                                                               |
| tools/nestctl                  | CLI                                                                 | Rust (static binary)                                                                                                                                                                                                                                     | C5                                                                                                                                                   | 1.5k                          | stable API surface (Track A)                                                                                            |
| pkg/pulumi-provider-nest       | 73-LoC Python stub IaC provider                                     | deprecate (decided)                                                                                                                                                                                                                                      | chore                                                                                                                                                | —                             | Ansible collection                                                                                                      |
| pkg/terraform-provider-nest    | Terraform provider (Go-only SDK)                                    | **deprecate → Ansible collection (Python)**                                                                                                                                                                                                              | chore                                                                                                                                                | 0.06k                         | —                                                                                                                       |
| pkg/sdk (Go stub)              | SDK stub (Rust + TS SDKs exist)                                     | delete                                                                                                                                                                                                                                                   | Exit gate                                                                                                                                            | 0.2k                          | —                                                                                                                       |
| shared/database                | DB library                                                          | dies with consumers                                                                                                                                                                                                                                      | Exit gate                                                                                                                                            | 3.6k                          | last consumer gone                                                                                                      |
| shared/licensing               | licensing library                                                   | replaced by `nest-gating` (Rust) + Python copy                                                                                                                                                                                                           | Exit gate                                                                                                                                            | 2.3k                          | last consumer gone                                                                                                      |
| shared/go_libs                 | shared Go helpers                                                   | dies with consumers                                                                                                                                                                                                                                      | Exit gate                                                                                                                                            | 0.4k                          | last consumer gone                                                                                                      |
| tests/ (Go)                    | Go tests                                                            | port with their targets                                                                                                                                                                                                                                  | Exit gate                                                                                                                                            | 0.4k                          | targets ported                                                                                                          |

**Rollup:** P2a ≈ 6.3k (+ controller slice) · P2b ≈ 2.7k · P3 ≈ 17k · P4 ≈ 4.6k · P5 ≈ 24k (controller slices ported in P2a–P4, deleted here) · P6 ≈ 9.2k · Track A ≈ 32k (gateway/apps-api/auth 24k + brain modules 7.9k: intelligence-engine, anomaly-detector, predictor, predictive-drive, cost-calculator; plus data-indexer's brain half and policy-engine's management half, sized at their specs) · Track C ≈ 20k (C1 7.7k, C3 5.0k, C4 5.5k, C5 1.5k) · Exit gate ≈ 7k. **Total ≈ 123k Go LoC retired.**

---

## 4. Phases & Tracks

Common to every Rust phase (inherited from Phase 1, not restated per section): rootless multi-stage Dockerfile; Helm chart with leader-elected controller Deployment, default-deny CiliumNetworkPolicy, PSA `restricted`, SPIFFE-ready; `tracing` + OTel + `/metrics`; `nest-gating` two-layer gate enforced at reconcile; `rust-owned` ownership set for the Go skip; ≥90% coverage; `cargo clippy -D warnings` + `cargo deny`.

### P1 — svc-streaming (DONE)

Reference implementation. Delivered: `crates/nest-gating`, `services/svc-streaming`, `valkey-stream` engine, strangler `rust-owned` set + Go skip, Dockerfile/Helm/CI. Kafka reconciler remains a fast-follow (Go still reconciles `kafka` until then) — carried as a P1 follow-up, completes the streaming category flip.

### P2 — svc-storage (Rust), split into P2a + P2b

**P2a — object/volume reconcilers (Wave 1, lower risk)**

- **Scope:** `object` + `volume` category reconcilers.
- **Absorbs:** `pkg/provider` (6.3k, Rust crate consumed by these reconcilers — stays with P2a) plus the object/volume slice of k8s-controller.
- **Cutover:** `rust-owned` gains the object/volume types one at a time; Go controller skips them (SSA-owned, §5.7).
- **Risks:** provider-lib breadth (6.3k, multi-cloud).
- **Size:** ~6.3k + controller slice; medium.

**P2b — in-line NFS/iSCSI gateways (deferred, higher risk)**

- **Scope:** nfs-gateway (1.2k) + iscsi-gateway (1.5k) → Rust data-path in svc-storage.
- **Cutover:** in-line → Rust-only, side-by-side Deployments until traffic is moved by Service selector flip.
- **Risks:** silent-data-corruption surface — protocol conformance tests from the Go services MUST be kept and ported (no Go oracle once deleted).
- **Size:** ~2.7k; medium risk, sequenced after P4 (§6).

### P3 — svc-database (Rust)

- **Scope:** `database` category reconcilers (postgres, mariadb, mysql, keyvalue, timeseries, vector, rockfs) + db-proxy data-path.
- **Goal — read/write splitting (§5.8):** db-proxy routes tenant reads to tenant-DB read replicas (CNPG/Galera, provisioned by svc-database) and writes/read-your-writes to the primary, lag-gated with primary fallback.
- **Absorbs:** db-proxy (17.1k — largest single piece, in-line, query-aware) + database slice of k8s-controller; extracts the shared Rust `valkey` module from svc-streaming (Phase 1 open item).
- **Cutover:** reconcilers go per-engine through `rust-owned`. db-proxy runs as a parallel data-path; cutover per-database via Service/connection-string flip with Go proxy kept warm for rollback.
- **Risks:** wire-protocol parity (Postgres/MySQL), query-aware features (largest behavioral surface in the program), tenant isolation at the proxy. Consider splitting P3 into P3a (reconcilers) and P3b (db-proxy) at spec time — disjoint file sets.
- **db-proxy de-risking (cutover approach):**
  - compare **parsed protocol state / AST**, not raw bytes (byte diffs false-positive on timing/ordering/ephemeral fields);
  - **100% shadow reads** through the Rust proxy against the Go proxy;
  - **writes mirrored to ephemeral copy-on-write forks** of the database and diffed — never to the live primary;
  - **rollback via an eBPF/iptables/Envoy bypass** so a Rust-proxy panic never resets client TCP sessions.
- **Size:** ~17k+ Go retired; largest; high risk.

### P4 — svc-query (Rust)

- **Scope:** `search` (opensearch) + `analytics` (clickhouse, warehouse/trino, lakehouse/iceberg) reconcilers; analytics is Professional-tier gated.
- **Absorbs:** search/analytics slice of k8s-controller; **iceberg-catalog (1.9k) and data-indexer (2.7k) where they are query-plane.** Default language per the split rule is Python (API/background); they move into Rust inside svc-query only if the P4 spec finds them in-line of the query path. Either way P4 owns them.
- **data-indexer spec-time decision (explicit):** its classifier/PII-detection goes to hub-api (Python) ONLY if it is a background scan. If it classifies data **in-line as it flows** (live traffic), that classifier is **Rust** (a data-plane module in svc-query/P4, or the Rust/WASM data-plane path) per precedence row 1 — NOT hub-api. The P4 spec settles this before the split is sized.
- **Cutover:** same `rust-owned` mechanism.
- **Risks:** analytics gating (tier path actually exercised here, unlike streaming); catalog API compatibility.
- **Size:** ~4.6k + controller slice; small-medium.

### P5 — Delete Go k8s-controller + apis/ (incremental, NOT big-bang)

- **Not a big-bang cutover:** the per-type handoff is already incremental via the `rust-owned` set (shipped in Phase 1 — the Go controller skips each type as its Rust owner lands). P5 is only the **final deletion of the now-empty controller shell**. The dual-run window lasts until the last type flips; SSA fieldManager ownership (§5.7) keeps it split-brain-free throughout.
- **Prerequisites (canonical):** P2a + P2b + P3 + P4 + P1-kafka-follow-up + C4-injector all complete — i.e. all six categories Rust-owned and admission webhooks in Rust.
- **Scope:** once those prerequisites hold, delete `services/k8s-controller` (18.8k) and `apis/` (5.0k, Go CRD types + deepcopy). Rust CRD types are the SSOT.
- **Gate to start:** zero DataResource types remain Go-owned (`rust-owned` covers `categories.yaml` entirely); soak period clean.
- **Risks:** hidden duties of the monolith (webhook, backfill, finalizers) not yet re-homed — P5 spec begins with a duty audit of the controller.
- **Size:** ~24k deleted, little new code; terminal for the controller.

### P6 — nest-node (Rust) + CSI controller

- **Scope:** consolidate csi (node half) + node-agent into ONE Rust DaemonSet with two cgroup-isolated containers (§5.1); CSI controller half becomes a central Deployment.
- **Absorbs:** csi (3.9k) + node-agent (5.3k). Reverses the 2026-09-22 "stay Go" decision.
- **Cutover:** DaemonSet-for-DaemonSet swap per node pool (node label), CSI driver name preserved so existing PVs keep binding; CSI is registered via kubelet plugin socket — verify rolling replacement does not detach in-use volumes.
- **Depends on (hard):** P2a (volume semantics) AND P5 (CSI controller split out of the monolith).
- **Risks:** systems work (block devices, mounts, privileged syscalls) — native Rust, no WASM, no gVisor; PV data-loss risk makes this the most conservative cutover; depends on P2a volume semantics.
- **Size:** ~9.2k; medium-high risk.

### Track A — hub-api (Python/Quart)

- **Scope:** fold Go `gateway` (19.4k) + `apps/api` (Go, 3.1k) + `pkg/auth` (1.5k) into the Quart hub-api (OpenAPI via `quart-schema`, `@validate_response` DTOs, OIDC scopes/tenant middleware, Layer-1/2 Python gating already exists).
- **Stays Python:** the Go gateway is VERIFIED control-plane REST, not a high-throughput data edge.
- **Cutover:** endpoint-by-endpoint behind the existing ingress; gateway discovery (enumerate client-facing endpoints — umbrella open item 2) is the first deliverable. Both stacks serve during cutover; Go routes removed per resource group.
  - **Weighted ingress routing** 0.1% → 1% → 10% → 100%, with **single-annotation rollback**.
  - **CI auth-matrix fuzzer:** expired/revoked/malformed JWTs — status codes, headers, and scopes must match the Go gateway exactly.
  - **Spec-time check:** confirm whether `/api/v1/objects/*` and `/api/v1/query` STREAM bytes in-line; any path that does is handled separately (Rust or redirect to the data-path), not in Quart.
- **Risks:** gateway parity surface (~19k); security-sensitive (auth) — Python is correct, but regression tests on scopes/tenant isolation are mandatory.
- **hub-api brain modules (per the §2.2 brain principle):** intelligence-engine (classifier), anomaly-detector, predictor (capacity forecaster), predictive-drive (drive-failure prediction) become in-process hub-api modules + worker entrypoints of the hub-api image, never standalone services; cost-calculator is a hub-api brain worker (CONFIRMED brain). **Recommendations / `/api/v1/intelligence/*`** (currently in the Go gateway) is explicitly a brain module, part of the gateway fold. The **classifier / PII-detection half of data-indexer** lands here as a brain module ONLY if it is a background scan (see the P4 spec-time decision); its catalog/indexing half stays P4. Heavier AI integrates WaddleAI (Enterprise, tier-gated). Forecasting/anomaly workers can be built in parallel as hub-api worker entrypoints once the hub-api scaffold exists.
- **Size:** ~32k (24k gateway fold + ~7.9k brain modules, plus data-indexer's brain half and policy-engine's management half — policy authoring/CRUD against the PRIMARY control DB); large, parallel to P1–P6. Unblocks Track B and C1.

### Track B — hub-webui (React)

- **Scope:** React consolidation (`web/`, `apps/web`) — already mostly done; repoint to hub-api, drop any residual Go-served assets, Express-served static.
- **Risks:** low. **Size:** small; follows Track A endpoint changes.

### Track C — Orphans (~11 units, ~20k)

Previously unowned (the ~18 orphans minus the C2 brain units, ~7.9k, that moved to Track A). C1=4 units, C3=3, C4=3, C5=1 (policy-engine dissolved: management half → Track A, enforcement half → Rust data-plane). Grouped into disjoint sub-batches:

| Batch                             | Units                                                                                                                                                          | Lang   | ~LoC         | Notes                                                                                                                                                                                                                                                                       |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **C1 identity & governance APIs** | audit-service, scim-server, ldap-sync, schema-service                                                                                                          | Python | 7.7k         | Needs Track A auth. Audit/schema are Enterprise-gated (policy governance is gated with the policy-engine halves in Track A / data-plane). ldap-sync stays an LDAP _client_ of skauswatch (never a server). Hosted as hub-api modules or small services — decide in C1 spec. |
| ~~C2 ML/forecast batch~~          | **Dissolved — folded into Track A / hub-api brain modules** (predictive-drive, predictor, anomaly-detector, intelligence-engine, cost-calculator); see Track A | Python | 7.9k (moved) | No standalone C2 track.                                                                                                                                                                                                                                                     |
| **C3 data lifecycle**             | erasure-engine, saga-engine, lineage-collector                                                                                                                 | Python | 5.0k         | erasure-engine depends on Track A auth + C1 audit-service (saga/lineage are independent). erasure touches statutory GDPR rights (never tier-gated; must stay in every tier). lineage-collector is Rust only if measured high-volume ingest.                                 |
| **C4 Rust control plane**         | scheduler, injector (admission webhooks), federation-controller                                                                                                | Rust   | 5.5k         | injector runs in Wave 2 (parallel with P4) and must complete before P5 — it is a P5 prerequisite. Shares one `nest-control` image if sensible (spec decision).                                                                                                              |
| **C5 CLI**                        | nestctl                                                                                                                                                        | Rust   | 1.5k         | Static binary; after Track A API stabilizes; in-app update check per `client.md`.                                                                                                                                                                                           |

### Chore — IaC: Ansible collection

- Deprecate `pkg/terraform-provider-nest` (Terraform plugin framework is Go-only, so it cannot survive zero-Go) and ship an **Ansible collection (Python)** as the IaC integration (modules for nest resources via the hub-api).
- Nest resources are K8s CRs, so many consumers need no provider at all (kubectl/GitOps/Terraform's own kubernetes provider); the collection is additive.
- **`pkg/pulumi-provider-nest`: DEPRECATE (decided)** — verified a 73-LoC stub (one `main.py`, no real work). The Ansible collection is the sole IaC integration.

### Exit gate (G0) — zero-Go verification

After the last consumer is gone: delete `pkg/sdk` Go stub, `shared/{database,licensing,go_libs}`, Go `tests/`, all `go.mod`/`go.sum`, Go CI jobs, govulncheck, Go Dockerfiles. Gate: `git ls-files '*.go' go.mod` returns zero (count printed, per Verification Integrity — zero-examined is a failure, so the check also asserts the Rust/Python file counts are nonzero).

---

## 5. Cross-Cutting Architecture

### 5.1 Per-node rule — ONE DaemonSet

Exactly one Rust node DaemonSet (`nest-node`) composed of csi-node + node-agent as **two cgroup-isolated containers**:

| Container  | Privilege                          | Resources           |
| ---------- | ---------------------------------- | ------------------- |
| csi-node   | privileged (mounts, block devices) | own requests/limits |
| node-agent | unprivileged                       | own requests/limits |

Rationale: fewest DaemonSets (one scheduling footprint per node), least-privilege (privilege confined to the one container that needs it), no resource contention (separate cgroups). **Everything else is a Deployment/controller, never a DaemonSet.** The CSI controller is a central Deployment.

### 5.2 Isolation baseline — gVisor REJECTED

Default isolation = **native Rust + the existing K8s baseline**: rootless + PSA `restricted` + Cilium default-deny + enforced Tetragon allowlists.

**gVisor is REJECTED** — operational headaches, breaks XDP and the privileged CSI node, performance cost (Waddles reached the same conclusion: not sustainable on MicroK8s/DOKS, notes §8 #12). This is a recorded decision; do not revisit without new evidence.

### 5.3 WASM for customer-extensible logic — OPTIONAL, spike-gated

- **Scope, strictly:** a Rust host/gateway running WASM module bundles for **customer-extensible / untrusted DATA-PLANE logic** (L7 filters, policy, transforms).
- **Out of scope for WASM:** reconcilers (kube-rs / long-lived watches don't fit WASM) and eBPF/XDP/CSI (native syscalls). These stay native Rust.
- **Pattern: reuse Waddles** (see `.superpowers/go-phaseout-wasm-waddles-notes.md`):
  - wasmtime component-model, exact `=49.0.2` pin; epoch interruption + `ResourceLimiter` + pooling allocator;
  - bundle = single `.wasm` component + signed sidecar; identity = SHA-256 digest; Ed25519 over a length-prefixed, domain-separated payload verified before instantiate; three-way digest check; control plane says what runs;
  - host hardening: native `wasi:sockets` denial, per-`(digest, permission-set)` linker linking only granted imports, typed-trap classification, per-module limits with a hard ceiling that fails validation rather than clamping, three-strike disable;
  - host in its own credential-less, rootless, network-restricted process/pod (reconciler holds creds; module runner never does);
  - one normative `nest:dataplane` WIT package (frozen world + additive `-next`);
  - **MUST implement the `.cwasm` precompile cache** (key `{digest}-{wasmtime_abi}-{collector}`) that Waddles specced but skipped — cold compile was the dominant cost; benchmark `--release`;
  - **Rust-only module toolchain** (cargo-component, wasm32-wasip2, `--locked`, reproducible-build gate, committed hostile fixtures) — Python/JS/C# toolchains caused most Waddles gotchas;
  - emit a span per module invocation in the host (nest requires traces; Waddles' executor did not).
- **Refinements (from a WASM review):**
  - **NEVER load customer-supplied `.cwasm`** (precompiled native code bypasses validation). `.cwasm` is produced only on our own isolated, version-pinned build worker AFTER signature verification of the source `.wasm`.
  - **Fresh `Store` per request** — pooling-allocator Store reuse risks cross-tenant leakage; also wrap the guest `cabi_realloc` in the memory/limit enforcement.
  - **Consider WASI 0.3** (ratified ~2026-06; fixes p2 async pain) instead of Waddles' 0.2 — a spike-time decision.
- **Status:** an OPTIONAL/future capability, gated on (a) an actual customer-extensibility need and (b) a de-risking spike. **Not a blocker for P2a, P2b or any phase.** No phase may depend on it.

### 5.4 Ansible IaC

See Chore above. Python collection against hub-api; additive to CR-based consumption.

### 5.5 Resource-request discipline

Conservative requests/limits on every node-resident or tenant-co-located component so nothing contends with tenant data pods; node components size to the smallest steady state with limits for bursts; controllers are single leader-elected Deployments with modest requests; data-path Deployments autoscale on traffic rather than over-requesting. Each phase spec states requests/limits explicitly and the Helm chart review checks them.

### 5.6 Gating & tenancy (program-wide)

- **Two-layer gate per category:** PostHog flag `nest.{category}` (default OFF, cached, fail-safe) + license tier (Free short-circuit), via the `nest-gating` crate (Rust) / existing Python client. Enforced at reconcile (unbypassable) and at hub-api (defense in depth).
- **Tenant isolation via admission VAP (#39)** applies to every reconciler, old and new.
- **Open follow-ups #39 / #40 / #41 / #42 / #43 / #44** (from the Phase 1 review) are program-wide concerns: each phase spec states which it consumes or closes; none is silently dropped.

### 5.7 Ownership & split-brain (program-wide invariant)

**Every Rust reconciler and the Go controller apply with server-side apply (SSA) using a distinct `fieldManager`** (e.g. `nest-svc-streaming`, `nest-k8s-controller`). During the per-type `rust-owned` handoff this guarantees exactly one owner per type and prevents split-brain dual-reconciliation: a stray write from the non-owner surfaces as an SSA field conflict rather than silently clobbering state. Per-type ownership flips are one-at-a-time; rollback flips the owner back (the new manager's fields are released via SSA, not deleted by hand).

### 5.8 Read/write split — maximize read-replica traffic

**Principle: push as much read traffic to read replicas as correctness allows.** It is both a scale lever (offloads the primary) and the generalization of the policy-enforcement read pattern. This section is a goal/principle (the "what"); the exact routing mechanism (penguin-dal/SeaORM replica routing, proxy rules) is per-phase.

**Deployment flexibility (graceful degradation):** read-replica routing is config/capability-driven and MUST degrade gracefully. The read/write split is an OPTIMIZATION layered on a primary-only baseline — nothing in the design hard-requires a replica.

- **Single-node / no-replica is a first-class supported topology** (the Free-tier sizing: Free = 1 node). With no replica configured, ALL reads use the primary — fully functional, zero behavioral difference, just no read-offload. This applies to BOTH scopes below: hub-api's control DB, and tenant data behind db-proxy (a tenant DB with no replica → the proxy sends reads to its primary; splitting activates only when a replica exists).
- **Two distinct cases — do not conflate:** **(a) no replica configured** (single-node) → reads go to the primary; this is NORMAL, not a failure. **(b) replica configured but unreachable/lagging** → the fail-mode path (lag-health-gated fallback, below).
- Routing auto-detects replica presence (config + health), so the same build runs single-node (Free) up to multi-replica (Enterprise) with no code change — only configuration.

**Scope 1 — Control DB (nest's own, hub-api):**

- Every read that tolerates bounded staleness goes to a **read replica**; the **PRIMARY** is reserved for writes + strong-consistency reads.
- All writes/management of mutable control state (policy, entitlements, routing, config) go through **hub-api → the PRIMARY**; the live/data path reads that state from a replica — never the primary on the hot path, never a synchronous call to hub-api.
- Topology: one primary + one or more replicas; data-plane components use **read-only DB accounts pointed at the replica** (per-service-DB-account rule, `backend-database.md`).
- First concrete application: **policy-engine** — hub-api owns authoring/CRUD on the primary; Rust enforcement embedded in db-proxy/gateways reads current policy from the replica. Same pattern for entitlements, routing, config.

**Scope 2 — Tenant data path via db-proxy (P3 / svc-database):**

- Because db-proxy is query-aware, it performs **read/write splitting on tenant traffic**: tenant read queries (`SELECT` / read-only transactions) route to tenant-DB **read replicas**; writes and read-your-writes route to the tenant primary.
- svc-database provisions/consumes read replicas for tenant engines that support them (CNPG for Postgres, Galera, etc.).
- Listed as a **P3 goal**; it reuses the same protocol parsing as the parsed-state cutover de-risking. The same split applies wherever other in-line components read tenant or control state.

**Non-negotiable carve-outs ("maximize" is not naive):**

- **Read-your-writes / strong-consistency reads → PRIMARY:** immediately after a write in the same flow; auth/token revocation; tenant/resource provisioning; anything unsafe when stale.
- **Lag-health-gated routing:** monitor replica lag; route to a replica only within a bounded-staleness budget; fall back to the primary (or last-known cache) when a replica is lagging or unreachable. Each phase spec states its staleness budget. Applies to case (b) only. _Open (pending user call):_ policy-enforcement replica-unreachable — fail-closed vs fail-to-cached (recommended: fail-to-cached + a per-policy strict flag); see §7 item 10.
- **Read-only accounts on replicas** for all data-plane consumers.

---

## 6. Sequencing & Parallelism

Adopted order (refined): **P2a + Track A(API, incl. hub-api brain modules) → C4 (injector) + P4 → P3 + P2b + Track B → incremental P5 → P6 + C1/C3/C5/chore → G0.**
Rationale: C4/injector runs in Wave 2 (parallel with P4) and must complete before P5, so a C4 slip cannot be discovered late — P5 depends on it. The riskiest in-line work (P3 db-proxy, P2b gateways) comes after the pattern has matured on lower-risk phases. Track B follows Track A's API landing.

```
Wave 1:  P2a ∥ Track A(API + brain modules; forecasting/anomaly workers parallel as hub-api entrypoints)
         (saga-engine + lineage-collector from C3 are independent and may start any time)
Wave 2:  C4 (injector, scheduler, federation) ∥ P4          (injector done before P5)
Wave 3:  P3 ∥ P2b ∥ Track B                  (P3/P2b in-line, highest risk; Track B after Track A API)
Wave 4:  P5 incremental (per-type flips already done; delete empty shell + apis/)
Wave 5:  P6 ∥ C1 ∥ C5 ∥ chore(Ansible) ; erasure-engine (C3) after C1 audit-service
Last:    G0 exit gate
         P5 requires: P2a + P2b + P3 + P4 + P1-kafka-follow-up + C4-injector
         P6 requires: P2a (volume semantics) AND P5 (CSI controller split) — both hard
```

| Relationship                                   | Phases                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Parallelizable (disjoint file sets/images)** | Within a wave (above). P3 is DISJOINT (separate crate) so CAN run in parallel with P2a/P4, but the RECOMMENDED order defers it to Wave 3 to benefit from pattern maturity (largest/riskiest) — not a contradiction, a risk-ordering choice. Serialize only the small shared `rust-owned` / Go-skip edit. Track A (incl. brain workers) ∥ all P\*; C4 ∥ P4; saga/lineage ∥ everything |
| **Must serialize**                             | P2b after P2a (shares svc-storage); P5 after P2a+P2b+P3+P4+P1-kafka+C4-injector; P6 after P2a AND P5; C1/C5 after Track A auth/API; erasure-engine after Track A auth + C1 audit-service (NOT blanket-parallel); Track B after Track A; G0 last                                                                                                                                      |
| **Shared-state caution**                       | Go controller skip edit and `categories.yaml` SSOT are shared files — parallel phases use worktrees and rebase; ownership-set changes land one at a time (§5.7)                                                                                                                                                                                                                      |

---

## 7. Risks & Open Items

| #   | Item                                       | Detail / recommendation                                                                                                                                                                                                                                                                                                                                                                                         |
| --- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **#37 accept-red**                         | Go stdlib CVEs (GO-2026-6605/6607/6608/6613 + `x/net`) are NOT fixed; they disappear as Go is deleted. Consequence: every branch touching Go stays unmergeable to `v1.2.x` (red CI govulncheck) and unbackable past the **local pre-push govulncheck** until its Go is gone. **Recommend: make the LOCAL pre-push govulncheck advisory while CI stays strict.** Pure-Rust/Python/React branches are unaffected. |
| 2   | **Large-phase risk**                       | P3 (db-proxy 17k) and Track A (gateway 19k) are the largest, riskiest pieces; each may split (P3a/b; Track A by resource group).                                                                                                                                                                                                                                                                                |
| 3   | **WASM spike**                             | §5.3 is unproven for nest; needs a spike (latency, `.cwasm` cache, WIT shape) and a real customer-extensibility need before any phase spec.                                                                                                                                                                                                                                                                     |
| 4   | **pulumi-provider fate**                   | DECIDED: deprecate (73-LoC stub); Ansible collection is the sole IaC integration. No open question.                                                                                                                                                                                                                                                                                                             |
| 5   | **Monolith hidden duties**                 | k8s-controller webhook/backfill/finalizers must be audited before P5.                                                                                                                                                                                                                                                                                                                                           |
| 6   | **Orphan roles are inferred**              | Roles come from file names + READMEs; each per-service role/LoC must be verified at its spec time.                                                                                                                                                                                                                                                                                                              |
| 7   | **Boundary calls deferred to phase specs** | iceberg-catalog / data-indexer Rust-vs-Python (P4); lineage-collector Rust-vs-Python (C3); ldap-sync/scim hosting (hub-api module vs service, C1); C3 image packaging; policy-engine enforcement points (which in-line components embed it) per phase spec.                                                                                                                                                     |
| 8   | **Rust logging gap**                       | No penguin-logging Rust crate; all Rust uses `tracing` + OTel (existing exception).                                                                                                                                                                                                                                                                                                                             |
| 9   | **Reversal of old decisions**              | csi/node-agent "stay Go" is reversed (P6); terraform "keep Go island" is rejected in favor of Ansible.                                                                                                                                                                                                                                                                                                          |
| 10  | **Policy-enforcement replica-unreachable** | fail-closed vs fail-to-cached (recommend fail-to-cached + per-policy strict flag) — **OPEN** (§5.8 case (b)).                                                                                                                                                                                                                                                                                                   |

### 7.1 Dual-run / cutover concerns

Both stacks run simultaneously during every cutover; each phase spec must address:

| Concern              | Requirement                                                                                                                                                           |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trace/metrics parity | Cross-runtime **W3C trace-context propagation** across Rust/Python/Go; **parity dashboards** comparing Tokio vs Python event-loop lag vs Go GC pauses during dual-run |
| CRD evolution        | CRD **versioning + conversion webhooks** when Rust CRD types diverge from `apis/`; one SSOT (Rust types) after P5                                                     |
| DB schema migrations | An **explicit single owner** for schema migrations per database during dual-run (no two runtimes migrating the same schema); named in each phase spec                 |
| Contract skew        | **CLI/UI/API contract-skew tests** (nestctl, hub-webui, hub-api, SDKs) so a mid-cutover version mix cannot break clients                                              |
| Control-plane load   | **N× LIST/WATCH load** on apiserver/etcd from many Rust controllers — mitigate with scoped/shared informers (ties to #40)                                             |
| Team load            | Cognitive load across 4 stacks (Rust/Python/React + ops) — limit concurrent in-flight cutovers; prefer finishing a wave before starting the next                      |

**Next step:** brainstorm the Wave-1 phases (P2a, Track A discovery + brain-module scaffold) through the normal spec → plan flow; each cites this program spec.
