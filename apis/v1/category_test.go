package v1

import (
	"go/ast"
	"go/parser"
	"go/token"
	"path/filepath"
	"sort"
	"strconv"
	"testing"
)

// controllerSource is the reconcile file whose type-dispatch switches are the
// live authority for which spec.type values the controller handles.
const controllerSource = "../../services/k8s-controller/controllers/dataresource_controller.go"

// controllerSwitchTypes parses the k8s-controller reconcile source and returns
// the exact, deduplicated set of spec.type values its `switch dr.Spec.Type`
// statements dispatch. Deriving the set from source (rather than a
// hand-maintained copy) means a type added to the controller switch but missing
// from categories.yaml is caught by the sync tests below.
func controllerSwitchTypes(t *testing.T) []string {
	t.Helper()

	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, filepath.FromSlash(controllerSource), nil, 0)
	if err != nil {
		t.Fatalf("parse controller source %q: %v", controllerSource, err)
	}

	// isSpecType reports whether an expression is `<x>.Spec.Type`.
	isSpecType := func(e ast.Expr) bool {
		outer, ok := e.(*ast.SelectorExpr)
		if !ok || outer.Sel.Name != "Type" {
			return false
		}
		inner, ok := outer.X.(*ast.SelectorExpr)
		return ok && inner.Sel.Name == "Spec"
	}

	seen := map[string]bool{}
	ast.Inspect(file, func(n ast.Node) bool {
		sw, ok := n.(*ast.SwitchStmt)
		if !ok || sw.Tag == nil || !isSpecType(sw.Tag) {
			return true
		}
		for _, stmt := range sw.Body.List {
			clause, ok := stmt.(*ast.CaseClause)
			if !ok {
				continue
			}
			for _, expr := range clause.List {
				lit, ok := expr.(*ast.BasicLit)
				if !ok || lit.Kind != token.STRING {
					continue
				}
				val, err := strconv.Unquote(lit.Value)
				if err != nil {
					t.Fatalf("unquote case literal %q: %v", lit.Value, err)
				}
				seen[val] = true
			}
		}
		return true
	})

	if len(seen) == 0 {
		t.Fatalf("no `switch dr.Spec.Type` case types found in %q", controllerSource)
	}

	out := make([]string, 0, len(seen))
	for ty := range seen {
		out = append(out, ty)
	}
	sort.Strings(out)
	return out
}

func TestEveryControllerTypeHasCategory(t *testing.T) {
	for _, ty := range controllerSwitchTypes(t) {
		if _, ok := CategoryForType(ty); !ok {
			t.Fatalf("type %q dispatched by the controller switch has no category in categories.yaml", ty)
		}
	}
}

func TestNoUnknownTypesInMapping(t *testing.T) {
	known := map[string]bool{}
	for _, ty := range controllerSwitchTypes(t) {
		known[ty] = true
	}
	for ty := range TypeToCategory {
		if !known[ty] {
			t.Fatalf("mapping has type %q not dispatched by the controller switch", ty)
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

func TestTypesForCategory(t *testing.T) {
	got := TypesForCategory(CategoryDatabase)
	expected := []string{"keyvalue", "mariadb", "mysql", "postgres", "rockfs", "timeseries", "vector"}
	if len(got) != len(expected) {
		t.Fatalf("TypesForCategory(CategoryDatabase): got %d types, want %d", len(got), len(expected))
	}
	for i, exp := range expected {
		if got[i] != exp {
			t.Fatalf("TypesForCategory(CategoryDatabase): index %d: got %q, want %q", i, got[i], exp)
		}
	}
}

func TestAllCategories(t *testing.T) {
	got := AllCategories()
	expected := []Category{
		CategoryDatabase, CategoryObject, CategoryVolume,
		CategoryStreaming, CategorySearch, CategoryAnalytics,
	}
	if len(got) != len(expected) {
		t.Fatalf("AllCategories(): got %d categories, want %d", len(got), len(expected))
	}
	for i, exp := range expected {
		if got[i] != exp {
			t.Fatalf("AllCategories(): index %d: got %q, want %q", i, got[i], exp)
		}
	}
}

func TestAllCategoriesAreClosed(t *testing.T) {
	validCats := make(map[Category]bool)
	for _, c := range AllCategories() {
		validCats[c] = true
	}
	for _, c := range TypeToCategory {
		if !validCats[c] {
			t.Fatalf("TypeToCategory contains %q which is not in AllCategories()", c)
		}
	}
}
