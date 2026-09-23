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
	validCategories := map[Category]bool{
		CategoryDatabase:  true,
		CategoryObject:    true,
		CategoryVolume:    true,
		CategoryStreaming: true,
		CategorySearch:    true,
		CategoryAnalytics: true,
	}
	for cat, types := range raw {
		c := Category(cat)
		if !validCategories[c] {
			panic(fmt.Sprintf("apis/v1: categories.yaml key %q is not a valid category (must be one of: database, object, volume, streaming, search, analytics)", cat))
		}
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
