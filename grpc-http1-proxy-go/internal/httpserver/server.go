// Package httpserver provides an HTTP/1.1 server that accepts JSON requests
// and proxies them to a gRPC backend. It handles request/response translation
// between JSON and protobuf formats, and provides metrics and health check endpoints.
package httpserver

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"google.golang.org/protobuf/encoding/protojson"

	"github.com/yinghanhung/grpc-polyglot/grpc-http1-proxy-go/internal/pb"
)

// Greeter is an interface that abstracts the gRPC client, allowing the HTTP server
// to work with any implementation that provides the SayHello method.
// This interface enables easier testing by allowing mock implementations.
type Greeter interface {
	// SayHello sends a greeting request to the gRPC backend and returns the response.
	SayHello(ctx context.Context, req *pb.HelloRequest) (*pb.HelloReply, error)
}

// Config holds configuration parameters for the HTTP server.
type Config struct {
	ListenAddr        string        // Address and port to bind the server (e.g., ":8080")
	MetricsPath       string        // URL path for Prometheus metrics endpoint (default: "/metrics")
	HealthPath        string        // URL path for health check endpoint (default: "/healthz")
	ReadHeaderTimeout time.Duration // Maximum time to wait for request headers (default: 5s)
}

// Server wraps an HTTP server that proxies requests to a gRPC backend.
// It handles routing, request/response translation, and metrics collection.
type Server struct {
	cfg     Config        // Server configuration
	srv     *http.Server // Underlying HTTP server
	handler *handler     // Request handler with business logic
}

// New creates and configures a new HTTP server with the provided settings.
// It sets up routing, request handlers, metrics collection, and health checks.
//
// Parameters:
//   - cfg: Server configuration. ListenAddr is required.
//   - greeter: gRPC client implementation for making backend calls. Must not be nil.
//   - logger: Logger for error and debug messages. If nil, a no-op logger is used.
//   - registry: Prometheus metrics registry. If nil, metrics are disabled.
//
// Returns:
//   - *Server: A configured server ready to accept connections.
//   - error: Non-nil if configuration is invalid.
//
// The server registers the following routes:
//   - POST /helloworld/SayHello: Main proxy endpoint for greeting requests
//   - GET /healthz: Health check endpoint (returns "ok")
//   - GET /metrics: Prometheus metrics endpoint (if registry is provided)
func New(cfg Config, greeter Greeter, logger *slog.Logger, registry *prometheus.Registry) (*Server, error) {
	// Validate required configuration
	if cfg.ListenAddr == "" {
		return nil, errors.New("httpserver: listen address is required")
	}
	if greeter == nil {
		return nil, errors.New("httpserver: greeter client is required")
	}

	// Apply defaults for optional fields
	if logger == nil {
		logger = slog.New(slog.NewTextHandler(io.Discard, nil))
	}
	if cfg.ReadHeaderTimeout == 0 {
		cfg.ReadHeaderTimeout = 5 * time.Second
	}

	// Initialize metrics collection (may be nil if registry is nil)
	metrics := newMetrics(registry)

	// Create request handler with JSON marshalling configuration
	h := &handler{
		greeter: greeter,
		logger:  logger,
		metrics: metrics,
		// Configure JSON marshaller to use camelCase (not proto field names)
		// and omit empty fields for cleaner JSON output
		marshaller: protojson.MarshalOptions{
			UseProtoNames:   false, // Use JSON names (camelCase) instead of proto names
			EmitUnpopulated: false, // Don't include zero-value fields in output
		},
		// Configure JSON unmarshaller to ignore unknown fields for forward compatibility
		unmarshaller: protojson.UnmarshalOptions{
			DiscardUnknown: true, // Ignore fields not present in the proto definition
		},
	}

	// Set up HTTP routing
	mux := http.NewServeMux()
	// Main proxy endpoint: accepts JSON, calls gRPC, returns JSON
	mux.HandleFunc("/helloworld/SayHello", h.hello)

	// Health check endpoint: simple endpoint for load balancers and monitoring
	healthPath := cfg.HealthPath
	if healthPath == "" {
		healthPath = "/healthz"
	}
	mux.HandleFunc(healthPath, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})

	// Prometheus metrics endpoint: exposes metrics in Prometheus format
	if registry != nil {
		metricsPath := cfg.MetricsPath
		if metricsPath == "" {
			metricsPath = "/metrics"
		}
		mux.Handle(metricsPath, promhttp.HandlerFor(registry, promhttp.HandlerOpts{}))
	}

	// Create HTTP server with configured timeout
	srv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           mux,
		ReadHeaderTimeout: cfg.ReadHeaderTimeout, // Prevent slowloris attacks
	}

	return &Server{cfg: cfg, srv: srv, handler: h}, nil
}

