package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/penguintechinc/nest/services/k8s-controller/controller"
	"github.com/penguintechinc/nest/services/k8s-controller/pkg/config"
	"github.com/sirupsen/logrus"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var (
	version   = "dev"
	buildTime = "unknown"
	gitCommit = "unknown"
)

func main() {
	logrus.WithFields(logrus.Fields{
		"version":    version,
		"build_time": buildTime,
		"git_commit": gitCommit,
	}).Info("NEST Kubernetes Controller starting")

	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		logrus.WithError(err).Fatal("Failed to load configuration")
	}

	// Setup logging
	if err := cfg.SetupLogging(); err != nil {
		logrus.WithError(err).Fatal("Failed to setup logging")
	}

	logrus.WithFields(logrus.Fields{
		"log_level":           cfg.LogLevel,
		"reconcile_interval":  cfg.ReconcileInterval,
		"worker_count":        cfg.WorkerCount,
		"namespace_prefix":    cfg.NamespacePrefix,
	}).Info("Configuration loaded")

	// Connect to database
	db, err := connectDatabase(cfg)
	if err != nil {
		logrus.WithError(err).Fatal("Failed to connect to database")
	}

	logrus.Info("Database connection established")

	// Create controller
	ctrl, err := controller.NewController(cfg, db)
	if err != nil {
		logrus.WithError(err).Fatal("Failed to create controller")
	}

	// Setup context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start health check server
	if cfg.EnableHealthCheck {
		go startHealthServer(cfg.HealthCheckPort)
	}

	// Start metrics server
	if cfg.EnableMetrics {
		go startMetricsServer(cfg.MetricsPort)
	}

	// Start controller
	if err := ctrl.Start(ctx); err != nil {
		logrus.WithError(err).Fatal("Failed to start controller")
	}

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	<-sigChan
	logrus.Info("Shutdown signal received")

	// Graceful shutdown
	cancel()
	ctrl.Stop()

	logrus.Info("Controller shutdown complete")
}

// connectDatabase establishes a connection to the PostgreSQL database
func connectDatabase(cfg *config.Config) (*gorm.DB, error) {
	dsn := cfg.GetDSN()

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: NewGormLogger(),
		NowFunc: func() time.Time {
			return time.Now().UTC()
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get database instance: %w", err)
	}

	// Set connection pool settings
	sqlDB.SetMaxOpenConns(25)
	sqlDB.SetMaxIdleConns(5)
	sqlDB.SetConnMaxLifetime(5 * time.Minute)

	// Test connection
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	return db, nil
}

// startHealthServer starts the health check HTTP server
func startHealthServer(port int) {
	mux := http.NewServeMux()

	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ready"))
	})

	addr := fmt.Sprintf(":%d", port)
	logrus.WithField("address", addr).Info("Starting health check server")

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logrus.WithError(err).Error("Health check server failed")
	}
}

// startMetricsServer starts the Prometheus metrics HTTP server
func startMetricsServer(port int) {
	mux := http.NewServeMux()

	mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		// TODO: Implement Prometheus metrics
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("# Metrics endpoint\n"))
	})

	addr := fmt.Sprintf(":%d", port)
	logrus.WithField("address", addr).Info("Starting metrics server")

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logrus.WithError(err).Error("Metrics server failed")
	}
}

// GormLogger is a custom GORM logger that integrates with logrus
type GormLogger struct {
	SlowThreshold time.Duration
}

func NewGormLogger() *GormLogger {
	return &GormLogger{
		SlowThreshold: 200 * time.Millisecond,
	}
}

func (l *GormLogger) LogMode(level gorm.LogLevel) gorm.Logger {
	return l
}

func (l *GormLogger) Info(ctx context.Context, msg string, data ...interface{}) {
	logrus.WithField("source", "gorm").Infof(msg, data...)
}

func (l *GormLogger) Warn(ctx context.Context, msg string, data ...interface{}) {
	logrus.WithField("source", "gorm").Warnf(msg, data...)
}

func (l *GormLogger) Error(ctx context.Context, msg string, data ...interface{}) {
	logrus.WithField("source", "gorm").Errorf(msg, data...)
}

func (l *GormLogger) Trace(ctx context.Context, begin time.Time, fc func() (string, int64), err error) {
	elapsed := time.Since(begin)
	sql, rows := fc()

	fields := logrus.Fields{
		"source":  "gorm",
		"elapsed": elapsed,
		"rows":    rows,
	}

	if err != nil {
		fields["error"] = err
		logrus.WithFields(fields).Error(sql)
	} else if elapsed > l.SlowThreshold {
		fields["slow"] = true
		logrus.WithFields(fields).Warn(sql)
	} else {
		logrus.WithFields(fields).Debug(sql)
	}
}
