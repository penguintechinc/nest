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
