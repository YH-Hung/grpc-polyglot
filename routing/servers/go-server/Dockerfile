# Build stage
FROM --platform=linux/arm64 golang:1.22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /build

# Copy proto files and modules
COPY proto/ /build/proto/
COPY servers/go-server/ /build/servers/go-server/

# Build the application
WORKDIR /build/servers/go-server
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o grpc-server main.go

# Runtime stage
FROM --platform=linux/arm64 alpine:latest

# Add ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/servers/go-server/grpc-server .

# Expose gRPC and metrics ports
EXPOSE 50051 9090

# Run the server
CMD ["./grpc-server"]
