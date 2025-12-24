# RBAC Middleware for Go API

Comprehensive Role-Based Access Control (RBAC) middleware for the Nest Go API.

## Overview

This middleware provides fine-grained access control with support for:
- Global roles (cross-team access)
- Team-specific roles (scoped to individual teams)
- Resource-level permissions
- Flexible permission matrix

## Role Definitions

### Global Roles

**GlobalAdmin**
- Full access to all teams and resources
- Can manage all users across the system
- Can create/delete teams
- Highest privilege level

**GlobalViewer**
- Read-only access to all teams and resources
- Cannot modify any data
- Useful for auditors and observers

### Team-Specific Roles

**TeamAdmin**
- Full control over team resources
- Can manage team members (add/remove/change roles)
- Can create/update/delete team resources
- Highest team-level privilege

**TeamMaintainer**
- Can manage team resources
- Cannot manage team members
- Can create/update/delete resources
- Operational role without member management

**TeamViewer**
- Read-only access to team resources
- Cannot modify anything
- Cannot manage team members
- Lowest team-level privilege

## Permission Matrix

| Role | Read | Write | Delete | Manage Members |
|------|------|-------|--------|----------------|
| GlobalAdmin | ✓ | ✓ | ✓ | ✓ (all teams) |
| GlobalViewer | ✓ (all teams) | ✗ | ✗ | ✗ |
| TeamAdmin | ✓ | ✓ | ✓ | ✓ (own team) |
| TeamMaintainer | ✓ | ✓ | ✓ | ✗ |
| TeamViewer | ✓ | ✗ | ✗ | ✗ |

## Database Models

### User
- `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`
- `Username`, `Email`, `PasswordHash`
- `FirstName`, `LastName`
- `GlobalRole` (GlobalAdmin, GlobalViewer, or empty)
- `IsActive`
- `LastLoginAt`

### Team
- `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`
- `Name`, `Description`
- `IsActive`

### TeamMembership
- `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`
- `UserID`, `TeamID`
- `Role` (TeamAdmin, TeamMaintainer, TeamViewer)
- Unique constraint on (UserID, TeamID)

### Resource
- `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`
- `TeamID`
- `Name`, `Type`, `Description`
- `IsActive`

## Middleware Functions

### RequireAuth()
Basic authentication middleware that verifies the user is authenticated and active.

**Usage:**
```go
router.Use(rbac.RequireAuth())
```

**Headers Required:**
- `X-User-ID`: User identifier (numeric)

**Sets in Context:**
- `user_id`: uint
- `user_role`: string (global role)

### RequireRole(roles ...string)
Requires the user to have one of the specified roles.

**Usage:**
```go
router.Use(rbac.RequireRole(middleware.GlobalAdmin))
router.Use(rbac.RequireRole(middleware.GlobalAdmin, middleware.GlobalViewer))
```

### RequireTeamAccess(permission string)
Checks if the user has access to the specified team with the given permission.

**Usage:**
```go
teams.GET("/:team_id", rbac.RequireTeamAccess(middleware.PermissionRead), handler)
teams.POST("/:team_id/resources", rbac.RequireTeamAccess(middleware.PermissionWrite), handler)
```

**URL Parameters Required:**
- `team_id`: Team identifier

**Permission Types:**
- `PermissionRead`: Read access
- `PermissionWrite`: Write access
- `PermissionDelete`: Delete access
- `PermissionAdmin`: Administrative access (member management)

### CheckResourceAccess(permission string)
Verifies the user can access a specific resource.

**Usage:**
```go
resources.GET("/:resource_id", rbac.CheckResourceAccess(middleware.PermissionRead), handler)
resources.PUT("/:resource_id", rbac.CheckResourceAccess(middleware.PermissionWrite), handler)
```

**URL Parameters Required:**
- `resource_id`: Resource identifier

## Helper Functions

### GetUserTeams(userID uint) ([]Team, error)
Returns all teams the user has access to.
- Global admins/viewers get all teams
- Other users get only their team memberships

### CanManageTeamMembers(userID uint, teamID uint) (bool, error)
Checks if user can manage team members.
- Only GlobalAdmin and TeamAdmin roles can manage members

## Quick Start

### 1. Initialize Middleware

```go
import (
    "gorm.io/gorm"
    "your-project/apps/api/middleware"
)

func main() {
    db, err := gorm.Open(/* your database config */)
    if err != nil {
        log.Fatal(err)
    }

    // Create RBAC middleware
    rbac := middleware.NewRBACMiddleware(db)

    // Run migrations
    if err := rbac.Migrate(); err != nil {
        log.Fatal("Failed to migrate RBAC models:", err)
    }
}
```

### 2. Apply to Routes

```go
router := gin.Default()

// Public routes (no auth)
router.POST("/login", loginHandler)

// Authenticated routes
api := router.Group("/api/v1")
api.Use(rbac.RequireAuth())
{
    api.GET("/profile", getProfile)

    // Global admin only
    admin := api.Group("/admin")
    admin.Use(rbac.RequireRole(middleware.GlobalAdmin))
    {
        admin.GET("/users", listUsers)
        admin.POST("/users", createUser)
    }

    // Team routes
    teams := api.Group("/teams/:team_id")
    {
        // Any team member can read
        teams.GET("", rbac.RequireTeamAccess(middleware.PermissionRead), getTeam)

        // Maintainer or admin can write
        teams.POST("/resources",
            rbac.RequireTeamAccess(middleware.PermissionWrite),
            createResource)

        // Only team admins can manage members
        teams.POST("/members",
            rbac.RequireTeamAccess(middleware.PermissionAdmin),
            addMember)
    }
}
```

### 3. Use Context in Handlers

```go
func getProfile(c *gin.Context) {
    userID, exists := c.Get(middleware.UserIDKey)
    if !exists {
        c.JSON(401, gin.H{"error": "Unauthorized"})
        return
    }

    // Use userID to fetch and return profile
    c.JSON(200, gin.H{
        "user_id": userID,
        "message": "Profile data",
    })
}
```

## Testing

Run the comprehensive test suite:

```bash
cd /home/penguin/code/Nest/apps/api/middleware
go test -v
```

The test suite includes:
- Authentication tests
- Role-based access tests
- Team access control tests
- Resource access control tests
- Helper function tests

## Examples

See `rbac_example.go` for comprehensive integration examples.

## Files

- `rbac.go` (485 lines): Main middleware implementation
- `rbac_example.go` (159 lines): Integration examples
- `rbac_test.go` (368 lines): Comprehensive test suite
- `README.md`: This file

## License

Limited AGPL3 with preamble for fair use
