#!/usr/bin/env bash

#
# Test script for APISIX gRPC Routing Demo
# Tests routing behavior with and without headers
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
    print_msg "$BLUE" "║   APISIX gRPC Routing Demo - Route Testing            ║"
    print_msg "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo
}

# Check if grpcurl is installed
check_grpcurl() {
    if ! command -v grpcurl &> /dev/null; then
        print_msg "$YELLOW" "grpcurl not found, attempting to install..."
        if command -v go &> /dev/null; then
            go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
            export PATH="$PATH:$(go env GOPATH)/bin"
        else
            print_msg "$RED" "Error: Please install grpcurl manually"
            print_msg "$YELLOW" "See: https://github.com/fullstorydev/grpcurl"
            exit 1
        fi
    fi
    print_msg "$GREEN" "✓ grpcurl is installed"
    echo
}

# Test without header (should route to Go server)
test_without_header() {
    print_msg "$YELLOW" "Test 1: Request WITHOUT header (should route to Go server)"
    echo

    response=$(grpcurl -plaintext -d '{"name": "TestUser"}' \
        localhost:9080 helloworld.Greeter/SayHello)

    echo "$response" | jq .

    if echo "$response" | grep -q "Go Server"; then
        print_msg "$GREEN" "✓ Test PASSED: Routed to Go server"
    else
        print_msg "$RED" "✗ Test FAILED: Expected Go server"
    fi
    echo
}

# Test with v2 header (should route to Rust server)
test_with_v2_header() {
    print_msg "$YELLOW" "Test 2: Request WITH x-backend-version: v2 (should route to Rust server)"
    echo

    response=$(grpcurl -plaintext -H "x-backend-version: v2" \
        -d '{"name": "TestUser"}' localhost:9080 helloworld.Greeter/SayHello)

    echo "$response" | jq .

    if echo "$response" | grep -q "Rust Server"; then
        print_msg "$GREEN" "✓ Test PASSED: Routed to Rust server"
    else
        print_msg "$RED" "✗ Test FAILED: Expected Rust server"
    fi
    echo
}

# Test with wrong header value (should route to Go server as fallback)
test_with_wrong_header() {
    print_msg "$YELLOW" "Test 3: Request WITH x-backend-version: v1 (should route to Go server as fallback)"
    echo

    response=$(grpcurl -plaintext -H "x-backend-version: v1" \
        -d '{"name": "TestUser"}' localhost:9080 helloworld.Greeter/SayHello)

    echo "$response" | jq .

    if echo "$response" | grep -q "Go Server"; then
        print_msg "$GREEN" "✓ Test PASSED: Routed to Go server (fallback)"
    else
        print_msg "$RED" "✗ Test FAILED: Expected Go server as fallback"
    fi
    echo
}

# Load test
load_test() {
    print_msg "$YELLOW" "Test 4: Load test with alternating headers (10 requests)"
    echo

    local go_count=0
    local rust_count=0

    for i in {1..10}; do
        if [ $((i % 2)) -eq 0 ]; then
            # Even: use v2 header
            response=$(grpcurl -plaintext -H "x-backend-version: v2" \
                -d "{\"name\": \"User$i\"}" localhost:9080 helloworld.Greeter/SayHello 2>/dev/null)
            if echo "$response" | grep -q "Rust Server"; then
                rust_count=$((rust_count + 1))
            fi
        else
            # Odd: no header
            response=$(grpcurl -plaintext \
                -d "{\"name\": \"User$i\"}" localhost:9080 helloworld.Greeter/SayHello 2>/dev/null)
            if echo "$response" | grep -q "Go Server"; then
                go_count=$((go_count + 1))
            fi
        fi
        echo -n "."
    done

    echo
    echo
    print_msg "$BLUE" "Results:"
    echo "  Go Server requests:   $go_count/5"
    echo "  Rust Server requests: $rust_count/5"

    if [ $go_count -eq 5 ] && [ $rust_count -eq 5 ]; then
        print_msg "$GREEN" "✓ Load test PASSED: Correct distribution"
    else
        print_msg "$RED" "✗ Load test FAILED: Incorrect distribution"
    fi
    echo
}

# Main execution
main() {
    print_banner
    check_grpcurl
    test_without_header
    test_with_v2_header
    test_with_wrong_header
    load_test

    print_msg "$GREEN" "╔════════════════════════════════════════════════════════╗"
    print_msg "$GREEN" "║              Testing Complete!                         ║"
    print_msg "$GREEN" "╚════════════════════════════════════════════════════════╝"
}

main "$@"
