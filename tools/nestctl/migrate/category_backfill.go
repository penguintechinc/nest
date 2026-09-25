package migrate

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"

	nestv1 "github.com/penguintechinc/nest/apis/v1"
)

// k8sNamePattern matches a valid Kubernetes resource name (RFC1123 DNS
// label/subdomain): lowercase alphanumerics, '-', and '.' only. Used to
// validate namespace/name values before they are passed as exec argv
// elements to kubectl (gosec G204 mitigation).
var k8sNamePattern = regexp.MustCompile(`^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$`)

// isValidK8sName reports whether s is a syntactically valid Kubernetes
// resource name: non-empty, at most 253 characters, and matching the
// RFC1123 DNS label/subdomain pattern.
func isValidK8sName(s string) bool {
	return len(s) > 0 && len(s) <= 253 && k8sNamePattern.MatchString(s)
}

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
		if !isValidK8sName(p.Namespace) || !isValidK8sName(p.Name) {
			fmt.Fprintf(os.Stderr, "warning: DataResource %s/%s has an invalid namespace or name; skipping\n", p.Namespace, p.Name)
			continue
		}
		patch := fmt.Sprintf(`{"spec":{"category":%q}}`, p.Category)
		if dryRun {
			fmt.Printf("[dry-run] %s/%s -> category=%s\n", p.Namespace, p.Name, p.Category)
			continue
		}
		patchArgs := []string{"patch", "dataresource", p.Name, "-n", p.Namespace, "--type=merge", "-p", patch}
		cmd := exec.CommandContext(ctx, "kubectl", patchArgs...) //#nosec G204 -- kubectl invoked via argv (no shell), so there is no shell-injection surface; p.Name/p.Namespace are validated above against the RFC1123 k8s-name pattern, and patch is a fixed-enum JSON string built from the SSOT category map
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("patch %s/%s: %w", p.Namespace, p.Name, err)
		}
		fmt.Printf("patched %s/%s -> category=%s\n", p.Namespace, p.Name, p.Category)
	}
	return nil
}
