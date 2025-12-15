# Build stage
FROM --platform=linux/arm64 golang:1.22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /build

# Copy proto files and modules
COPY proto/ /build/proto/
COPY client/ /build/client/

# Build the application
WORKDIR /build/client
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o grpc-client main.go

# Runtime stage
FROM --platform=linux/arm64 alpine:latest

# Add ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/client/grpc-client .

# Run the client interactively
CMD ["./grpc-client"]
