package middleware

// Example usage of RBAC middleware with Gin router
//
// This file demonstrates how to integrate the RBAC middleware
// into your Gin application.

/*
Example integration in main.go:

import (
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"your-project/apps/api/middleware"
)

func setupRouter(db *gorm.DB) *gin.Engine {
	r := gin.Default()

	// Create RBAC middleware instance
	rbac := middleware.NewRBACMiddleware(db)

	// Run migrations (only needed once)
	if err := rbac.Migrate(); err != nil {
		log.Fatal("Failed to migrate RBAC models:", err)
	}

	// Public routes (no authentication required)
	r.GET("/health", healthCheck)
	r.POST("/login", login)

	// Authenticated routes
	api := r.Group("/api/v1")
	api.Use(rbac.RequireAuth())
	{
		// User profile routes
		api.GET("/profile", getProfile)
		api.PUT("/profile", updateProfile)

		// Global admin only routes
		admin := api.Group("/admin")
		admin.Use(rbac.RequireRole(middleware.GlobalAdmin))
		{
			admin.GET("/users", listAllUsers)
			admin.POST("/users", createUser)
			admin.DELETE("/users/:id", deleteUser)
		}

		// Global viewer routes (read-only across all teams)
		viewer := api.Group("/viewer")
		viewer.Use(rbac.RequireRole(middleware.GlobalViewer, middleware.GlobalAdmin))
		{
			viewer.GET("/teams", listAllTeams)
			viewer.GET("/resources", listAllResources)
		}

		// Team routes (requires team membership)
		teams := api.Group("/teams/:team_id")
		{
			// Read team info (any team member)
			teams.GET("", rbac.RequireTeamAccess(middleware.PermissionRead), getTeam)

			// Manage team resources (maintainer or admin)
			teams.POST("/resources",
				rbac.RequireTeamAccess(middleware.PermissionWrite),
				createResource)
			teams.PUT("/resources/:resource_id",
				rbac.CheckResourceAccess(middleware.PermissionWrite),
				updateResource)
			teams.DELETE("/resources/:resource_id",
				rbac.CheckResourceAccess(middleware.PermissionDelete),
				deleteResource)

			// Team member management (team admin only)
			members := teams.Group("/members")
			members.Use(rbac.RequireTeamAccess(middleware.PermissionAdmin))
			{
				members.GET("", listTeamMembers)
				members.POST("", addTeamMember)
				members.PUT("/:user_id", updateMemberRole)
				members.DELETE("/:user_id", removeTeamMember)
			}
		}

		// Resource routes with permission checking
		resources := api.Group("/resources/:resource_id")
		{
			resources.GET("",
				rbac.CheckResourceAccess(middleware.PermissionRead),
				getResource)
			resources.PUT("",
				rbac.CheckResourceAccess(middleware.PermissionWrite),
				updateResource)
			resources.DELETE("",
				rbac.CheckResourceAccess(middleware.PermissionDelete),
				deleteResource)
		}
	}

	return r
}

// Example handler using RBAC context
func getProfile(c *gin.Context) {
	userID, exists := c.Get(middleware.UserIDKey)
	if !exists {
		c.JSON(401, gin.H{"error": "Unauthorized"})
		return
	}

	// Use userID to fetch profile
	c.JSON(200, gin.H{
		"user_id": userID,
		"message": "User profile",
	})
}

// Example handler checking team member management permission
func addTeamMember(c *gin.Context) {
	userID, _ := c.Get(middleware.UserIDKey)
	teamID := c.Param("team_id")

	// RBAC middleware already verified the user has admin permission
	// for this team, so we can proceed with adding the member

	c.JSON(200, gin.H{
		"message": "Member added successfully",
		"team_id": teamID,
		"added_by": userID,
	})
}

// Permission Matrix Reference:
//
// GlobalAdmin:
//   - All permissions on all teams
//   - Can manage all users
//   - Can create/delete teams
//
// GlobalViewer:
//   - Read-only access to all teams
//   - Cannot modify any resources
//   - Cannot manage team members
//
// TeamAdmin:
//   - Full control of team resources
//   - Can manage team members (add/remove/change roles)
//   - Can create/update/delete team resources
//
// TeamMaintainer:
//   - Can manage team resources
//   - Cannot manage team members
//   - Can create/update/delete resources
//
// TeamViewer:
//   - Read-only access to team resources
//   - Cannot modify anything
//   - Cannot manage team members
*/
