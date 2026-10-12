# Track A: Go leftover verification (spec section 10 item 8)

Oracle: `scripts/verify-go-leftovers.sh` (run before deletion, 2026-10-12).

| Check                                                | Result                                                                                                                                             |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/api` Go files examined                         | 10                                                                                                                                                 |
| `package main` in `apps/api`                         | none (no binary can be produced)                                                                                                                   |
| External importers of `penguintechinc/nest/apps/api` | 0                                                                                                                                                  |
| `pkg/auth` importer dirs examined                    | 9 (anomaly-detector, audit-service, cost-calculator, data-indexer, iceberg-catalog, intelligence-engine, ldap-sync, policy-engine, schema-service) |
| `go build ./...` before vs after deletion            | identical (rc=0, no output)                                                                                                                        |

Note: after deletion the script exits 1 by design (zero Go files examined). It is a pre-deletion oracle.

## Capability diff

| Go file                                                                                        | Capability                                                 | Python equivalent                                                        | Verdict                                                                                                |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `middleware/auth.go`, `middleware/rbac.go` (+ `rbac_example.go`, `rbac_test.go`)               | gin JWT validation, role-name RBAC, team permission checks | `penguin-aaa` + `auth/authz.py` (Tasks 3/4)                              | Superseded. Role-name branching is forbidden by policy (scope-only authz); not ported.                 |
| `controllers/auth.go` (Login/Logout/Me/CreateUser), `models/user.go` (sha256 password hashing) | gin/gorm user management                                   | none in hub-api; a port already exists at `apps/manager/routes/auth.py`  | Legacy gin/gorm surface, no router/main, unreachable; not ported.                                      |
| `controllers/teams.go`, `controllers/models.go` (teams CRUD, members)                          | gin/gorm teams management                                  | none in hub-api; a port already exists at `apps/manager/routes/teams.py` | Legacy, unreachable; not ported.                                                                       |
| `resources_controller.go`, `models.go` (gorm `Resource`, `Team`, `TeamMember`, stats)          | pre-CRD resource CRUD API                                  | read paths covered by `data-resources` (Group 1)                         | Legacy, unreachable.                                                                                   |
| `resources_controller.go` `GetResourceStats`, `GetConnectionInfo`                              | per-resource stats, connection info                        | none                                                                     | Not ported, no caller found (grep of `*.go` for both names: only the definitions in the deleted file). |
| `pkg/auth` (shared Go package)                                                                 | JWT/OIDC middleware                                        | n/a                                                                      | KEEP: 9 other Go services import it; it is deleted with each importer's own track, not Track A.        |

## Open gap

Hub-api owns `users` per the PII boundary, but a user/team management API is NOT in Part 1. User/team management belongs to the auth service (penguin-aaa / Track C).

## Evidence of unreachability

- No `package main` and no `ListenAndServe`/router wiring in any `apps/api/*.go` file; the `apps/api/Dockerfile` entrypoint is `python3 apps/api/main.py`.
- Constructors (`NewResourceController`, `NewAuthController`, `NewTeamsController`, `NewRBACMiddleware`, `AuthMiddleware`) are referenced only inside the deleted files.
