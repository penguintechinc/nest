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
