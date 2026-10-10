# Phase 0: Category Contract + Gating — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit `spec.category` to `DataResource`, enforce `type∈category` at admission (CRD CEL) and reconcile (controller), backfill existing CRs, and gate `DataResource` creation with the two-layer standard (PostHog flag + license tier) — all additive, shipping on today's Go controller with zero rewrites.

**Architecture:** A single data file `apis/v1/categories.yaml` is the source of truth for the type→category mapping. Go embeds it (`go:embed`) into a runtime map; the CRD schema gains a `category` enum plus a CEL cross-field rule (drift-tested against the YAML); the controller re-validates at reconcile (defense in depth); a `nestctl migrate categories` subcommand backfills existing CRs; the Python API derives the category from the requested type and runs a fail-safe two-layer gate before creating the record.

**Tech Stack:** Go 1.25 (controller-runtime, `sigs.k8s.io/yaml`, `go:embed`, fake-client tests), Python 3.13 / Quart (pytest-asyncio, `posthog` SDK), Kubernetes CRD `x-kubernetes-validations` (CEL).

**Spec:** `docs/superpowers/specs/2026-09-22-modular-categories-design.md` (Phase 0 only; §2 taxonomy, §4 contract, §5 gating).

## Global Constraints

- **Backward compatible / additive only** — `spec.category` is `omitempty` (optional); no existing CR breaks; CEL fires only when `category` is set (`!has(self.category) || …`).
- **SSOT** — `apis/v1/categories.yaml` is the ONLY hand-edited mapping. Go embed, Python bundled copy, and CRD CEL are all drift-tested against it; never hand-maintain a second copy silently.
- **Real type set (18)** — the mapping must cover exactly the controller's `switch` in `services/k8s-controller/controllers/dataresource_controller.go:122-162`: `postgres, mariadb, mysql, object, pvc/block, pvc/file, keyvalue, kafka, search, rockfs, vector, clickhouse, timeseries, warehouse/trino, lakehouse/iceberg, nfs, iscsi, filesystem`.
- **Categories (6):** `database | object | volume | streaming | search | analytics`.
- **Gating fail-safe** — PostHog unreachable → last-known cached value; never-seen flag → OFF; never crash the request path (`critical-rules.md` Feature Flags & License Tiers). Flag key: `nest.{category}`.
- **Entitlement (Phase 0 subset):** `analytics` → Professional; all other categories → Free. (SSO / governance / node-count gating is NOT in Phase 0.)
- **Dependency pinning** — Python deps pinned with hashes via `uv pip compile --generate-hashes`; Go deps exact tags. No `latest`.
- **Coverage ≥90%**, ruff clean (Python), `gofmt`/`staticcheck` clean (Go), penguin/`tracing` logging + OTel where a code path is added.
- **Enum marker house style** (from `apis/v1/dataresource_types.go:55`): `// +kubebuilder:validation:Enum=a;b;c` immediately above a named `string` type.

---

## File Structure

**Go (mapping SSOT + CRD + controller + backfill):**

- Create `apis/v1/categories.yaml` — SSOT: category → list of types.
- Create `apis/v1/category.go` — `Category` enum type; `//go:embed categories.yaml`; `TypeToCategory` map; `CategoryForType(string) (Category, bool)`.
- Modify `apis/v1/dataresource_types.go` — add `Category` field to `DataResourceSpec`.
- Create `apis/v1/category_test.go` — mapping completeness + `CategoryForType` behavior.
- Modify `k8s/kustomize/base/crds/dataresource.yaml` — add `category` enum property + `x-kubernetes-validations` CEL rule.
- Create `apis/v1/crd_cel_test.go` — drift guard: CRD CEL membership == `categories.yaml`.
- Modify `services/k8s-controller/controllers/dataresource_controller.go` — reconcile-time `type∈category` re-validation.
- Modify `services/k8s-controller/controllers/controllers_test.go` — controller rejects mismatch.
- Create `tools/nestctl/migrate/category_backfill.go` — `nestctl migrate categories` subcommand.
- Create `tools/nestctl/migrate/category_backfill_test.go` — compute/patch unit tests.

**Python (gating):**

- Create `apps/api/categories.yaml` — bundled copy of the SSOT (shipped in the image).
- Create `apps/api/categories.py` — loads bundled YAML; `category_for_type(str) -> str | None`.
- Create `apps/api/tests/test_categories_sync.py` — drift guard vs `apis/v1/categories.yaml`.
- Create `apps/api/gating.py` — two-layer `evaluate_category_gate(...)`, fail-safe.
- Modify `apps/api/handlers/dataresource.py:66` — derive category, run gate before record creation.
- Create `apps/api/tests/test_gating.py` — gate unit + handler-integration tests.
- Modify `apps/api/requirements.in` + recompile `requirements.txt` — add `posthog`.

**Docs:**

