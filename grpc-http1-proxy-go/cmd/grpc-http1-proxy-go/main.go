// Package main is the entry point for the gRPC HTTP/1 proxy service.
// It initializes the configuration, creates the gRPC client and HTTP server,
// and handles graceful shutdown on termination signals.
package main

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"

	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/config"
	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/grpcclient"
	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/httpserver"
)

// main is the application entry point. It performs the following steps:
// 1. Load configuration from environment variables
// 2. Parse command-line flags to override environment variables
// 3. Validate the configuration
// 4. Initialize logging
// 5. Create and connect the gRPC client
// 6. Create and start the HTTP server
// 7. Wait for shutdown signals (SIGINT or SIGTERM)
// 8. Gracefully shut down the server
func main() {
	// Step 1: Load configuration from environment variables
	// This sets defaults and overrides them with any environment variables that are set
	cfg := config.FromEnv()

	// Step 2: Set up command-line flag parsing
	// Flags will override environment variables, allowing runtime configuration
	fs := flag.NewFlagSet(os.Args[0], flag.ExitOnError)
	cfg.BindFlags(fs)
	if err := fs.Parse(os.Args[1:]); err != nil {
		slog.Error("failed to parse flags", slog.String("err", err.Error()))
		os.Exit(2) // Exit code 2 indicates invalid command-line arguments
	}

	// Step 3: Validate configuration to ensure all required fields are set correctly
	if err := cfg.Validate(); err != nil {
		slog.Error("invalid configuration", slog.String("err", err.Error()))
		os.Exit(2)
	}

	// Step 4: Initialize structured logging
	// Using slog (structured logging) which is part of the standard library in Go 1.21+
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	// Step 5: Create gRPC client connection to the backend service
	// This establishes a connection pool and configures retry logic
	ctx := context.Background()
	grpcClient, err := grpcclient.New(ctx, grpcclient.Config{
		Address:     cfg.GRPCBackendAddr,
		DialTimeout: cfg.GRPCDialTimeout,
		Deadline:    cfg.GRPCDeadline,
		MaxRetries:  cfg.MaxGRPCRetries,
	}, logger)
	if err != nil {
		logger.Error("failed to create gRPC client", slog.String("err", err.Error()))
		os.Exit(1) // Exit code 1 indicates a runtime error
	}
	// Ensure the connection is closed when the program exits
	defer grpcClient.Close()

	// Step 6: Create Prometheus metrics registry
	// This will collect metrics from the HTTP server and gRPC client
	registry := prometheus.NewRegistry()

	// Step 7: Create HTTP server that will proxy requests to gRPC backend
	server, err := httpserver.New(httpserver.Config{
		ListenAddr:        cfg.HTTPListenAddr,
		MetricsPath:       cfg.MetricsPath,
		HealthPath:        cfg.HealthPath,
		ReadHeaderTimeout: 5 * time.Second, // Prevent slowloris attacks
	}, grpcClient, logger, registry)
	if err != nil {
		logger.Error("failed to create HTTP server", slog.String("err", err.Error()))
		os.Exit(1)
	}

	// Step 8: Start the HTTP server in a goroutine
	// This allows the main goroutine to handle shutdown signals
	go func() {
		logger.Info("HTTP proxy listening", slog.String("addr", cfg.HTTPListenAddr))
		if err := server.Start(); err != nil {
			// Log error but don't exit - the main goroutine will handle shutdown
			logger.Error("HTTP server stopped with error", slog.String("err", err.Error()))
		}
	}()

	// Step 9: Set up signal handling for graceful shutdown
	// Create a channel to receive OS signals (SIGINT from Ctrl+C, SIGTERM from kill)
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Step 10: Wait for shutdown signal
	// This blocks until the process receives SIGINT or SIGTERM
	sig := <-sigCh
	logger.Info("received shutdown signal", slog.String("signal", sig.String()))

	// Step 11: Gracefully shut down the HTTP server
	// Create a context with timeout to limit how long we wait for in-flight requests
	ctxShutdown, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	if err := server.Shutdown(ctxShutdown); err != nil {
		logger.Error("graceful shutdown failed", slog.String("err", err.Error()))
		// Note: We don't exit with an error code here because we're already shutting down
		// The defer statement will ensure the gRPC connection is closed
	}
}
