package httpserver

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
)

// metrics holds Prometheus metric collectors for the HTTP server.
// If metrics are disabled (registry is nil), all fields will be nil and
// observe() calls will be no-ops.
type metrics struct {
	// httpDuration tracks the duration of HTTP requests in seconds.
	// It's a histogram with labels for route (e.g., "/helloworld/SayHello")
	// and status code category (e.g., "2xx", "4xx", "5xx").
	httpDuration *prometheus.HistogramVec
}

// newMetrics creates and registers Prometheus metrics with the provided registry.
// If registry is nil, returns a metrics struct with all fields set to nil,
// which allows the code to work without metrics (all observe() calls become no-ops).
//
// Parameters:
//   - registry: Prometheus registry to register metrics with. If nil, metrics are disabled.
//
// Returns:
//   - *metrics: A metrics collector, or a no-op collector if registry is nil.
func newMetrics(registry *prometheus.Registry) *metrics {
	// If no registry provided, return a no-op metrics collector
	if registry == nil {
		return &metrics{}
	}

	// Create histogram metric for HTTP request duration
	m := &metrics{
		httpDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Namespace: "grpc_http1_proxy",                    // Metric namespace prefix
				Name:      "http_request_duration_seconds",         // Metric name
				Help:      "Time spent serving HTTP requests",     // Description for Prometheus
				Buckets:   prometheus.DefBuckets,                 // Default histogram buckets (0.005s to 10s)
			},
			[]string{"route", "status"}, // Labels: route path and status code category
		),
	}

	// Register the metric with the Prometheus registry
	// MustRegister panics if registration fails (e.g., duplicate metric name)
	registry.MustRegister(m.httpDuration)
	return m
}

// observe records the duration of an HTTP request for metrics collection.
// This is a no-op if metrics are disabled (m is nil or httpDuration is nil).
//
// Parameters:
//   - route: The HTTP route/path that was called (e.g., "/helloworld/SayHello")
//   - status: The HTTP status code returned (e.g., 200, 404, 500)
//   - d: The duration the request took to complete
func (m *metrics) observe(route string, status int, d time.Duration) {
	// Early return if metrics are disabled
	if m == nil || m.httpDuration == nil {
		return
	}

	// Record the observation with appropriate labels
	// The status is converted to a category (2xx, 4xx, 5xx) for better aggregation
	m.httpDuration.WithLabelValues(route, httpStatusLabel(status)).Observe(d.Seconds())
}

// httpStatusLabel converts an HTTP status code to a category label for metrics.
// This groups similar status codes together (e.g., all 4xx errors) which makes
// it easier to create alerts and dashboards.
//
// Parameters:
//   - status: HTTP status code (e.g., 200, 404, 500)
//
// Returns:
//   - string: Status code category ("2xx", "3xx", "4xx", "5xx", or "other")
func httpStatusLabel(status int) string {
	switch {
	case status >= 500:
		return "5xx" // Server errors
	case status >= 400:
		return "4xx" // Client errors
	case status >= 300:
		return "3xx" // Redirects
	case status >= 200:
		return "2xx" // Success
	default:
		return "other" // Unusual status codes (< 200)
	}
}

// middleware returns a Gin middleware function that tracks HTTP request duration.
// This middleware records metrics for all routes it's applied to.
//
// The middleware:
//   - Records the start time before processing the request
//   - Calls the next handler in the chain
//   - Records the duration and status code after the request completes
//
// Returns:
//   - gin.HandlerFunc: A Gin middleware function for metrics collection
func (m *metrics) middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Record start time
		start := time.Now()

		// Process request
		c.Next()

		// Record metrics after request completes
		// Use FullPath() to get the route pattern (e.g., "/helloworld/SayHello")
		// instead of c.Request.URL.Path which would give the actual path
		route := c.FullPath()
		if route == "" {
			route = c.Request.URL.Path // Fallback for routes without a pattern
		}
		m.observe(route, c.Writer.Status(), time.Since(start))
	}
}
