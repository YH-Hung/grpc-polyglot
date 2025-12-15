# APISIX gRPC Routing Demo

A comprehensive demonstration of header-based gRPC routing using Apache APISIX, featuring polyglot backend servers (Go and Rust), full observability stack (Prometheus + Grafana), and an interactive testing client.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Client Applications                        │
│                   (Interactive Go Client)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ gRPC Request
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APISIX Gateway                              │
│              (Header-based Routing Logic)                        │
│                                                                  │
│  Route 1 (Priority 10): x-backend-version: v2  ──►  Rust       │
│  Route 2 (Priority 1):  Default (no header)    ──►  Go         │
└─────────────┬───────────────────────┬────────────────────────────┘
              │                       │
              │                       │
              ▼                       ▼
┌──────────────────────┐   ┌──────────────────────┐
│   Go gRPC Server     │   │  Rust gRPC Server    │
│   (v1 - Port 50051)  │   │  (v2 - Port 50052)   │
│   - Greeter Service  │   │  - Greeter Service   │
│   - Prometheus       │   │  - Prometheus        │
└──────────────────────┘   └──────────────────────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
           ┌─────────────────────────────┐
           │     Prometheus              │
           │  (Metrics Collection)       │
           └─────────────┬───────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │       Grafana               │
           │  (Metrics Visualization)    │
           └─────────────────────────────┘
```

## Features

- **Header-Based Routing**: Route gRPC requests to different backends based on HTTP headers
- **Polyglot Architecture**: Go (v1) and Rust (v2) gRPC servers demonstrating language diversity
- **ARM64 Optimized**: All Docker images target linux/arm64 for Apple Silicon compatibility
- **Full Observability**: Prometheus metrics and Grafana dashboards for monitoring
- **Interactive Client**: Menu-driven Go client for easy testing
- **Health Checks**: Comprehensive health checking for all services
- **Automated Scripts**: Setup, testing, and cleanup automation

## Prerequisites

- Docker (with Compose V2)
- ARM64 architecture (Apple Silicon) recommended
- 4GB+ RAM available for Docker
- Ports available: 9080, 9090, 9091, 9092, 9093, 9180, 3000, 50051, 50052

Optional:
- `grpcurl` for manual testing
- `jq` for JSON formatting

## Quick Start

### 1. Setup and Start All Services

```bash
./scripts/setup.sh
```

This script will:
- Check prerequisites
- Build all Docker images (ARM64)
- Start all services (APISIX, Go server, Rust server, Prometheus, Grafana)
- Wait for health checks
- Display service URLs and architecture information

### 2. Run the Interactive Client

```bash
docker compose run --rm client
```

The interactive client provides a menu with options:
1. Send request WITHOUT header (routes to Go server)
2. Send request WITH x-backend-version: v2 (routes to Rust server)
3. Send request with custom header value
4. Run load test with N alternating requests
5. Exit

### 3. Test Routing with grpcurl (Optional)

```bash
./scripts/test-routes.sh
```

Or manually:

```bash
# Test 1: No header → Go server
grpcurl -plaintext -d '{"name": "Alice"}' \
  localhost:9080 helloworld.Greeter/SayHello

# Test 2: With v2 header → Rust server
grpcurl -plaintext -H "x-backend-version: v2" \
  -d '{"name": "Bob"}' \
  localhost:9080 helloworld.Greeter/SayHello
```

### 4. View Metrics and Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9093
- **APISIX Metrics**: http://localhost:9091/apisix/prometheus/metrics
- **Go Server Metrics**: http://localhost:9090/metrics
- **Rust Server Metrics**: http://localhost:9092/metrics

### 5. Cleanup

```bash
./scripts/cleanup.sh
```

## Routing Logic

APISIX evaluates routes by priority (higher number = higher priority):

| Priority | Header Condition | Target Server | Use Case |
|----------|------------------|---------------|----------|
| 10 | `x-backend-version: v2` | Rust Server (v2) | Explicit v2 requests |
| 1 | No header or any other value | Go Server (v1) | Default/fallback |

### Example Routing Scenarios

```
Request: {"name": "Alice"}
Header: (none)
→ Routes to: Go Server v1

