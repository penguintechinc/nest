# Modular Data Categories + Feature-Flag/License Gating — Design

**Date:** 2026-09-22
**Status:** Design (approved for spec review)
**Author:** justin@penguintech.io (with Claude)
**Scope:** Target architecture + phased migration roadmap. This is the umbrella design; each phase below becomes its own spec → plan → implementation cycle.

---

## 1. Problem

Nest today reconciles ~18 engine `type`s through a single flat `switch` in one Go `k8s-controller`, with no module boundary, no feature-flag gating, and no license entitlement layer. The repo has ~25 Go services + 3 Python/React apps and 12 Dockerfiles with no consolidation story. Three goals:

1. **Modularity** — organize engines into a small set of user-facing _categories_ (the "big buckets": database, object, volume, streaming, search, analytics) with a hard contract, not a free-string `type`.
2. **Gating** — every category behind the two-layer standard (PostHog flag + license entitlement), fail-safe, per `critical-rules.md` Feature Flags & License Tiers.
3. **Consolidation + language alignment** — collapse to ~8 container images, convert the data-path/module services to **Rust** (per the Go phase-out + Data Plane rule), keep the control API **Python/Quart**, keep the UI **React**.

---

## 2. Category Taxonomy

Six categories + one cross-cutting concern. `spec.type` remains the engine; `spec.category` becomes an explicit enum.

| Category                    | Engines (`spec.type`)                                                                           |
| --------------------------- | ----------------------------------------------------------------------------------------------- |
| **database**                | postgres, mariadb, mysql, keyvalue, timeseries, vector, rockfs                                  |
| **object**                  | object (s3 / gcs / azure-blob are provider variants of `object`, not distinct spec.type values) |
| **volume**                  | pvc/block, pvc/file, nfs, iscsi, filesystem                                                     |
| **streaming**               | kafka                                                                                           |
| **search**                  | search (opensearch)                                                                             |
| **analytics**               | clickhouse, warehouse/trino, lakehouse/iceberg                                                  |
| **proxy** _(cross-cutting)_ | not a category — a sidecar/data-path any category may request                                   |

The **type→category mapping table is the single source of truth**, shared by the webhook, the backfill migration, and every controller's watch filter — one generated module, so they cannot drift.

The authoritative type list is `apis/v1/categories.yaml` (18 engine types); the webhook/backfill/watch filters all derive from it.

---

## 3. Target Architecture

Three layers, cleanly separated. Each Rust `svc-*` image is **both** the data-path **and** the reconciler for the categories it owns (kube-rs watch loop); the monolithic Go `k8s-controller` dissolves into the four module services.

```
LAYER 1 — logical modules (what users select via spec.category)
  database   object   volume   streaming   search   analytics     [+ proxy = cross-cutting]

LAYER 2 — runtime images (what ships)
 ┌───────────────┐ ┌───────────────┐ ┌────────────────┐ ┌──────────────┐
 │ svc-storage   │ │ svc-database  │ │ svc-streaming  │ │ svc-query    │   RUST
 │ object+volume │ │ database      │ │ streaming+proxy│ │ search+anal. │   (kube-rs
 │ + reconcile   │ │ + reconcile   │ │ + reconcile    │ │ + reconcile  │   controller
 └───────────────┘ └───────────────┘ └────────────────┘ └──────────────┘   + data-path)
 ┌────────────────────────────┐ ┌──────────────┐   ┌─────────┐ ┌────────────┐
 │ hub-api  (Python/Quart)    │ │ hub-webui    │   │ csi     │ │ node-agent │
 │ REST/OpenAPI, auth, tenancy│ │ (React)      │   │ (Go)    │ │ (Go, DS)   │
 │ = apps/api+manager+gateway │ │              │   └─────────┘ └────────────┘
 └────────────────────────────┘ └──────────────┘   mandatory-separate node comps

LAYER 3 — data engines (vendored operators + CRs, NOT our images)
  CloudNativePG · Valkey · Strimzi · OpenSearch-op · Trino · altinity · Ceph/RGW · MariaDB-op
```

**8 images total** (6 "app" + 2 node).

### 3.1 Language topology

