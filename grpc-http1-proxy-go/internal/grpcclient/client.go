// Package grpcclient provides a gRPC client wrapper for communicating with the
// HelloWorld Greeter service. It handles connection management, retries, timeouts,
// and provides a clean interface for making gRPC calls.
package grpcclient

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"time"

	grpc_retry "github.com/grpc-ecosystem/go-grpc-middleware/v2/interceptors/retry"
	"google.golang.org/grpc"
	"google.golang.org/grpc/backoff"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"

	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/pb"
)

// Config holds configuration parameters for the gRPC client connection.
type Config struct {
	Address     string        // Target gRPC server address (e.g., "localhost:50051")
	DialTimeout time.Duration // Maximum time to wait when establishing the connection
	Deadline    time.Duration // Maximum time to wait for each RPC call to complete
	MaxRetries  uint          // Maximum number of retry attempts for transient errors
}

// Client wraps a gRPC connection and provides methods to call the Greeter service.
// It automatically handles retries, timeouts, and connection lifecycle management.
// The client should be closed when no longer needed to free up resources.
type Client struct {
	cfg     Config              // Client configuration
	conn    *grpc.ClientConn    // Underlying gRPC connection
	greeter pb.GreeterClient    // Generated gRPC client stub
	logger  *slog.Logger        // Logger for error and debug messages
}

// New creates a new gRPC client with the provided configuration.
// It establishes a connection to the gRPC backend and configures retry logic
// for handling transient failures.
//
// Parameters:
//   - ctx: Context for the connection establishment. If nil, context.Background() is used.
//   - cfg: Client configuration. Address is required; other fields have defaults.
//   - logger: Logger instance. If nil, a no-op logger is used.
//
// Returns:
//   - *Client: A configured client ready to make gRPC calls.
//   - error: Non-nil if connection establishment fails.
//
// The client will automatically retry on transient errors (Unavailable, ResourceExhausted,
// DeadlineExceeded) up to MaxRetries times. Each retry uses exponential backoff.
func New(ctx context.Context, cfg Config, logger *slog.Logger) (*Client, error) {
	// Use background context if none provided
	if ctx == nil {
		ctx = context.Background()
	}

	// Validate required configuration
	if cfg.Address == "" {
		return nil, errors.New("grpcclient: address must be provided")
	}

	// Apply defaults for optional fields
	if cfg.DialTimeout <= 0 {
		cfg.DialTimeout = 5 * time.Second
	}
	if cfg.Deadline <= 0 {
		cfg.Deadline = 5 * time.Second
	}
	if logger == nil {
		logger = slog.New(slog.NewTextHandler(io.Discard, nil))
	}

	// Configure retry behavior for transient errors
	retryOpts := []grpc_retry.CallOption{
		// Retry on these gRPC status codes:
		// - Unavailable: Service temporarily unavailable
		// - ResourceExhausted: Rate limiting or resource constraints
		// - DeadlineExceeded: Request timeout (may be transient)
		grpc_retry.WithCodes(codes.Unavailable, codes.ResourceExhausted, codes.DeadlineExceeded),
		// Each retry attempt has its own deadline
		grpc_retry.WithPerRetryTimeout(cfg.Deadline),
	}
	if cfg.MaxRetries > 0 {
		retryOpts = append(retryOpts, grpc_retry.WithMax(cfg.MaxRetries))
	}

	// Create a context with timeout for the dial operation
	dctx, cancel := context.WithTimeout(ctx, cfg.DialTimeout)
	defer cancel()

	// Establish gRPC connection with retry middleware and connection parameters
	conn, err := grpc.DialContext(
		dctx,
		cfg.Address,
		// Use insecure credentials (no TLS) - suitable for local development
		// In production, use grpc.WithTransportCredentials() with proper TLS config
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		// Add retry interceptors for both unary and streaming calls
		grpc.WithChainUnaryInterceptor(grpc_retry.UnaryClientInterceptor(retryOpts...)),
		grpc.WithChainStreamInterceptor(grpc_retry.StreamClientInterceptor(retryOpts...)),
		// Configure connection backoff: start with 200ms, multiply by 1.6, max 2s
		grpc.WithConnectParams(grpc.ConnectParams{
			MinConnectTimeout: cfg.DialTimeout,
			Backoff: backoff.Config{
				BaseDelay:  200 * time.Millisecond,
				Multiplier: 1.6,
				MaxDelay:   2 * time.Second,
			},
		}),
	)
	if err != nil {
		return nil, err
	}

	return &Client{
		cfg:     cfg,
		conn:    conn,
		greeter: pb.NewGreeterClient(conn),
		logger:  logger,
	}, nil
}

// SayHello calls the SayHello RPC method on the Greeter service.
// It applies the configured deadline to the request and handles context cancellation.
//
// Parameters:
//   - ctx: Request context. If nil, context.Background() is used. The context can be
//     used to cancel the request or set request-scoped values.
//   - req: The HelloRequest containing the name to greet. Must not be nil.
//
// Returns:
//   - *pb.HelloReply: The greeting response from the server.
//   - error: Non-nil if the RPC call fails (network error, timeout, server error, etc.).
//
// The method will automatically retry on transient errors according to the client's
// retry configuration. If the context is cancelled or the deadline is exceeded,
// the call will fail immediately.
func (c *Client) SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error) {
	// Use background context if none provided
	if ctx == nil {
		ctx = context.Background()
	}

	// Validate request
	if req == nil {
		return nil, errors.New("grpcclient: request must not be nil")
	}

	// Apply deadline if configured
	callCtx := ctx
	if c.cfg.Deadline > 0 {
		var cancel context.CancelFunc
		callCtx, cancel = context.WithTimeout(ctx, c.cfg.Deadline)
		defer cancel() // Ensure the cancel function is called to free resources
	}

	// Make the gRPC call (retries are handled by the interceptor)
	return c.greeter.SayHello(callCtx, req)
}

// Close closes the underlying gRPC connection and releases associated resources.
// This should be called when the client is no longer needed to prevent resource leaks.
// It is safe to call Close multiple times or on a nil client.
//
// Returns:
//   - error: Non-nil if closing the connection fails (rare).
func (c *Client) Close() error {
	if c == nil || c.conn == nil {
		return nil
	}
	return c.conn.Close()
}
