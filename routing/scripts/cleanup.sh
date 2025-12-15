#!/usr/bin/env bash

#
# Cleanup script for APISIX gRPC Routing Demo
# Stops and removes all containers, networks, and volumes
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_banner() {
    print_msg "$BLUE" "╔════════════════════════════════════════════════════════╗"
    print_msg "$BLUE" "║   APISIX gRPC Routing Demo - Cleanup Script           ║"
    print_msg "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo
}

# Stop and remove containers
stop_containers() {
    print_msg "$YELLOW" "Stopping containers..."
    docker compose down
    print_msg "$GREEN" "✓ Containers stopped and removed"
    echo
}

# Remove volumes
remove_volumes() {
    print_msg "$YELLOW" "Removing volumes..."
    docker compose down -v
    print_msg "$GREEN" "✓ Volumes removed"
    echo
}

# Remove images (optional)
remove_images() {
    print_msg "$YELLOW" "Do you want to remove built images? (y/n)"
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_msg "$YELLOW" "Removing images..."
        docker compose down --rmi local
        print_msg "$GREEN" "✓ Images removed"
    else
        print_msg "$BLUE" "Skipping image removal"
    fi
    echo
}

# Display status
display_status() {
    print_msg "$GREEN" "╔════════════════════════════════════════════════════════╗"
    print_msg "$GREEN" "║              Cleanup Complete!                         ║"
    print_msg "$GREEN" "╚════════════════════════════════════════════════════════╝"
    echo
    print_msg "$BLUE" "To start again, run:"
    echo "  ./scripts/setup.sh"
    echo
}

# Main execution
main() {
    print_banner
    stop_containers
    remove_volumes
    remove_images
    display_status
}

main "$@"
