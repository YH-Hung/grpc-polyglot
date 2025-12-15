# Build stage
FROM --platform=linux/arm64 rust:1.83-alpine AS builder

# Install build dependencies
RUN apk add --no-cache musl-dev protobuf-dev protoc

WORKDIR /build

# Copy proto files
COPY proto/ /build/proto/

# Copy Rust server files
COPY servers/rust-server/ /build/servers/rust-server/

# Build the application
WORKDIR /build/servers/rust-server

# Add musl target for static linking on Alpine
RUN rustup target add aarch64-unknown-linux-musl

# Build with the musl target
RUN cargo build --release --target aarch64-unknown-linux-musl

# Runtime stage
FROM --platform=linux/arm64 alpine:latest

# Add ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/servers/rust-server/target/aarch64-unknown-linux-musl/release/server .

# Expose gRPC and metrics ports
EXPOSE 50052 9092

# Run the server
CMD ["./server"]