- Modify `docs/superpowers/specs/2026-09-22-modular-categories-design.md` §2 — add `rockfs`→database; note `s3/gcs/azure-blob` are `object` provider-variants, not distinct types.

---

## Task 1: Category SSOT data file + Go loader

**Files:**

- Create: `apis/v1/categories.yaml`
- Create: `apis/v1/category.go`
- Test: `apis/v1/category_test.go`

**Interfaces:**

- Produces: `type Category string`; consts `CategoryDatabase, CategoryObject, CategoryVolume, CategoryStreaming, CategorySearch, CategoryAnalytics`; `var TypeToCategory map[string]Category`; `func CategoryForType(t string) (Category, bool)`; `func AllCategories() []Category`; `func TypesForCategory(c Category) []string`.

- [ ] **Step 1: Write the SSOT data file**

`apis/v1/categories.yaml`:

```yaml
# SSOT for the DataResource type→category mapping (Phase 0).
# Hand-edit ONLY here. Go embeds this; Python bundles a drift-tested copy;
# the CRD CEL rule is drift-tested against it. Keys are categories; each
# lists the exact spec.type engine strings the controller switch dispatches.
database:
  - postgres
  - mariadb
  - mysql
  - keyvalue
  - timeseries
  - vector
  - rockfs
object:
  - object
volume:
  - pvc/block
  - pvc/file
  - nfs
  - iscsi
  - filesystem
streaming:
  - kafka
search:
  - search
analytics:
  - clickhouse
  - warehouse/trino
  - lakehouse/iceberg
```

- [ ] **Step 2: Write the failing test**

`apis/v1/category_test.go`:

```go
package v1

import "testing"

// controllerTypes is the exact set the k8s-controller switch dispatches
// (dataresource_controller.go create-path switch). The mapping must cover
// all of them and nothing else.
var controllerTypes = []string{
	"postgres", "mariadb", "mysql", "object", "pvc/block", "pvc/file",
	"keyvalue", "kafka", "search", "rockfs", "vector", "clickhouse",
	"timeseries", "warehouse/trino", "lakehouse/iceberg", "nfs", "iscsi",
	"filesystem",
}

func TestEveryControllerTypeHasCategory(t *testing.T) {
	for _, ty := range controllerTypes {
		if _, ok := CategoryForType(ty); !ok {
			t.Fatalf("type %q has no category in categories.yaml", ty)
		}
	}
}

func TestNoUnknownTypesInMapping(t *testing.T) {
	known := map[string]bool{}
	for _, ty := range controllerTypes {
		known[ty] = true
	}
	for ty := range TypeToCategory {
		if !known[ty] {
			t.Fatalf("mapping has type %q not dispatched by the controller", ty)
		}
	}
}

func TestCategoryForType(t *testing.T) {
	got, ok := CategoryForType("clickhouse")
	if !ok || got != CategoryAnalytics {
		t.Fatalf("clickhouse: got (%q,%v), want (analytics,true)", got, ok)
	}
	if _, ok := CategoryForType("nonexistent"); ok {
		t.Fatalf("nonexistent type should not resolve")
	}
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && go test ./apis/v1/ -run TestCategory -v`
Expected: FAIL — `undefined: CategoryForType` / `TypeToCategory`.

- [ ] **Step 4: Write the loader**

`apis/v1/category.go`:

```go
package v1

import (
	_ "embed"
	"fmt"
	"sort"

	"sigs.k8s.io/yaml"
)

// Category is the coarse module a DataResource belongs to. The set is closed;
// spec.type must be a member of its declared category (enforced by CRD CEL and
// re-checked by the controller).
// +kubebuilder:validation:Enum=database;object;volume;streaming;search;analytics
type Category string

const (
	CategoryDatabase  Category = "database"
	CategoryObject    Category = "object"
	CategoryVolume    Category = "volume"
	CategoryStreaming Category = "streaming"
	CategorySearch    Category = "search"
	CategoryAnalytics Category = "analytics"
)

//go:embed categories.yaml
var categoriesYAML []byte

// categoryToTypes is the parsed SSOT (category → member engine types).
var categoryToTypes map[Category][]string

// TypeToCategory is the inverted SSOT (engine type → owning category).
var TypeToCategory map[string]Category

func init() {
	raw := map[string][]string{}
	if err := yaml.Unmarshal(categoriesYAML, &raw); err != nil {
		panic(fmt.Sprintf("apis/v1: cannot parse categories.yaml: %v", err))
	}
	categoryToTypes = make(map[Category][]string, len(raw))
	TypeToCategory = make(map[string]Category)
	for cat, types := range raw {
		c := Category(cat)
		categoryToTypes[c] = types
		for _, ty := range types {
			if existing, dup := TypeToCategory[ty]; dup {
				panic(fmt.Sprintf("apis/v1: type %q mapped to both %q and %q", ty, existing, c))
			}
			TypeToCategory[ty] = c
		}
	}
}

// CategoryForType returns the category owning the given engine type.
func CategoryForType(t string) (Category, bool) {
	c, ok := TypeToCategory[t]
	return c, ok
}

// TypesForCategory returns the sorted member types of a category.
func TypesForCategory(c Category) []string {
	out := append([]string(nil), categoryToTypes[c]...)
	sort.Strings(out)
	return out
}

// AllCategories returns the categories in a stable order.
func AllCategories() []Category {
	return []Category{
		CategoryDatabase, CategoryObject, CategoryVolume,
		CategoryStreaming, CategorySearch, CategoryAnalytics,
	}
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/penguin/code/nest && go test ./apis/v1/ -run TestCategory -v && go test ./apis/v1/ -run TestNoUnknown -v && go test ./apis/v1/ -run TestEvery -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apis/v1/categories.yaml apis/v1/category.go apis/v1/category_test.go
git commit -m "feat(apis): add type->category SSOT mapping with go:embed loader"
```

