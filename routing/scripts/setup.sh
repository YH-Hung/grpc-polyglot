#!/usr/bin/env bash

#
# Setup script for APISIX gRPC Routing Demo
# This script builds and starts all services
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Print banner
print_banner() {
    print_msg "$BLUE" "╔════════════════════════════════════════════════════════╗"
    print_msg "$BLUE" "║   APISIX gRPC Routing Demo - Setup Script             ║"
    print_msg "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo
}

# Check prerequisites
check_prerequisites() {
    print_msg "$YELLOW" "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_msg "$RED" "Error: Docker is not installed"
        exit 1
    fi
    print_msg "$GREEN" "✓ Docker found: $(docker --version)"

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        print_msg "$RED" "Error: Docker Compose is not installed"
        exit 1
    fi
    print_msg "$GREEN" "✓ Docker Compose found: $(docker compose version)"

    # Check architecture
    ARCH=$(uname -m)
    print_msg "$GREEN" "✓ System architecture: $ARCH"

    if [ "$ARCH" != "arm64" ] && [ "$ARCH" != "aarch64" ]; then
        print_msg "$YELLOW" "Warning: This demo is optimized for ARM64 architecture"
        print_msg "$YELLOW" "You are running on $ARCH - builds may be slower"
    fi

    echo
}

# Build images
build_images() {
    print_msg "$YELLOW" "Building Docker images (this may take a while)..."
    # Platform is already specified in docker-compose.yml and Dockerfiles
    docker compose build
    print_msg "$GREEN" "✓ Images built successfully"
    echo
}

# Start services
start_services() {
    print_msg "$YELLOW" "Starting services..."
    docker compose up -d apisix go-server rust-server prometheus grafana
    print_msg "$GREEN" "✓ Services started"
    echo
}

# Wait for health checks
wait_for_health() {
    print_msg "$YELLOW" "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        local healthy=true

        for service in go-server rust-server apisix prometheus grafana; do
            if ! docker compose ps $service | grep -q "healthy"; then
                healthy=false
                break
            fi
        done

        if [ "$healthy" = true ]; then
            print_msg "$GREEN" "✓ All services are healthy"
            echo
            return 0
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_msg "$RED" "Timeout waiting for services to be healthy"
    docker compose ps
    return 1
}

# Display architecture info
display_architecture() {
    print_msg "$YELLOW" "Container architecture information:"

    for container in go-grpc-server rust-grpc-server apisix-gateway; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            arch=$(docker exec $container uname -m 2>/dev/null || echo "N/A")
            print_msg "$BLUE" "  $container: $arch"
        fi
    done

    echo
}

# Display access information
display_info() {
    print_msg "$GREEN" "╔════════════════════════════════════════════════════════╗"
    print_msg "$GREEN" "║              Setup Complete!                           ║"
    print_msg "$GREEN" "╚════════════════════════════════════════════════════════╝"
    echo
    print_msg "$BLUE" "Service URLs:"
    echo "  APISIX Proxy:       http://localhost:9080"
    echo "  APISIX Admin API:   http://localhost:9180"
    echo "  Prometheus:         http://localhost:9093"
    echo "  Grafana:            http://localhost:3000 (admin/admin)"
    echo "  Go Server Metrics:  http://localhost:9090/metrics"
    echo "  Rust Server Metrics: http://localhost:9092/metrics"
    echo
    print_msg "$YELLOW" "To run the interactive client:"
    echo "  docker compose run --rm client"
    echo
    print_msg "$YELLOW" "To test routes with grpcurl:"
    echo "  ./scripts/test-routes.sh"
    echo
    print_msg "$YELLOW" "To view logs:"
    echo "  docker compose logs -f [service-name]"
    echo
    print_msg "$YELLOW" "To stop all services:"
    echo "  docker compose down"
    echo
}

# Main execution
main() {
    print_banner
    check_prerequisites
    build_images
    start_services
    wait_for_health
    display_architecture
    display_info
}

main "$@"
