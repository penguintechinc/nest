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