Request: {"name": "Bob"}
Header: x-backend-version: v2
→ Routes to: Rust Server v2

Request: {"name": "Charlie"}
Header: x-backend-version: v1
→ Routes to: Go Server v1 (fallback)
```

## Project Structure

```
routing/
├── README.md                          # This file
├── docker-compose.yml                 # Service orchestration
├── proto/
│   ├── helloworld.proto              # gRPC service definition
│   └── go/helloworld/                # Generated Go code
├── servers/
│   ├── go-server/
│   │   ├── main.go                   # Go gRPC server
│   │   ├── Dockerfile                # ARM64 Docker build
│   │   └── go.mod                    # Go dependencies
│   └── rust-server/
│       ├── src/main.rs               # Rust gRPC server
│       ├── Cargo.toml                # Rust dependencies
│       ├── build.rs                  # Proto build script
│       └── Dockerfile                # ARM64 Docker build
├── client/
│   ├── main.go                       # Interactive Go client
│   ├── Dockerfile                    # ARM64 Docker build
│   └── go.mod                        # Go dependencies
├── apisix/
│   ├── config.yaml                   # APISIX configuration
│   └── apisix.yaml                   # Routes and upstreams
├── prometheus/
│   └── prometheus.yml                # Prometheus scrape config
├── grafana/
│   ├── provisioning/                 # Auto-provisioning
│   └── dashboards/                   # Pre-built dashboards
└── scripts/
    ├── setup.sh                      # Automated setup
    ├── test-routes.sh                # Automated testing
    └── cleanup.sh                    # Cleanup script
```

## Service Details

### APISIX Gateway
- **Port**: 9080 (gRPC proxy), 9180 (Admin API), 9091 (Prometheus)
- **Mode**: Standalone (file-based configuration)
- **Features**: Header-based routing, health checks, Prometheus metrics

### Go gRPC Server (v1)
- **Port**: 50051 (gRPC), 9090 (metrics)
- **Language**: Go 1.22
- **Response**: Identifies as "Go Server v1"
- **Metrics**: request_total, request_duration, active_connections

### Rust gRPC Server (v2)
- **Port**: 50052 (gRPC), 9092 (metrics)
- **Language**: Rust 1.75 (using Tonic)
- **Response**: Identifies as "Rust Server v2"
- **Metrics**: request_total, request_duration, active_connections

### Prometheus
- **Port**: 9093 (host) → 9090 (container)
- **Scrape Interval**: 15 seconds
- **Targets**: APISIX, Go server, Rust server

### Grafana
- **Port**: 3000
- **Credentials**: admin/admin
- **Dashboards**: Pre-configured APISIX gRPC Routing dashboard

## Observability

### Prometheus Metrics

All services expose Prometheus metrics:

**gRPC Servers (Go & Rust)**:
- `grpc_requests_total{method, status}` - Total requests counter
- `grpc_request_duration_seconds{method}` - Request duration histogram
- `grpc_active_connections` - Active connection gauge

**APISIX**:
- `apisix_http_status` - HTTP status codes
- `apisix_bandwidth` - Bandwidth usage
- `apisix_http_latency` - Request latency

### Grafana Dashboards

Access Grafana at http://localhost:3000 (admin/admin)

Pre-configured dashboard shows:
- Total requests by server (Go vs Rust)
- Request duration percentiles (p50, p95, p99)
- Active connections
- Error rates
- Header-based routing distribution

### Query Examples

```promql
# Request rate by server
sum by (service) (rate(grpc_requests_total[1m]))

# P95 latency
histogram_quantile(0.95, sum(rate(grpc_request_duration_seconds_bucket[1m])) by (le, service))

