package migrate

import "testing"

func TestComputeCategoryPatches(t *testing.T) {
	items := []DataResourceItem{
		{Namespace: "default", Name: "pg", Type: "postgres", Category: ""},      // needs patch
		{Namespace: "default", Name: "ck", Type: "clickhouse", Category: ""},    // needs patch
		{Namespace: "default", Name: "obj", Type: "object", Category: "object"}, // already set → skip
		{Namespace: "default", Name: "weird", Type: "made-up", Category: ""},    // unknown → skip + warn
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