---

## Task 2: Add `spec.category` field + CRD schema + CEL validation

**Files:**

- Modify: `apis/v1/dataresource_types.go:21-53` (add field)
- Modify: `k8s/kustomize/base/crds/dataresource.yaml`
- Test: `apis/v1/crd_cel_test.go`

**Interfaces:**

- Consumes: `Category` type + `TypesForCategory`/`AllCategories` (Task 1).
- Produces: `DataResourceSpec.Category Category` field (json `category,omitempty`).

- [ ] **Step 1: Add the Go field**

In `apis/v1/dataresource_types.go`, inside `DataResourceSpec` (after the `Type` field at line 23):

```go
	// Category is the coarse module this resource belongs to. Optional during
	// Phase 0 (backfilled); when set, spec.type must be a member of it.
	// +optional
	Category Category `json:"category,omitempty"`
```

(No `zz_generated.deepcopy.go` change: `Category` is a value-typed string, copied by the existing `*out = *in`.)

- [ ] **Step 2: Write the failing drift test**

`apis/v1/crd_cel_test.go`:

```go
package v1

import (
	"os"
	"regexp"
	"sort"
	"strings"
	"testing"
)

// TestCRDCELMatchesMapping asserts the CRD's x-kubernetes-validations CEL rule
// enforces exactly the same type∈category membership as categories.yaml, so the
// admission rule can never drift from the Go SSOT.
func TestCRDCELMatchesMapping(t *testing.T) {
	crd, err := os.ReadFile("../../k8s/kustomize/base/crds/dataresource.yaml")
	if err != nil {
		t.Fatalf("read CRD: %v", err)
	}
	body := string(crd)

	// For each category, extract the `self.type in ['a','b',...]` list the CEL
	// rule declares, and compare it (as a set) to the SSOT.
	for _, cat := range AllCategories() {
		re := regexp.MustCompile(`self\.category == '` + string(cat) + `' && self\.type in \[([^\]]*)\]`)
		m := re.FindStringSubmatch(body)
		if m == nil {
			t.Fatalf("CRD CEL missing a membership clause for category %q", cat)
		}
		got := parseCELList(m[1])
		want := TypesForCategory(cat)
		sort.Strings(got)
		if strings.Join(got, ",") != strings.Join(want, ",") {
			t.Fatalf("category %q CEL types %v != SSOT %v", cat, got, want)
		}
	}
}

func parseCELList(s string) []string {
	var out []string
	for _, part := range strings.Split(s, ",") {
		p := strings.TrimSpace(part)
		p = strings.Trim(p, "'")
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && go test ./apis/v1/ -run TestCRDCELMatchesMapping -v`
Expected: FAIL — CRD has no `category` CEL yet.

- [ ] **Step 4: Edit the CRD YAML**

In `k8s/kustomize/base/crds/dataresource.yaml`, under the `spec` object's `properties`, add the `category` property (alongside `type`):

```yaml
category:
  description: Coarse module this resource belongs to; when set, type must be a member.
  type: string
  enum:
    - database
    - object
    - volume
    - streaming
    - search
    - analytics
```

And on the `spec` object itself (sibling of `properties`, `required`), add the cross-field CEL rule:

```yaml
x-kubernetes-validations:
  - message: "spec.type is not valid for spec.category"
    rule: >-
      !has(self.category) ||
      (self.category == 'database' && self.type in ['postgres','mariadb','mysql','keyvalue','timeseries','vector','rockfs']) ||
      (self.category == 'object' && self.type in ['object']) ||
      (self.category == 'volume' && self.type in ['pvc/block','pvc/file','nfs','iscsi','filesystem']) ||
      (self.category == 'streaming' && self.type in ['kafka']) ||
      (self.category == 'search' && self.type in ['search']) ||
      (self.category == 'analytics' && self.type in ['clickhouse','warehouse/trino','lakehouse/iceberg'])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/penguin/code/nest && go test ./apis/v1/ -v`
