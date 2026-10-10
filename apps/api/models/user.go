package models

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"time"

	"gorm.io/gorm"
)

// User represents a user in the system
type User struct {
	ID        uint      `gorm:"primaryKey" json:"id"`
	Username  string    `gorm:"uniqueIndex;not null" json:"username"`
	Email     string    `gorm:"uniqueIndex;not null" json:"email"`
	Password  string    `gorm:"not null" json:"-"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// TableName sets the table name
func (User) TableName() string {
	return "users"
}

// BeforeSave hook to hash password
func (u *User) BeforeSave(tx *gorm.DB) error {
	if tx.Statement.Changed("Password") {
		hash := sha256.Sum256([]byte(u.Password))
		u.Password = hex.EncodeToString(hash[:])
	}
	return nil
}

// VerifyPassword checks if the provided password matches the stored hash.
// The comparison is constant-time to avoid leaking the hash via timing.
//
// NOTE: this still uses unsalted SHA-256, which is weak. Replacing it with a
// salted/strong hasher (bcrypt/argon2) requires a migration path for existing
// stored hashes and is deferred to a dedicated migration.
func (u *User) VerifyPassword(password string) bool {
	hash := sha256.Sum256([]byte(password))
	computed := hex.EncodeToString(hash[:])
	return subtle.ConstantTimeCompare([]byte(u.Password), []byte(computed)) == 1
}

// UserClaims represents JWT claims
type UserClaims struct {
	UserID   uint   `json:"user_id"`
	Username string `json:"username"`
	Email    string `json:"email"`
}