# Go vs Rust request distribution
sum(grpc_requests_total{service="go-server"}) /
sum(grpc_requests_total)
```

## Troubleshooting

### Services Not Starting

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f [service-name]

# Restart specific service
docker compose restart [service-name]
```

### Health Check Failures

```bash
# Check Go server health
curl http://localhost:9090/health

# Check Rust server health
curl http://localhost:9092/health

# Check APISIX metrics endpoint
curl http://localhost:9091/apisix/prometheus/metrics
```

### Routing Not Working

```bash
# Check APISIX logs
docker compose logs apisix

# Verify routes via Admin API
curl http://localhost:9180/apisix/admin/routes \
  -H 'X-API-KEY: edd1c9f034335f136f87ad84b625c8f1'

# Test direct connection to servers
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50052 list
```

### ARM64 Build Issues

If you're not on ARM64:
```bash
# Force platform in docker-compose.yml
# Already configured with platform: linux/arm64

# Or build without platform specification
docker compose build --no-cache
```

### Port Conflicts

If ports are already in use:
```bash
# Find process using port
lsof -i :9080

# Kill process or change port in docker-compose.yml
```

## Advanced Usage

### Custom Routing Rules

Edit [apisix/apisix.yaml](apisix/apisix.yaml) to add new routes:

```yaml
routes:
  - id: custom-route
    uri: /helloworld.Greeter/SayHello
    priority: 5
    vars:
      - - http_x_custom_header
        - "=="
        - "custom-value"
    upstream_id: custom-upstream
```

### Adding More Servers

1. Create new server directory in `servers/`
2. Add Dockerfile and implementation
3. Add service to `docker-compose.yml`
4. Add upstream and route to `apisix/apisix.yaml`
5. Add metrics scrape to `prometheus/prometheus.yml`

### Load Testing

```bash
# Using ghz (install: go install github.com/bojand/ghz/cmd/ghz@latest)
ghz --insecure --proto proto/helloworld.proto \
  --call helloworld.Greeter.SayHello \
  -d '{"name":"LoadTest"}' \
  -n 1000 -c 10 \
  localhost:9080
```

## Development

### Rebuilding After Code Changes

```bash
# Rebuild specific service
docker compose build [service-name]

# Restart service
docker compose up -d [service-name]
```

### Regenerating Proto Code

**Go**:
```bash
cd proto
protoc --go_out=go --go_opt=paths=source_relative \
  --go-grpc_out=go --go-grpc_opt=paths=source_relative \
  helloworld.proto
```

**Rust**: Automatically handled by `build.rs` during cargo build

## Technical Details

### ARM64 Platform Targeting

All Dockerfiles use explicit platform targeting:

```dockerfile
FROM --platform=linux/arm64 golang:1.22-alpine AS builder
```

Build commands specify ARM64:
- Go: `GOARCH=arm64`
- Rust: `aarch64-unknown-linux-musl` target

### gRPC Protocol

APISIX communicates with backends using native gRPC (HTTP/2):
- Upstream scheme: `grpc://`
- No transcoding (gRPC-to-gRPC pass-through)
- Full support for metadata (headers)

### Health Checks

Docker Compose health checks ensure proper startup order:
- Go/Rust servers: HTTP /health endpoint
- APISIX: Prometheus metrics endpoint
- Prometheus/Grafana: Built-in health endpoints

## References

- [APISIX Documentation](https://apisix.apache.org/docs/)
- [gRPC Go Quick Start](https://grpc.io/docs/languages/go/quickstart/)
- [Tonic (Rust gRPC)](https://github.com/hyperium/tonic)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

## License

Apache License 2.0 (same as APISIX)

## Contributing

This is a demonstration project. Feel free to:
- Fork and experiment
- Add new routing scenarios
- Implement additional server languages
- Enhance observability dashboards
- Share improvements and learnings