Expected: PASS (mapping + CEL drift tests green). Also `go build ./...` compiles with the new field.

- [ ] **Step 6: Commit**

```bash
git add apis/v1/dataresource_types.go k8s/kustomize/base/crds/dataresource.yaml apis/v1/crd_cel_test.go
git commit -m "feat(apis): add spec.category field + CRD CEL type-in-category validation"
```

---

## Task 3: Controller reconcile-time re-validation (defense in depth)

**Files:**

- Modify: `services/k8s-controller/controllers/dataresource_controller.go:122-162`
- Test: `services/k8s-controller/controllers/controllers_test.go`

**Interfaces:**

- Consumes: `CategoryForType` (Task 1), `DataResourceSpec.Category` (Task 2).
- Produces: reconcile returns a terminal (non-requeue) error + sets a `Failed` phase with a reason when `spec.category` is set and `type∉category`.

- [ ] **Step 1: Write the failing test**

Add to `services/k8s-controller/controllers/controllers_test.go`:

```go
func TestReconcileRejectsTypeCategoryMismatch(t *testing.T) {
	scheme := newTestScheme(t)
	dr := &nestv1.DataResource{
		ObjectMeta: metav1.ObjectMeta{Name: "bad", Namespace: "default"},
		Spec: nestv1.DataResourceSpec{
			Type:     "s3",              // object-ish engine…
			Category: nestv1.CategoryDatabase, // …declared as database → mismatch
			Tenant:   "tenant-1",
			Class:    "standard",
		},
		Status: nestv1.DataResourceStatus{Phase: nestv1.PhasePending},
	}
	fakeClient := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(dr).
		WithStatusSubresource(&nestv1.DataResource{}).
		Build()
	r := &DataResourceReconciler{Client: fakeClient, Scheme: scheme}

	_, err := r.Reconcile(context.Background(), ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "bad", Namespace: "default"},
	})
	if err == nil {
		t.Fatalf("expected a validation error for type/category mismatch")
	}

	var got nestv1.DataResource
	if gerr := fakeClient.Get(context.Background(), types.NamespacedName{Name: "bad", Namespace: "default"}, &got); gerr != nil {
		t.Fatalf("get: %v", gerr)
	}
	if got.Status.Phase != nestv1.PhaseFailed {
		t.Fatalf("phase = %q, want Failed", got.Status.Phase)
	}
}
```

