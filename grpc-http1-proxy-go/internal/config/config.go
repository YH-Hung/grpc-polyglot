// Package config provides configuration management for the gRPC HTTP/1 proxy.
// It supports loading configuration from environment variables and command-line flags,
// with sensible defaults for all settings.
package config

import (
	"flag"
	"fmt"
	"os"
	"strconv"
	"time"
)

// Environment variable names used for configuration.
const (
	envHTTPListen     = "HTTP_LISTEN_ADDR"      // HTTP server bind address
	envMetricsPath    = "METRICS_PATH"          // Path for Prometheus metrics endpoint
	envGRPCBackend    = "GRPC_BACKEND_ADDR"     // Target gRPC backend address
	envGRPCDeadlineMS = "GRPC_DEADLINE_MS"      // Per-request timeout in milliseconds
	envGRPCDialMS     = "GRPC_DIAL_TIMEOUT_MS"  // Connection establishment timeout in milliseconds
	envShutdownMS     = "SHUTDOWN_TIMEOUT_MS"   // Graceful shutdown timeout in milliseconds
	envMaxRetries     = "GRPC_MAX_RETRIES"      // Maximum retry attempts for transient errors
)

// Config holds all configuration parameters for the proxy service.
// Fields can be set via environment variables or command-line flags.
type Config struct {
	// HTTP server configuration
	HTTPListenAddr string // Address and port to bind the HTTP server (e.g., ":8080")
	MetricsPath    string // URL path for Prometheus metrics endpoint (default: "/metrics")
	HealthPath     string // URL path for health check endpoint (default: "/healthz")

	// gRPC client configuration
	GRPCBackendAddr string        // Target gRPC backend address (e.g., "localhost:50051")
	GRPCDeadline    time.Duration // Maximum time to wait for a gRPC call to complete
	GRPCDialTimeout time.Duration // Maximum time to establish a gRPC connection
	ShutdownTimeout time.Duration // Maximum time to wait for graceful shutdown
	MaxGRPCRetries  uint          // Maximum number of retry attempts for transient gRPC errors
}

// Defaults returns a Config with all fields set to their default values.
// These defaults are suitable for local development and can be overridden
// via environment variables or command-line flags.
func Defaults() Config {
	return Config{
		HTTPListenAddr: ":8080",
		MetricsPath:    "/metrics",
		HealthPath:     "/healthz",

		GRPCBackendAddr: "localhost:50051",
		GRPCDeadline:    5 * time.Second,
		GRPCDialTimeout: 5 * time.Second,
		ShutdownTimeout: 10 * time.Second,
		MaxGRPCRetries:  2,
	}
}

// FromEnv creates a Config by loading values from environment variables.
// Any environment variable that is not set will use the default value from Defaults().
// This function is typically called first, then BindFlags() can be used to allow
// command-line flags to override the environment variable values.
//
// Example:
//   export GRPC_BACKEND_ADDR=localhost:9090
//   export GRPC_DEADLINE_MS=10000
//   cfg := config.FromEnv()
func FromEnv() Config {
	cfg := Defaults()

	// Load HTTP server configuration from environment
	if v := os.Getenv(envHTTPListen); v != "" {
		cfg.HTTPListenAddr = v
	}
	if v := os.Getenv(envMetricsPath); v != "" {
		cfg.MetricsPath = v
	}
	if v := os.Getenv(envGRPCBackend); v != "" {
		cfg.GRPCBackendAddr = v
	}

	// Load duration-based settings (converted from milliseconds)
	if v := parseDurationFromMillis(envGRPCDeadlineMS); v > 0 {
		cfg.GRPCDeadline = v
	}
	if v := parseDurationFromMillis(envGRPCDialMS); v > 0 {
		cfg.GRPCDialTimeout = v
	}
	if v := parseDurationFromMillis(envShutdownMS); v > 0 {
		cfg.ShutdownTimeout = v
	}

	// Load retry configuration
	if v := parseUint(envMaxRetries); v >= 0 {
		cfg.MaxGRPCRetries = uint(v)
	}

	return cfg
}

// parseDurationFromMillis reads an environment variable and parses it as milliseconds,
// returning the equivalent time.Duration. Returns 0 if the variable is not set,
// empty, or cannot be parsed as a positive integer.
func parseDurationFromMillis(key string) time.Duration {
	if raw := os.Getenv(key); raw != "" {
		ms, err := strconv.ParseInt(raw, 10, 64)
		if err == nil && ms > 0 {
			return time.Duration(ms) * time.Millisecond
		}
	}
	return 0
}

// parseUint reads an environment variable and parses it as an integer.
// Returns -1 if the variable is not set, empty, or cannot be parsed.
// This allows distinguishing between "not set" (returns -1) and "set to 0" (returns 0).
func parseUint(key string) int64 {
	if raw := os.Getenv(key); raw != "" {
		if v, err := strconv.ParseInt(raw, 10, 64); err == nil {
			return v
		}
	}
	return -1
}

// BindFlags registers command-line flags for all Config fields in the provided FlagSet.
// The default value for each flag is taken from the current Config state, allowing
// environment variables to be overridden by command-line arguments.
//
// This should be called after FromEnv() to allow flags to override environment variables.
// After calling flag.Parse(), the Config will contain the final values.
//
// Example:
//   cfg := config.FromEnv()
//   fs := flag.NewFlagSet("app", flag.ExitOnError)
//   cfg.BindFlags(fs)
//   fs.Parse(os.Args[1:])
func (cfg *Config) BindFlags(fs *flag.FlagSet) {
	if fs == nil {
		panic("nil FlagSet")
	}
	fs.StringVar(&cfg.HTTPListenAddr, "http-listen", cfg.HTTPListenAddr, "address to bind the HTTP server to")
	fs.StringVar(&cfg.MetricsPath, "metrics-path", cfg.MetricsPath, "path that exposes Prometheus metrics")
	fs.StringVar(&cfg.GRPCBackendAddr, "grpc-backend", cfg.GRPCBackendAddr, "address of the target gRPC backend")
	fs.DurationVar(&cfg.GRPCDeadline, "grpc-deadline", cfg.GRPCDeadline, "per-request timeout when calling the gRPC backend")
	fs.DurationVar(&cfg.GRPCDialTimeout, "grpc-dial-timeout", cfg.GRPCDialTimeout, "timeout for establishing the gRPC connection")
	fs.DurationVar(&cfg.ShutdownTimeout, "shutdown-timeout", cfg.ShutdownTimeout, "maximum time to wait for graceful HTTP shutdown")
	fs.UintVar(&cfg.MaxGRPCRetries, "grpc-max-retries", cfg.MaxGRPCRetries, "maximum number of retry attempts for transient gRPC errors")
}

// Validate checks that all required configuration fields have valid values.
// Returns an error describing the first validation failure encountered.
// This should be called before using the Config to start the service.
func (cfg Config) Validate() error {
	if cfg.HTTPListenAddr == "" {
		return fmt.Errorf("http listen address must not be empty")
	}
	if cfg.GRPCBackendAddr == "" {
		return fmt.Errorf("grpc backend address must not be empty")
	}
	if cfg.GRPCDeadline <= 0 {
		return fmt.Errorf("grpc deadline must be positive")
	}
	if cfg.GRPCDialTimeout <= 0 {
		return fmt.Errorf("grpc dial timeout must be positive")
	}
	if cfg.ShutdownTimeout <= 0 {
		return fmt.Errorf("shutdown timeout must be positive")
	}
	return nil
}
