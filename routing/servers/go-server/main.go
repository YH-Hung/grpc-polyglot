package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	pb "github.com/yinghanhung/grpc-polyglot/routing/proto/go/helloworld"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
)

const (
	grpcPort    = ":50051"
	metricsPort = ":9090"
	serverName  = "Go Server"
	version     = "v1"
)

// Prometheus metrics
var (
	requestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "grpc_requests_total",
			Help: "Total number of gRPC requests",
		},
		[]string{"method", "status"},
	)
	requestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "grpc_request_duration_seconds",
			Help:    "Duration of gRPC requests in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method"},
	)
	activeConnections = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "grpc_active_connections",
			Help: "Number of active gRPC connections",
		},
	)
)

func init() {
	// Register Prometheus metrics
	prometheus.MustRegister(requestsTotal)
	prometheus.MustRegister(requestDuration)
	prometheus.MustRegister(activeConnections)
}

// server is used to implement helloworld.GreeterServer
type server struct {
	pb.UnimplementedGreeterServer
}

// SayHello implements helloworld.GreeterServer
func (s *server) SayHello(ctx context.Context, in *pb.HelloRequest) (*pb.HelloReply, error) {
	start := time.Now()

	activeConnections.Inc()
	defer activeConnections.Dec()

	log.Printf("Received request from: %s", in.GetName())

	// Get architecture info
	arch := fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH)

	reply := &pb.HelloReply{
		Message:        fmt.Sprintf("Hello %s! Greetings from %s %s", in.GetName(), serverName, version),
		ServerName:     serverName,
		ServerVersion:  version,
		Architecture:   arch,
	}

	// Record metrics
	requestsTotal.WithLabelValues("SayHello", "success").Inc()
	requestDuration.WithLabelValues("SayHello").Observe(time.Since(start).Seconds())

	return reply, nil
}

// startMetricsServer starts the HTTP server for Prometheus metrics
func startMetricsServer() {
	http.Handle("/metrics", promhttp.Handler())
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	log.Printf("Metrics server listening on %s", metricsPort)
	if err := http.ListenAndServe(metricsPort, nil); err != nil {
		log.Fatalf("Failed to start metrics server: %v", err)
	}
}

func main() {
	// Log startup info
	log.Printf("Starting %s %s", serverName, version)
	log.Printf("Runtime architecture: %s/%s", runtime.GOOS, runtime.GOARCH)

	// Start metrics server in a goroutine
	go startMetricsServer()

	// Create gRPC server
	lis, err := net.Listen("tcp", grpcPort)
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterGreeterServer(grpcServer, &server{})

	// Register health service
	healthServer := health.NewServer()
	grpc_health_v1.RegisterHealthServer(grpcServer, healthServer)
	healthServer.SetServingStatus("", grpc_health_v1.HealthCheckResponse_SERVING)

	log.Printf("gRPC server listening on %s", grpcPort)

	// Handle graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down gracefully...")
		grpcServer.GracefulStop()
	}()

	// Start serving
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