(If `PhaseFailed` does not exist, use the existing terminal phase constant in `apis/v1`; check `dataresource_types.go` Status phases and adjust this assertion + Step 3 to match.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && go test ./services/k8s-controller/controllers/ -run TestReconcileRejectsTypeCategoryMismatch -v`
Expected: FAIL — reconcile currently ignores category, dispatches to `reconcileObject`/default.

- [ ] **Step 3: Add the guard before the dispatch switch**

In `dataresource_controller.go`, immediately before the `switch dr.Spec.Type` at line ~124:

```go
	// Defense in depth: the CRD CEL rejects type/category mismatches at
	// admission, but a CR can be written by a client that bypasses admission
	// plugins, so re-validate here before provisioning anything.
	if dr.Spec.Category != "" {
		if cat, ok := nestv1.CategoryForType(dr.Spec.Type); !ok || cat != dr.Spec.Category {
			dr.Status.Phase = nestv1.PhaseFailed
			meta.SetStatusCondition(&dr.Status.Conditions, metav1.Condition{
				Type:    "Validated",
				Status:  metav1.ConditionFalse,
				Reason:  "TypeCategoryMismatch",
				Message: fmt.Sprintf("type %q is not a member of category %q", dr.Spec.Type, dr.Spec.Category),
			})
			if uerr := r.Status().Update(ctx, dr); uerr != nil {
				return ctrl.Result{}, uerr
			}
			return ctrl.Result{}, fmt.Errorf("type %q not in category %q", dr.Spec.Type, dr.Spec.Category)
		}
	}
```

(Confirm `meta` = `k8s.io/apimachinery/pkg/api/meta` and `metav1` are imported; add if missing. If `Status.Conditions` is absent on `DataResourceStatus`, drop the condition block and keep the phase + error.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/penguin/code/nest && go test ./services/k8s-controller/controllers/ -run TestReconcileRejectsTypeCategoryMismatch -v`
Expected: PASS. Also run the full package: `go test ./services/k8s-controller/controllers/` — no regressions.

- [ ] **Step 5: Commit**

```bash
git add services/k8s-controller/controllers/dataresource_controller.go services/k8s-controller/controllers/controllers_test.go
git commit -m "feat(controller): reject type/category mismatch at reconcile (defense in depth)"
```

---

## Task 4: `nestctl migrate categories` backfill subcommand

**Files:**

- Create: `tools/nestctl/migrate/category_backfill.go`
- Test: `tools/nestctl/migrate/category_backfill_test.go`

**Interfaces:**

- Consumes: `CategoryForType` (Task 1).
- Produces: `func ComputeCategoryPatches(items []DataResourceItem) []CategoryPatch` (pure, testable); `func BackfillCategories(ctx context.Context, dryRun bool) error` (kubectl-driven, modeled on `longhorn.go`).

- [ ] **Step 1: Write the failing test**

`tools/nestctl/migrate/category_backfill_test.go`:

```go
package migrate

import "testing"

func TestComputeCategoryPatches(t *testing.T) {
	items := []DataResourceItem{
		{Namespace: "default", Name: "pg", Type: "postgres", Category: ""},        // needs patch
		{Namespace: "default", Name: "ck", Type: "clickhouse", Category: ""},       // needs patch
		{Namespace: "default", Name: "obj", Type: "object", Category: "object"},    // already set → skip
		{Namespace: "default", Name: "weird", Type: "made-up", Category: ""},       // unknown → skip + warn
	}
	patches := ComputeCategoryPatches(items)
	if len(patches) != 2 {
		t.Fatalf("got %d patches, want 2: %+v", len(patches), patches)
	}
	byName := map[string]string{}
	for _, p := range patches {
		byName[p.Name] = p.Category
	}
	if byName["pg"] != "database" || byName["ck"] != "analytics" {
		t.Fatalf("wrong categories: %+v", byName)
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && go test ./tools/nestctl/migrate/ -run TestComputeCategoryPatches -v`
Expected: FAIL — undefined `DataResourceItem` / `ComputeCategoryPatches`.

- [ ] **Step 3: Implement the backfill**

`tools/nestctl/migrate/category_backfill.go`:

```go
package migrate

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"

	nestv1 "github.com/penguintechinc/nest/apis/v1"
)

// DataResourceItem is the minimal projection of a DataResource CR the backfill
// needs to decide whether spec.category must be patched.
type DataResourceItem struct {
	Namespace string
	Name      string
	Type      string
	Category  string
}

// CategoryPatch is a single spec.category patch to apply to one CR.
type CategoryPatch struct {
	Namespace string
	Name      string
	Category  string
}

// ComputeCategoryPatches returns the set of patches for items whose category is
// empty and whose type maps to a known category. Items already categorized, or
// with an unknown type, are skipped (the latter logged to stderr).
func ComputeCategoryPatches(items []DataResourceItem) []CategoryPatch {
	var patches []CategoryPatch
	for _, it := range items {
		if it.Category != "" {
			continue
		}
		cat, ok := nestv1.CategoryForType(it.Type)
		if !ok {
			fmt.Fprintf(os.Stderr, "warning: DataResource %s/%s has unknown type %q; skipping\n", it.Namespace, it.Name, it.Type)
			continue
		}
		patches = append(patches, CategoryPatch{Namespace: it.Namespace, Name: it.Name, Category: string(cat)})
	}
	return patches
}

// crList mirrors the kubectl -o json envelope for DataResource CRs.
type crList struct {
	Items []struct {
		Metadata struct {
			Namespace string `json:"namespace"`
			Name      string `json:"name"`
		} `json:"metadata"`
		Spec struct {
			Type     string `json:"type"`
			Category string `json:"category"`
		} `json:"spec"`
	} `json:"items"`
}

// BackfillCategories lists every DataResource cluster-wide and patches
// spec.category on any that lack it. dryRun prints the patches without applying.
func BackfillCategories(ctx context.Context, dryRun bool) error {
	out, err := exec.CommandContext(ctx, "kubectl", "get", "dataresources", "--all-namespaces", "-o", "json").Output()
	if err != nil {
		return fmt.Errorf("kubectl get dataresources: %w", err)
	}
	var list crList
	if err := json.Unmarshal(out, &list); err != nil {
		return fmt.Errorf("parse kubectl output: %w", err)
	}
	items := make([]DataResourceItem, 0, len(list.Items))
	for _, it := range list.Items {
		items = append(items, DataResourceItem{
			Namespace: it.Metadata.Namespace, Name: it.Metadata.Name,
			Type: it.Spec.Type, Category: it.Spec.Category,
		})
	}
	patches := ComputeCategoryPatches(items)
	for _, p := range patches {
		patch := fmt.Sprintf(`{"spec":{"category":%q}}`, p.Category)
		if dryRun {
			fmt.Printf("[dry-run] %s/%s -> category=%s\n", p.Namespace, p.Name, p.Category)
			continue
		}
		if err := exec.CommandContext(ctx, "kubectl", "patch", "dataresource", p.Name,
			"-n", p.Namespace, "--type=merge", "-p", patch).Run(); err != nil {
			return fmt.Errorf("patch %s/%s: %w", p.Namespace, p.Name, err)
		}
		fmt.Printf("patched %s/%s -> category=%s\n", p.Namespace, p.Name, p.Category)
	}
	return nil
}
```

Then register a `categories` subcommand under the existing `nestctl migrate` command group (match the pattern used by `longhorn.go`'s command registration in `tools/nestctl/`; wire `--dry-run` to `BackfillCategories`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/penguin/code/nest && go test ./tools/nestctl/migrate/ -run TestComputeCategoryPatches -v`
Expected: PASS. Also `go build ./tools/nestctl/...`.

- [ ] **Step 5: Commit**

```bash
git add tools/nestctl/migrate/category_backfill.go tools/nestctl/migrate/category_backfill_test.go tools/nestctl/
git commit -m "feat(nestctl): add 'migrate categories' backfill for spec.category"
```

---

## Task 5: Python bundled category map + drift guard

**Files:**

- Create: `apps/api/categories.yaml` (byte-copy of `apis/v1/categories.yaml`)
- Create: `apps/api/categories.py`
- Test: `apps/api/tests/test_categories_sync.py`

**Interfaces:**

- Produces: `def category_for_type(engine_type: str) -> str | None`; `CATEGORIES: frozenset[str]`.

- [ ] **Step 1: Create the bundled copy**

```bash
cp apis/v1/categories.yaml apps/api/categories.yaml
```

- [ ] **Step 2: Write the failing tests**

`apps/api/tests/test_categories_sync.py`:

```python
from pathlib import Path

import yaml

from apps.api.categories import CATEGORIES, category_for_type


def test_bundled_copy_matches_ssot():
    """The image-bundled copy must byte-match the canonical SSOT."""
    repo_root = Path(__file__).resolve().parents[3]
    canonical = (repo_root / "apis/v1/categories.yaml").read_text()
    bundled = (repo_root / "apps/api/categories.yaml").read_text()
    assert bundled == canonical, "apps/api/categories.yaml drifted from apis/v1/categories.yaml"


def test_category_for_type():
    assert category_for_type("postgres") == "database"
    assert category_for_type("clickhouse") == "analytics"
    assert category_for_type("made-up") is None


def test_categories_constant():
    assert CATEGORIES == frozenset(
        {"database", "object", "volume", "streaming", "search", "analytics"}
    )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_categories_sync.py -v`
Expected: FAIL — `apps.api.categories` does not exist.

- [ ] **Step 4: Implement the loader**

`apps/api/categories.py`:

```python
"""Type→category mapping for the API, loaded from the image-bundled SSOT copy.

The canonical source is apis/v1/categories.yaml; apps/api/categories.yaml is a
drift-tested byte copy shipped in the container (the Go tree is not present at
runtime). See tests/test_categories_sync.py.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_MAP_PATH = Path(__file__).with_name("categories.yaml")

_category_to_types: dict[str, list[str]] = yaml.safe_load(_MAP_PATH.read_text())
_TYPE_TO_CATEGORY: dict[str, str] = {
    t: cat for cat, types in _category_to_types.items() for t in types
}

CATEGORIES: frozenset[str] = frozenset(_category_to_types.keys())


def category_for_type(engine_type: str) -> str | None:
    """Return the category owning ``engine_type``, or None if unknown."""
    return _TYPE_TO_CATEGORY.get(engine_type)
```

Add `PyYAML` to `apps/api/requirements.in` if not already present (manager has it; confirm for api), then recompile per Task 7 Step 5.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_categories_sync.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/categories.yaml apps/api/categories.py apps/api/tests/test_categories_sync.py
git commit -m "feat(api): bundle type->category map with drift guard against SSOT"
```

---

## Task 6: Two-layer gating client (fail-safe)

**Files:**

- Create: `apps/api/gating.py`
- Test: `apps/api/tests/test_gating.py` (gate-unit portion)

**Interfaces:**

- Consumes: `category_for_type` (Task 5).
- Produces: `@dataclass GateDecision(allowed: bool, code: str, message: str)`; `def evaluate_category_gate(category: str, tier: str, tenant: str) -> GateDecision`.

- [ ] **Step 1: Write the failing tests**

`apps/api/tests/test_gating.py`:

```python
from unittest.mock import patch

from apps.api.gating import evaluate_category_gate


def _flag_on(*_a, **_k):
    return True


def _flag_off(*_a, **_k):
    return False


def _flag_raises(*_a, **_k):
    raise RuntimeError("posthog unreachable")


def test_core_category_allowed_when_flag_on():
    with patch("apps.api.gating._flag_enabled", _flag_on):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert d.allowed


def test_flag_off_denies():
    with patch("apps.api.gating._flag_enabled", _flag_off):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert not d.allowed
    assert d.code == "nest.gate.flag_disabled"


def test_analytics_requires_professional():
    with patch("apps.api.gating._flag_enabled", _flag_on):
        free = evaluate_category_gate("analytics", tier="free", tenant="t1")
        pro = evaluate_category_gate("analytics", tier="pro", tenant="t1")
    assert not free.allowed and free.code == "nest.gate.tier_required"
    assert pro.allowed


def test_posthog_failure_is_failsafe_off():
    # Unreachable flag backend → treated as OFF (cached default), never crash.
    with patch("apps.api.gating._flag_enabled", _flag_raises):
        d = evaluate_category_gate("database", tier="free", tenant="t1")
    assert not d.allowed
    assert d.code == "nest.gate.flag_disabled"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_gating.py -v`
Expected: FAIL — `apps.api.gating` missing.

- [ ] **Step 3: Implement the gate**

`apps/api/gating.py`:

```python
"""Two-layer DataResource category gate: PostHog rollout flag + license tier.

Both layers fail safe. If the flag backend is unreachable the last-known cached
value is used; a never-seen flag defaults OFF (critical-rules.md Feature Flags).
A gate failure never raises into the request path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Tier ordering for entitlement comparison.
_TIER_RANK = {"free": 0, "professional": 1, "pro": 1, "enterprise": 2}

# Phase 0 entitlement: analytics needs Professional; everything else is Free.
_MIN_TIER = {"analytics": "professional"}

# Last-known flag values, per (flag, tenant), for graceful degradation.
_flag_cache: dict[tuple[str, str], bool] = {}


@dataclass(slots=True)
class GateDecision:
    """Outcome of a category gate check."""

    allowed: bool
    code: str
    message: str


def _flag_enabled(flag_key: str, tenant: str) -> bool:
    """Return whether a PostHog flag is enabled for a tenant.

    Wraps the PostHog SDK; isolated so tests patch it. Follows the
    integrating-license-server skill for client init (env-configured).
    """
    import posthog

    posthog.project_api_key = os.environ["POSTHOG_API_KEY"]
    posthog.host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
    return bool(posthog.feature_enabled(flag_key, tenant) or False)


def _flag_or_cached(flag_key: str, tenant: str) -> bool:
    """Evaluate a flag, falling back to the last-known cached value (else OFF)."""
    try:
        value = _flag_enabled(flag_key, tenant)
        _flag_cache[(flag_key, tenant)] = value
        return value
    except Exception:
        return _flag_cache.get((flag_key, tenant), False)


def evaluate_category_gate(category: str, tier: str, tenant: str) -> GateDecision:
    """Run the two-layer gate for a category. Never raises."""
    # Layer 1: operational rollout flag.
    if not _flag_or_cached(f"nest.{category}", tenant):
        return GateDecision(
            False,
            "nest.gate.flag_disabled",
            f"The '{category}' module is not enabled in this environment.",
        )
    # Layer 2: license tier entitlement.
    required = _MIN_TIER.get(category)
    if required is not None:
        if _TIER_RANK.get(tier, 0) < _TIER_RANK[required]:
            return GateDecision(
                False,
                "nest.gate.tier_required",
                f"The '{category}' module requires the {required} tier.",
            )
    return GateDecision(True, "", "")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_gating.py -v`
Expected: PASS (note the failsafe test patches `_flag_enabled` to raise; `_flag_or_cached` returns cached/OFF).

- [ ] **Step 5: Commit**

```bash
git add apps/api/gating.py apps/api/tests/test_gating.py
git commit -m "feat(api): two-layer category gate (PostHog flag + tier), fail-safe"
```

---

## Task 7: Wire the gate into the create path + add dependency

**Files:**

- Modify: `apps/api/handlers/dataresource.py:66` (`create_data_resource`)
- Modify: `apps/api/requirements.in` (+ recompiled `requirements.txt`)
- Test: `apps/api/tests/test_gating.py` (handler-integration portion)

**Interfaces:**

- Consumes: `category_for_type` (Task 5), `evaluate_category_gate` (Task 6), existing `claims.tier` + `store` + request JSON.

- [ ] **Step 1: Write the failing integration tests**

Append to `apps/api/tests/test_gating.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_denied_when_flag_off(client, bearer_token):
    with patch("apps.api.handlers.dataresource.evaluate_category_gate") as gate:
        from apps.api.gating import GateDecision

        gate.return_value = GateDecision(False, "nest.gate.flag_disabled", "off")
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"name": "x", "type": "postgres", "class": "std", "origination": "managed"},
        )
    assert resp.status_code == 403
    body = await resp.get_json()
    assert body["code"] == "nest.gate.flag_disabled"


@pytest.mark.asyncio
async def test_create_allowed_when_gate_passes(client, bearer_token):
    with patch("apps.api.handlers.dataresource.evaluate_category_gate") as gate:
        from apps.api.gating import GateDecision

        gate.return_value = GateDecision(True, "", "")
        resp = await client.post(
            "/api/v1/tenants/test-tenant/data-resources",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json={"name": "x", "type": "postgres", "class": "std", "origination": "managed"},
        )
    assert resp.status_code == 202
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_gating.py -k create -v`
Expected: FAIL — handler does not call the gate; flag-off create returns 202.

- [ ] **Step 3: Wire the gate into the handler**

In `apps/api/handlers/dataresource.py`, add imports near the top:

```python
from apps.api.categories import category_for_type
from apps.api.gating import evaluate_category_gate
```

In `create_data_resource`, after `resource_type` is parsed and validated but **before** the free-tier quota check at line ~142 (so gating precedes quota), insert:

```python
    category = category_for_type(resource_type)
    if category is None:
        return (
            jsonify({
                "code": "nest.validation.unknown_type",
                "message": f"Unknown resource type '{resource_type}'.",
                "requestId": request_id,
            }),
            400,
        )
    tier = claims.tier if claims else "free"
    gate = evaluate_category_gate(category, tier=tier, tenant=tenant)
    if not gate.allowed:
        return (
            jsonify({"code": gate.code, "message": gate.message, "requestId": request_id}),
            403,
        )
```

Also set the derived category onto the persisted record so the CR carries it: add `category=category,` to the `DataResourceRecord(...)` constructor at line ~210 (add a `category` field to `DataResourceRecord` and the store schema if absent — mirror the existing `resource_type` plumbing).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/penguin/code/nest && python -m pytest apps/api/tests/test_gating.py -v && python -m pytest apps/api/tests/test_dataresource.py -v`
Expected: PASS — gating tests green, existing dataresource tests still green (the mocked gate returns allowed in those, or add an autouse fixture that allows by default; if existing tests now hit a real gate, add a conftest fixture `@pytest.fixture(autouse=True)` patching `evaluate_category_gate` to allow).

- [ ] **Step 5: Add and pin the PostHog dependency**

Add to `apps/api/requirements.in`:

```
posthog==3.7.0
```

Recompile with hashes (never plain pip-compile):

```bash
cd /home/penguin/code/nest/apps/api && uv pip compile --generate-hashes requirements.in -o requirements.txt
```

(Confirm `PyYAML` is present in `requirements.in`; add `PyYAML==6.0.3` if the api app lacked it — Task 5 needs it.)

- [ ] **Step 6: Commit**

```bash
git add apps/api/handlers/dataresource.py apps/api/requirements.in apps/api/requirements.txt apps/api/tests/test_gating.py apps/api/store/
git commit -m "feat(api): gate DataResource creation on category flag + tier, persist category"
```

---

## Task 8: Spec taxonomy addendum

**Files:**

- Modify: `docs/superpowers/specs/2026-09-22-modular-categories-design.md` §2

- [ ] **Step 1: Correct the taxonomy table**

In §2, update the **database** row to include `rockfs`, and annotate the **object** row so the design matches the real engine set:

```
| **database** | postgres, mariadb, mysql, keyvalue, timeseries, vector, rockfs |
| **object**   | object (s3 / gcs / azure-blob are provider variants of `object`, not distinct spec.type values) |
```

Add one line under the table: "The authoritative type list is `apis/v1/categories.yaml` (18 engine types); the webhook/backfill/watch filters all derive from it."

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-09-22-modular-categories-design.md
git commit -m "docs(spec): align category taxonomy with real engine set (add rockfs)"
```

---

## Self-Review

**Spec coverage (Phase 0 scope):**

- spec.category field → Task 2 ✓
- type∈category admission validation → Task 2 (CRD CEL) ✓
- controller re-validation (defense in depth) → Task 3 ✓
- backfill migration → Task 4 ✓
- type→category SSOT (no drift) → Task 1 (Go embed) + Task 5 (Python copy + drift test) + Task 2 (CRD CEL drift test) ✓
- Python two-layer gating in create path, fail-safe → Tasks 6–7 ✓
- entitlement map subset (analytics→Pro) → Task 6 ✓
- taxonomy discrepancy (rockfs) → Task 8 ✓

**Out of Phase 0 (do NOT implement here):** Rust svc rewrites, hub-api consolidation, node-count metering, SSO/governance gating, making `category` required (stays optional this phase).

**Type consistency:** `CategoryForType` (Go, Tasks 1/3/4), `category_for_type` (Python, Tasks 5/7), `evaluate_category_gate`/`GateDecision` (Tasks 6/7), `ComputeCategoryPatches`/`DataResourceItem`/`CategoryPatch` (Task 4) — names used consistently across tasks.

**Assumptions to verify at execution time (adjust the step, don't guess silently):**

1. `DataResourceStatus` phase constant name (`PhaseFailed`?) and whether `Conditions` exists — Task 3 Step 1/3.
2. `nestctl migrate` command registration pattern — Task 4 Step 3.
3. `DataResourceRecord` / store schema accepting a `category` field — Task 7 Step 3.
4. `claims.tier` value vocabulary (`pro` vs `professional`) — `_TIER_RANK` in Task 6 already maps both; confirm the JWT emits one of them.
5. `apps/api` import path prefix (`apps.api.` vs `api.`) in tests — match the existing `test_dataresource.py` imports.