// Start begins listening for HTTP requests on the configured address.
// This method blocks until the server is stopped via Shutdown() or encounters an error.
// It should typically be called in a goroutine.
//
// Returns:
//   - error: Non-nil if the server fails to start or encounters a fatal error.
//     Returns nil if the server is gracefully shut down.
func (s *Server) Start() error {
	if err := s.srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

// Shutdown gracefully stops the HTTP server, allowing in-flight requests to complete.
// It stops accepting new connections and waits for existing requests to finish,
// up to the timeout specified in ctx.
//
// Parameters:
//   - ctx: Context with timeout for the shutdown operation. The server will wait
//     for this duration before forcefully closing connections.
//
// Returns:
//   - error: Non-nil if shutdown fails or the context deadline is exceeded.
func (s *Server) Shutdown(ctx context.Context) error {
	return s.srv.Shutdown(ctx)
}

// handler contains the business logic for processing HTTP requests and translating
// them into gRPC calls. It handles JSON/protobuf conversion, error handling, and metrics.
type handler struct {
	greeter      Greeter                    // gRPC client for making backend calls
	logger       *slog.Logger               // Logger for error messages
	metrics      *metrics                   // Metrics collector (may be nil)
	marshaller   protojson.MarshalOptions   // Options for converting protobuf to JSON
	unmarshaller protojson.UnmarshalOptions // Options for converting JSON to protobuf
}

// hello handles POST requests to /helloworld/SayHello.
// It accepts a JSON request body, converts it to a protobuf message, calls the gRPC backend,
// and returns the response as JSON.
//
// Request format:
//   POST /helloworld/SayHello
//   Content-Type: application/json
//   Body: {"name": "Alice"}
//
// Response format:
//   Status: 200 OK
//   Content-Type: application/json
//   Body: {"message": "Hello, Alice"}
//
// Error responses:
//   - 405 Method Not Allowed: If request method is not POST
//   - 400 Bad Request: If request body is invalid or cannot be parsed
//   - 502 Bad Gateway: If the gRPC backend call fails
//   - 500 Internal Server Error: If response cannot be marshalled to JSON
func (h *handler) hello(w http.ResponseWriter, r *http.Request) {
	// Track request duration for metrics
	start := time.Now()
	statusCode := http.StatusOK
	defer func() {
		// Record metrics after request completes (even if it failed)
		if h.metrics != nil {
			h.metrics.observe("/helloworld/SayHello", statusCode, time.Since(start))
		}
	}()

	// Only accept POST requests
	if r.Method != http.MethodPost {
		statusCode = http.StatusMethodNotAllowed
		http.Error(w, "method not allowed", statusCode)
		return
	}

	// Read request body with a size limit (1MB) to prevent memory exhaustion
	// LimitReader ensures we don't read more than 1MB even if Content-Length is larger
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		statusCode = http.StatusBadRequest
		http.Error(w, "invalid body", statusCode)
		return
	}

	// Parse JSON request body into protobuf message
	req := &pb.HelloRequest{}
	if err := h.unmarshaller.Unmarshal(body, req); err != nil {
		statusCode = http.StatusBadRequest
		http.Error(w, "invalid JSON payload", statusCode)
		return
	}

	// Call the gRPC backend with the parsed request
	// The context from the HTTP request is passed through, allowing cancellation
	// if the client disconnects
	resp, err := h.greeter.SayHello(r.Context(), req)
	if err != nil {
		// gRPC call failed - return 502 to indicate upstream error
		statusCode = http.StatusBadGateway
		http.Error(w, "upstream error", statusCode)
		h.logger.Error("gRPC call failed", slog.String("err", err.Error()))
		return
	}

	// Convert protobuf response to JSON
	data, err := h.marshaller.Marshal(resp)
	if err != nil {
		// This should rarely happen, but handle it gracefully
		statusCode = http.StatusInternalServerError
		http.Error(w, "failed to marshal response", statusCode)
		return
	}

	// Write successful response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}