| Tier                                                   | Language                                  | Rationale                                                                      |
| ------------------------------------------------------ | ----------------------------------------- | ------------------------------------------------------------------------------ |
| svc-storage / svc-database / svc-streaming / svc-query | **Rust**                                  | data-path / in-line-of-traffic + Go phase-out (`critical-rules.md` Data Plane) |
| hub-api                                                | **Python 3.13 / Quart**                   | control-plane API tier; security-sensitive                                     |
| hub-webui                                              | **React 18 + Vite + TS** (Express-served) | frontend tier                                                                  |
| csi, node-agent                                        | **Go (deferred)**                         | node components; out of scope for the Rust conversion — later candidates       |

### 3.2 Per-svc runtime structure — 1 controller per container, not per category

A grouped container runs **one** controller reconciling **all** categories mapped to it (not one controller per category). The controller is a **separate Deployment** from the data-path, because they have opposite operational profiles.

```
svc-storage   → 1 controller  watches category ∈ {object, volume}    + data-path: nfs-gw, iscsi-gw
svc-database  → 1 controller  watches category ∈ {database}          + data-path: db-proxy
svc-streaming → 1 controller  watches category ∈ {streaming}         + data-path: proxy
svc-query     → 1 controller  watches category ∈ {search, analytics} + data-path: (likely none)
```

|                      | Controller Deployment                         | Data-path Deployment         |
| -------------------- | --------------------------------------------- | ---------------------------- |
| Replicas             | 1–2, **leader-elected** (singleton reconcile) | N, **autoscaled** on traffic |
| Restart blast radius | reconcile pauses briefly                      | one connection drains        |
| Lifecycle            | tied to CRD/watch                             | tied to request load         |

**One image per svc, two entrypoints:** `svc-<name> --role=controller` and `--role=dataplane` select the process. Image = packaging boundary; Deployment = runtime boundary. Not every module has a persistent data-path (svc-query clients likely query the engine directly).

---

## 4. The `spec.category` Contract

- **`spec.category`** — explicit enum on `DataResource`: `database | object | volume | streaming | search | analytics`. `spec.type` stays the engine.
- **Validating webhook** enforces `type ∈ category` — reject at admission when e.g. `category: database, type: s3`. This also routes the CR: each controller's watch filters on its owned categories.
- **Backfill migration** — one-time job derives `category` from existing `type` via the mapping table and patches every pre-existing `DataResource`, so nothing is left unrouted.
- **Mapping table = SSOT** — webhook, backfill, and every watch filter read the same generated module.

---

## 5. Two-Layer Gating

Two independent layers, checked in order, both fail-safe to cached/OFF (`critical-rules.md` Feature Flags & License Tiers).

```
DataResource create / reconcile
   ├─ Layer 1: PostHog flag  nest.{category}    — operational rollout switch
   │     default OFF until the module is validated in that deployment
   │     unreachable → last-known cached value; never-seen → OFF; never crash
   └─ Layer 2: license entitlement (license.penguintech.io) — commercial tier gate
         get_tier() → is this tier entitled? bypass domain-based ONLY
         (*.penguincloud.io, *.penguintech.cloud, {product}.app)
```

### 5.1 Enforcement points (defense in depth)

The CR is directly creatable via `kubectl`, so the API check is not sufficient alone.

| Point      | Where                                        | On deny                                                                                            |
| ---------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| API create | `hub-api` (Python) at DataResource admission | 4xx with reason (flag off / tier not entitled)                                                     |
| Reconcile  | svc-\* controller (Rust) at watch→reconcile  | refuse to provision; set CR `status.conditions` with reason; **never** silently provision or crash |

The controller check is the real, unbypassable gate.

### 5.2 Entitlement map

Categories are almost all Free; tiers gate **capability**, not **data type**.

| Gate                                                                                | Entitlement                                        | Maps to standard               |
| ----------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------ |
| database, object, volume, streaming, search                                         | **Free**                                           | core product                   |
| analytics (ClickHouse/Trino/Iceberg)                                                | **Professional**                                   | —                              |
| Google OAuth2 SSO                                                                   | **Professional**                                   | tier table                     |
| SAML 2.0 / OIDC SSO                                                                 | **Enterprise**                                     | tier table                     |
| Data governance — lineage, audit logs, policy engine, schema registry, external KMS | **Enterprise**                                     | "audit & compliance"           |
| Node count                                                                          | **Free = 1 physical/virtual node**; paid = metered | Licensing Model: Nodes & Seats |

Two clarifications for the license-server integration:

- **nest's `analytics` category ≠ the tier table's "advanced analytics" (Enterprise).** The latter is _platform usage analytics_; nest's is a _customer-run OLAP engine_. analytics-category = Professional is not a conflict.
- **Free's 1-node cap is an upgrade-gate, not a hard enrollment block.** Per `critical-rules.md`, node overage must never block enrollment or suspend management (avoids customer outages). A 2nd node on Free still enrolls and keeps running; the platform surfaces an upgrade prompt and gates _new provisioning_.

### 5.3 Gating clients

| Client                        | Status                                                                                                                                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Python** (hub-api)          | existing penguin license/PostHog integration (`integrating-license-server` skill) — solved path                                                                                                        |
| **Rust** (svc-\* controllers) | **net-new crate** — no Rust PostHog/license client exists yet (same gap as the Rust penguin-logging crate). Flag/tier fetch + on-disk cache for graceful degradation + TTL refresh. Its own work item. |

---

## 6. Migration Strategy

Strangler-fig, never big-bang. The Go controller keeps reconciling every category until each Rust module is ready to take its slice.

```
PHASE 0 — Foundation (additive, ZERO rewrites, ships on today's Go controller)
  • spec.category enum + type∈category validating webhook + backfill migration
  • Python gating client in the API layer (Layer-1 flag + Layer-2 tier)
  → routing contract + gating exist before any service is rewritten. De-risks all of it.

PHASE 1 — First Rust module (proves the pattern)
  • one svc-* image: kube-rs controller + data-path, owns its category group
  • NEW Rust PostHog/license crate (first needed here)
  • coexistence flag: Go controller RELINQUISHES that category; Rust takes it
  → recommended first slice: svc-streaming (kafka only = smallest clean cut)  [confirm at Phase-1 spec]

PHASES 2–4 — Remaining Rust modules (same shape, parallelizable once pattern proven)
  svc-storage · svc-database · svc-query   each: build → migrate reconcile → flip ownership

PHASE 5 — Dissolve k8s-controller (once all 4 categories Rust-owned, delete it)

PARALLEL TRACK A — hub-api: Go gateway API → Python/Quart; fold apps/api + apps/manager
PARALLEL TRACK B — hub-webui: React consolidation (mostly exists as web/)
DEFERRED — csi + node-agent stay Go

Image consolidation falls out of Phases 1–4 + Track A (multi-entrypoint images), not a separate phase.
```

### 6.1 Coexistence safety mechanism (load-bearing)

During transition, **exactly one controller reconciles each category**. A per-category ownership flag (config or PostHog) marks categories as `rust-owned`; the Go controller skips those, the Rust module picks them up. Guarantees:

- no dual reconciliation, no CRs fought over;
- clean rollback — flip the flag back to Go if a module regresses.

---

## 7. Decomposition into Sub-Projects

This design is too large for one implementation spec. Each phase gets its own spec → plan → implement cycle:

| Sub-project                              | Depends on             | Independent?              |
| ---------------------------------------- | ---------------------- | ------------------------- |
| P0 category contract + Python gating     | —                      | ships alone               |
| P1 first Rust module + Rust gating crate | P0                     | proves pattern            |
| P2–P4 remaining Rust modules             | P1                     | parallel among themselves |
| P5 delete k8s-controller                 | P1–P4                  | terminal                  |
| Track A hub-api (Python)                 | P0 (category contract) | parallel to P1–P5         |
| Track B hub-webui (React)                | Track A endpoints      | parallel                  |

**Next step after this design is approved:** brainstorm **P0** through the normal design flow (its own spec + plan).

---

## 8. Out of Scope / Deferred

- **csi + node-agent** — remain Go; node-level, not data-path. Later Rust candidates (block device / iSCSI / hardware = systems work), tracked separately.
- **Data engine choices** — the vendored operators (CNPG, Strimzi, OpenSearch-op, Trino, Ceph/RGW, Valkey, MariaDB-op) are unchanged by this design.
- **Rust penguin-logging crate** — known ecosystem gap; svc-\* use `tracing` + OTel until it exists (`testing.md` Logging Library Conformance).

---

## 9. Open Items (confirm at phase-spec time)

1. **First Rust module** — svc-streaming recommended (smallest); confirm when P1 is spec'd.
2. **hub-api gateway parity** — enumerate the Go `gateway`'s client-facing endpoints to reimplement in Quart (Track A discovery).
3. **Ownership-flag mechanism** — config map vs PostHog flag for the Go↔Rust category handoff; decide at P1.
4. **proxy data-path home** — housed in svc-streaming per grouping, but requestable by any category's reconciler; confirm the sidecar-injection contract at P1.
