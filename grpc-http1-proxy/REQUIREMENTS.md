# COMPREHENSIVE REQUIREMENTS DOCUMENT: gRPC HTTP/1.1 PROXY
## High-Concurrency, Non-Blocking Architecture

---

## EXECUTIVE SUMMARY

This document specifies the requirements for a **high-performance, non-blocking gRPC HTTP/1.1 Proxy** that enables HTTP/1.1 clients to communicate with gRPC servers through protocol translation.

### Core Design Principle
**CONCURRENCY AND NON-BLOCKING I/O ARE THE PRIMARY ARCHITECTURAL REQUIREMENTS**

The system must handle thousands of concurrent requests efficiently without blocking threads, using async I/O patterns, reactive programming, or coroutines to maximize throughput and minimize resource consumption.

### Key Performance Targets
- **Throughput**: 10,000+ requests/second per instance
- **Concurrency**: Support 10,000+ concurrent connections
- **Latency**: P99 < 50ms (including proxy overhead)
- **Resource Efficiency**: < 100 threads for 10,000 concurrent requests
- **Non-Blocking**: Zero blocking I/O operations in critical path

---

## TABLE OF CONTENTS

1. [Project Overview & Purpose](#1-project-overview--purpose)
2. [Concurrency & Non-Blocking Architecture](#2-concurrency--non-blocking-architecture) ⭐ **PRIMARY FOCUS**
   - 2.8 [Request Cancellation & Propagation](#28-request-cancellation--propagation) 🔴 **CRITICAL**
3. [System Architecture](#3-system-architecture)
4. [Core Features & Functionality](#4-core-features--functionality)
5. [Data Flow & Processing](#5-data-flow--processing)
6. [Configuration & Deployment](#6-configuration--deployment)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Performance & Scalability](#8-performance--scalability)
9. [Testing Strategy](#9-testing-strategy)
10. [Operational Considerations](#10-operational-considerations)
11. [Implementation Patterns](#11-implementation-patterns)
12. [Constraints & Limitations](#12-constraints--limitations)
13. [Appendices](#appendices)

---

## 1. PROJECT OVERVIEW & PURPOSE

### 1.1 Main Goal
Create a **high-performance, non-blocking proxy service** that allows HTTP/1.1 clients to interact with gRPC backend services through efficient protocol translation, capable of handling thousands of concurrent requests with minimal resource overhead.

### 1.2 Problem Statement
The system solves the following challenges:

1. **Protocol Incompatibility**: Legacy systems and browsers cannot communicate directly with gRPC services (HTTP/2)
2. **Performance Requirements**: Must handle high concurrency without dedicating threads to waiting on I/O
3. **Resource Efficiency**: Traditional thread-per-request models are too expensive at scale
4. **Client Simplicity**: Enables simple HTTP clients to access gRPC services without gRPC-specific libraries
5. **JSON Preference**: Allows clients to use familiar JSON payloads instead of Protocol Buffer binary format

### 1.3 Critical Use Cases
- **High-Traffic API Gateway**: Serving thousands of concurrent HTTP clients accessing gRPC microservices
- **Real-Time Systems**: Low-latency proxy for time-sensitive applications
- **Resource-Constrained Environments**: Efficient operation in containerized/serverless environments
- **Elastic Scaling**: Rapid scale-up/down based on traffic patterns

---

## 2. CONCURRENCY & NON-BLOCKING ARCHITECTURE ⭐

### 2.1 Core Concurrency Requirements

#### 2.1.1 Non-Blocking I/O Mandate
**CRITICAL REQUIREMENT**: All I/O operations MUST be non-blocking

```
BLOCKING (❌ NOT ALLOWED):
┌─────────┐
│ Thread  │──────────────────────────────────┐
└─────────┘  Blocked waiting for I/O         │
             (thread doing nothing)           │
                                              ▼
                                         [I/O Complete]

NON-BLOCKING (✅ REQUIRED):
┌─────────┐
│ Thread  │───┐ Register callback/continuation
└─────────┘   │ Thread freed immediately
              │
              ▼
      [Event Loop / Scheduler]
              │
              ▼ Notification when I/O complete
      Execute callback on available thread
```

**Zero-Blocking Operations**:
- HTTP request reading: Non-blocking stream consumption
- JSON parsing: Async parsing (or sync but off critical path)
- Protocol Buffer serialization: Async or parallel
- gRPC calls: Async stub invocation only
- Response writing: Non-blocking stream writing

#### 2.1.2 Concurrency Models

The implementation MUST use one or more of these patterns:

**Pattern 1: Reactive Streams (Recommended)**
```
Components:
- Reactive HTTP server (e.g., Netty, Ktor with coroutines, Tokio)
- Async gRPC client with reactive API
- Backpressure handling between components
- Event loop for I/O multiplexing

Flow:
Request → Mono/Single → async gRPC call → Mono/Single → Response
All operations return immediately with Future/Promise/Mono
```

**Pattern 2: Coroutines/Async-Await**
```
Components:
- Coroutine-based HTTP server
- Suspending functions for all I/O
- Coroutine dispatcher for thread management
- Structured concurrency for resource cleanup

Flow:
suspend fun handleRequest(req) {
    val grpcResponse = grpcClient.callAsync(req) // suspends, doesn't block
    return convertToHttp(grpcResponse)
}
Thread freed during suspension, reused for other requests
```

**Pattern 3: Event Loop + Async I/O**
```
Components:
- Single-threaded or small thread pool event loop
- Callback-based or Future-based APIs
- Asynchronous gRPC stub
- Promise/Future composition for pipeline

Flow:
HTTP request → Register callback → Return
gRPC call → Register callback → Return
Response ready → Trigger callbacks → Send HTTP response
All on event loop thread(s)
```

**Pattern 4: Virtual Threads (Modern JVM)**
```
Components:
- Virtual threads for request handling
- Blocking-style code (looks synchronous)
- JVM manages millions of virtual threads
- Automatic thread parking on I/O

Flow:
Virtual thread per request (cheap)
Can use blocking APIs (JVM converts to non-blocking internally)
Scales to millions of concurrent requests
```

#### 2.1.3 Threading Model Requirements

**Request Handler Threads**:
- **Minimum**: 1 thread (single event loop)
- **Optimal**: Number of CPU cores (for CPU-bound work)
- **Maximum**: 2 × CPU cores (to avoid context switching)
- **NOT ACCEPTABLE**: 1 thread per request (unless virtual threads)

**I/O Threads**:
- Separate thread pool for I/O operations (Netty, nio, etc.)
- Size: Small fixed pool (e.g., 4-8 threads) OR single event loop
- Handles all network I/O (HTTP server, gRPC client)

**Worker Threads (Optional)**:
- For CPU-intensive operations (JSON parsing, protobuf serialization)
- Size: Configurable, typically CPU cores × 2
- Offload heavy computation from I/O threads

**Example Architecture**:
```
┌───────────────────────────────────────────────────┐
│           HTTP Server (Event Loop)                │
│              2-4 I/O Threads                      │
└───────────────────────────────────────────────────┘
                       │
                       ▼ (non-blocking dispatch)
┌───────────────────────────────────────────────────┐
│         Request Handler Pool                      │
│         8-16 Worker Threads (CPU cores)           │
│    • JSON parsing                                 │
│    • Protobuf conversion                          │
│    • Business logic                               │
└───────────────────────────────────────────────────┘
                       │
                       ▼ (async gRPC call)
┌───────────────────────────────────────────────────┐
│           gRPC Client (Event Loop)                │
│              2-4 I/O Threads                      │
│    • Channel multiplexing                         │
│    • Response callbacks                           │
└───────────────────────────────────────────────────┘
```

### 2.2 Connection Management

#### 2.2.1 HTTP Connection Handling
**Requirements**:
- Keep-alive connections for HTTP/1.1 clients
- Connection pooling with configurable limits
- Idle connection timeout (e.g., 60 seconds)
- Maximum connections per client (rate limiting)
- Non-blocking accept/read/write operations

**Configuration Parameters**:
```yaml
http:
  server:
    max_connections: 10000           # Total concurrent connections
    idle_timeout: 60s                # Keep-alive timeout
    request_timeout: 30s             # Per-request timeout
    max_connections_per_ip: 100      # Rate limiting
    backlog: 1024                    # Accept queue size
```

#### 2.2.2 gRPC Connection Handling
**Requirements**:
- HTTP/2 connection multiplexing (many streams per connection)
- Connection pooling to backend (small pool, e.g., 2-4 connections)
- Automatic reconnection on failures
- Keep-alive pings to detect dead connections
- Non-blocking channel operations

**gRPC Channel Configuration**:
```yaml
grpc:
  client:
    channels:
      backend:
        address: backend:50051
        pool_size: 4                    # HTTP/2 connections
        max_concurrent_streams: 1000    # Per connection
        keep_alive_time: 30s
        keep_alive_timeout: 10s
        idle_timeout: 300s
```

**Stream Multiplexing**:
```
Single gRPC Connection (HTTP/2):
┌────────────────────────────────────┐
│  TCP Connection to gRPC Backend    │
│  ┌──────────┐ ┌──────────┐        │
│  │ Stream 1 │ │ Stream 2 │ ...    │ ← 1000s of concurrent requests
│  └──────────┘ └──────────┘        │
└────────────────────────────────────┘

4 connections × 1000 streams = 4000 concurrent gRPC calls
without blocking any threads
```

### 2.3 Backpressure & Flow Control

#### 2.3.1 Backpressure Requirements
**Definition**: System's ability to signal upstream when downstream cannot keep up

**Scenarios**:
1. **gRPC backend slower than HTTP clients**: Queue fills up, need to slow down request acceptance
2. **JSON serialization slower than gRPC**: Buffer builds up, need to pause gRPC reads
3. **Client slower than proxy**: Response buffer fills, need to pause gRPC backend reads

**Implementation Requirements**:
```
Layer 1: HTTP Server Backpressure
- Monitor request queue depth
- When queue > threshold (e.g., 80% full):
  → Slow down accepting new connections
  → Return 503 Service Unavailable
  → Use TCP backpressure (stop reading from socket)

Layer 2: Processing Pipeline Backpressure
- Reactive streams: Use Flux/Flow with demand signaling
- Coroutines: Use Channel with capacity limits
- Event loop: Use bounded queues with overflow handling

Layer 3: gRPC Client Backpressure
- Monitor pending request count
- When pending > threshold:
  → Reject new HTTP requests
  → Return 429 Too Many Requests
  → Apply circuit breaker pattern
```

#### 2.3.2 Flow Control Mechanisms

**Queue-Based Flow Control**:
```yaml
flow_control:
  request_queue:
    capacity: 1000                  # Max pending requests
    strategy: "reject_when_full"    # Or "block" (not recommended)

  response_buffer:
    per_connection: 64KB            # Per-connection buffer
    total: 100MB                    # Total memory limit
```

**Reactive Streams Flow Control**:
```
Publisher (gRPC) ←──request(n)──── Subscriber (HTTP)
                ───data→
                ←──request(n)────
                ───data→

Subscriber controls rate by requesting specific number of items
Publisher never sends more than requested (backpressure)
```

### 2.4 Resource Pooling

#### 2.4.1 Object Pooling
To reduce garbage collection pressure and improve performance:

**Protocol Buffer Message Pooling**:
- Reuse message builder objects
- Pool for frequently used message types
- Return to pool after serialization

**Buffer Pooling**:
- Reuse byte buffers for I/O operations
- Netty ByteBuf pooling
- Reduces memory allocation overhead

**Connection Pooling** (HTTP/1.1 clients):
- Maintain pool of outgoing connections (if proxy makes HTTP calls)
- Reuse connections across requests
- Configurable pool size and timeout

#### 2.4.2 Thread Pool Configuration

**Executor Service Requirements**:
```yaml
executors:
  io_threads:
    type: "fixed"
    size: 4                         # Number of CPU cores
    queue: "unbounded"              # Or bounded with backpressure

  worker_threads:
    type: "fixed"
    size: 16                        # 2× CPU cores
    queue: "bounded"
    capacity: 1000
    rejection_policy: "caller_runs" # Or abort with 503

  grpc_executor:
    type: "fixed"
    size: 8
    keep_alive: 60s
```

### 2.5 Asynchronous Operation Patterns

#### 2.5.1 Request Processing Pipeline (Non-Blocking)

**Stage-by-Stage Non-Blocking Flow**:
```
Stage 1: HTTP Request Reception (Non-Blocking)
─────────────────────────────────────────────
Input:  HTTP request on NIO socket
Action: Event loop detects readable socket
        Reads bytes into buffer (non-blocking read)
        Dispatches to handler
Output: Request object
Time:   < 1ms, thread never blocks

Stage 2: JSON Parsing (Offloaded or Async)
─────────────────────────────────────────────
Input:  JSON string from request body
Action: Dispatch to worker thread OR
        Use async JSON parser
        Thread freed immediately
Output: JSON object / Parse tree
Time:   1-5ms, original thread freed

Stage 3: Protobuf Conversion (Async)
─────────────────────────────────────────────
Input:  JSON object
Action: Worker thread converts to protobuf
        Uses Builder pattern
        Validates fields
Output: Protobuf message
Time:   1-3ms, non-blocking at caller

Stage 4: gRPC Call (Async, Primary Non-Blocking Point)
─────────────────────────────────────────────────────
Input:  Protobuf request message
Action: asyncStub.method(request, callback)
        ↓
        Returns immediately (< 1μs)
        ↓
        Callback registered with gRPC channel
        ↓
        Thread freed for other requests
        ↓
        gRPC I/O thread handles network
        ↓
        Response arrives → callback invoked
Output: Protobuf response (via callback/future)
Time:   10-50ms backend latency, ZERO thread blocking

Stage 5: Response Serialization (Async)
─────────────────────────────────────────────
Input:  Protobuf response
Action: Dispatch to worker thread
        Convert to JSON
Output: JSON string
Time:   1-5ms, non-blocking at caller

Stage 6: HTTP Response Writing (Non-Blocking)
─────────────────────────────────────────────
Input:  JSON response string
Action: Write to NIO socket buffer
        Mark interest for write ready
        Return immediately
        I/O thread sends when socket writable
Output: HTTP response to client
Time:   < 1ms, thread never blocks
```

**Total Thread Time**: < 5ms per request
**Total Request Time**: 15-100ms (mostly backend latency)
**Concurrency**: 1 thread can handle 200+ requests/second

#### 2.5.2 Async API Patterns

**Pattern 1: Callback-Based (Traditional)**
```pseudo
interface AsyncGrpcClient {
    fun callMethod(
        request: RequestProto,
        callback: (ResponseProto?, Exception?) -> Unit
    )
}

Usage:
client.callMethod(request) { response, error ->
    if (error != null) {
        sendErrorResponse(error)
    } else {
        sendSuccessResponse(response)
    }
}
// Returns immediately, callback invoked later
```

**Pattern 2: Future/Promise-Based**
```pseudo
interface AsyncGrpcClient {
    fun callMethod(request: RequestProto): Future<ResponseProto>
}

Usage:
val future = client.callMethod(request)
future.thenApply { response ->
    convertToJson(response)
}.thenAccept { json ->
    sendHttpResponse(json)
}.exceptionally { error ->
    sendErrorResponse(error)
}
// Fully non-blocking, composable
```

**Pattern 3: Reactive Streams**
```pseudo
interface ReactiveGrpcClient {
    fun callMethod(request: RequestProto): Mono<ResponseProto>
}

Usage:
client.callMethod(request)
    .map { response -> convertToJson(response) }
    .subscribe(
        onNext = { json -> sendHttpResponse(json) },
        onError = { error -> sendErrorResponse(error) }
    )
// Reactive, supports backpressure
```

**Pattern 4: Coroutines (Kotlin)**
```pseudo
interface SuspendingGrpcClient {
    suspend fun callMethod(request: RequestProto): ResponseProto
}

Usage:
launch {
    try {
        val response = client.callMethod(request) // suspends, doesn't block
        val json = convertToJson(response)
        sendHttpResponse(json)
    } catch (e: Exception) {
        sendErrorResponse(e)
    }
}
// Looks synchronous, but fully non-blocking
```

**Pattern 5: Async/Await (JavaScript, Python, C#)**
```pseudo
async function handleRequest(request) {
    try {
        const response = await grpcClient.callMethod(request); // awaits, doesn't block
        const json = convertToJson(response);
        sendHttpResponse(json);
    } catch (error) {
        sendErrorResponse(error);
    }
}
// Event loop remains free during await
```

### 2.6 Performance Characteristics

#### 2.6.1 Resource Utilization Targets

**Thread Efficiency**:
```
Metric: Requests per Thread per Second

Blocking Model:
- 1 thread per request
- Thread blocked during gRPC call (20ms avg)
- Max throughput: 50 req/s per thread
- 10,000 req/s = 200 threads
- Context switching overhead: HIGH

Non-Blocking Model:
- 8 worker threads (CPU cores)
- Thread never blocked, just processes
- Processing time: 5ms per request
- Max throughput: 200 req/s per thread
- 10,000 req/s = 50 threads (with headroom)
- Context switching overhead: LOW

Efficiency Gain: 4× fewer threads, 80% less memory
```

**Memory Efficiency**:
```
Per Request Memory Usage:

Blocking:
- Thread stack: 1MB (default)
- Request/response buffers: 64KB
- Protobuf messages: 16KB
- Total per concurrent request: ~1.1MB
- 10,000 concurrent = 11GB

Non-Blocking:
- No dedicated thread stack (shared)
- Request/response buffers: 64KB (can be pooled)
- Protobuf messages: 16KB
- Async state: 1KB
- Total per concurrent request: ~81KB
- 10,000 concurrent = 810MB

Memory Savings: 93% reduction
```

#### 2.6.2 Throughput Targets

**Per-Instance Targets**:
```yaml
performance:
  throughput:
    sustained: 10000        # req/s, continuous load
    peak: 20000            # req/s, burst capacity (30s)

  latency:
    p50: < 15ms            # Median (proxy overhead only)
    p95: < 30ms
    p99: < 50ms
    p999: < 100ms

  concurrency:
    max_concurrent_requests: 10000    # Simultaneous in-flight
    max_connections: 15000             # HTTP connections

  resources:
    max_threads: 50                    # Total threads (excluding JVM/runtime)
    max_memory: 2GB                    # Heap/memory usage
    cpu_cores: 8                       # Recommended
```

**Scaling Characteristics**:
```
Single Instance (8 cores, 2GB RAM):
- 10,000 req/s
- 10,000 concurrent connections

Linear Scaling (10 instances):
- 100,000 req/s
- 100,000 concurrent connections

Key: Resource usage should scale linearly with load
Avoid: Memory leaks, thread pool exhaustion, connection leaks
```

### 2.7 Concurrency Safety Requirements

#### 2.7.1 Thread Safety
**CRITICAL**: All shared state must be thread-safe

**Thread-Safe Components**:
1. **gRPC Channel**: Thread-safe (shared across requests)
2. **Configuration Objects**: Immutable or thread-safe
3. **Connection Pools**: Synchronized access
4. **Metrics Collectors**: Atomic counters or thread-local

**Thread-Unsafe (Require Isolation)**:
1. **Protocol Buffer Builders**: Not thread-safe, create per-request
2. **JSON Parsers**: May not be thread-safe, check documentation
3. **Request/Response Objects**: Per-request lifecycle, no sharing

#### 2.7.2 Race Condition Prevention

**Common Pitfalls**:
```
❌ UNSAFE: Shared mutable state
var requestCount = 0
fun handleRequest() {
    requestCount++  // Race condition!
}

✅ SAFE: Atomic operations
val requestCount = AtomicLong(0)
fun handleRequest() {
    requestCount.incrementAndGet()
}

❌ UNSAFE: Lazy initialization without synchronization
var channel: Channel? = null
fun getChannel(): Channel {
    if (channel == null) {  // Race condition!
        channel = createChannel()
    }
    return channel!!
}

✅ SAFE: Thread-safe lazy initialization
val channel: Channel by lazy {
    createChannel()  // Thread-safe lazy initialization
}
```

#### 2.7.3 Resource Cleanup

**Requirements**:
- Ensure all resources released even on exceptions
- Use try-with-resources or RAII patterns
- Async cleanup for async resources
- Timeout on cleanup operations (prevent hang)

**Pattern**:
```pseudo
async fun handleRequest(request: HttpRequest): HttpResponse {
    val grpcCall = grpcClient.startCall(request)  // Acquire resource
    try {
        val response = grpcCall.await()
        return convertResponse(response)
    } finally {
        grpcCall.cancel()  // Always cleanup, even on error
    }
}
```

### 2.8 Request Cancellation & Propagation

#### 2.8.1 Cancellation Requirements
**CRITICAL**: Cancellation must propagate through the entire request pipeline

**Why Cancellation is Critical**:
```
Without Cancellation:
- Client disconnects → Proxy continues processing → Backend still processing
- Wasted CPU, memory, network bandwidth
- Backend overload with abandoned requests
- Resource leaks (connections, buffers held)

With Cancellation:
- Client disconnects → Proxy cancels gRPC call → Backend stops processing
- Resources immediately freed
- Backend protected from wasted work
- Clean resource cleanup
```

**Cancellation Triggers**:
1. **HTTP Client Disconnect**: Client closes connection before response sent
2. **Timeout**: Request exceeds configured timeout (HTTP, gRPC, or total)
3. **Explicit Cancellation**: Application-level cancellation (e.g., circuit breaker)
4. **Server Shutdown**: Graceful shutdown cancels in-flight requests
5. **Resource Limits**: Backpressure triggers cancellation of low-priority requests

#### 2.8.2 HTTP Client Disconnect Detection

**Requirement**: Detect client disconnection and cancel gRPC call immediately

**Detection Mechanisms**:
```yaml
http_disconnect_detection:
  # Method 1: Connection state monitoring
  check_connection_state: true
  check_interval: 100ms           # Poll interval (if polling required)

  # Method 2: Write attempt detection
  detect_on_write: true           # Detect disconnect when writing response

  # Method 3: Socket keep-alive
  tcp_keepalive: true
  keepalive_idle: 30s
  keepalive_interval: 10s
  keepalive_count: 3
```

**Implementation Pattern**:
```pseudo
async fun handleRequest(httpRequest: HttpRequest): HttpResponse {
    // Monitor connection state
    val connectionMonitor = monitorConnection(httpRequest.connection)

    try {
        // Start async gRPC call
        val grpcCallHandle = grpcClient.callAsync(request)

        // Race between gRPC response and client disconnect
        val result = select {
            grpcCallHandle.await() -> { response ->
                Response.Success(response)
            }
            connectionMonitor.disconnected() -> {
                Response.Cancelled("Client disconnected")
            }
        }

        when (result) {
            is Response.Success -> return toHttpResponse(result.data)
            is Response.Cancelled -> {
                grpcCallHandle.cancel()  // Cancel gRPC call
                throw ClientDisconnectedException()
            }
        }
    } catch (e: Exception) {
        // Ensure cancellation on any error
        grpcCallHandle?.cancel()
        throw e
    }
}
```

#### 2.8.3 Cancellation Propagation Chain

**Complete Cancellation Flow**:
```
HTTP Client            Proxy                    gRPC Backend
───────────            ─────                    ────────────
    │                    │                           │
    │  HTTP Request      │                           │
    ├──────────────────→ │                           │
    │                    │  gRPC Call                │
    │                    ├─────────────────────────→ │
    │                    │                           │
    │  [Client          │                           │
    │   disconnects]     │                           │
    ×                    │                           │
                         │  Detect disconnect        │
                         ├─→ Cancel gRPC call        │
                         │                           │
                         │  gRPC CANCEL message      │
                         ├─────────────────────────→ │
                         │                           │ Backend stops
                         │                           │ processing
                         │  CANCELLED status         │
                         │←─────────────────────────┤
                         │                           │
                         │  Cleanup resources        │
                         ├─→ Release buffers         │
                         │   Free connections        │
                         │   Update metrics          │

Result: Resources freed in < 100ms of disconnect
```

#### 2.8.4 Timeout-Based Cancellation

**Timeout Hierarchy**:
```yaml
timeouts:
  http_read: 30s              # Reading HTTP request body
  processing: 5s              # JSON parsing + protobuf conversion
  grpc_call: 10s              # gRPC backend timeout
  http_write: 10s             # Writing HTTP response
  total: 30s                  # End-to-end (strictest)

cancellation_behavior:
  on_timeout: "cancel_grpc_and_return_error"
  grace_period: 1s            # Time to attempt graceful cancel
  force_cancel_after: 2s      # Force termination if graceful fails
```

**Multi-Level Timeout Pattern**:
```pseudo
async fun handleRequestWithTimeouts(request: HttpRequest): HttpResponse {
    return withTimeout(totalTimeout = 30.seconds) {
        // Outer timeout: total request time

        val proto = withTimeout(processingTimeout = 5.seconds) {
            // Inner timeout: processing only
            parseAndConvert(request)
        }

        val grpcResponse = withTimeout(grpcTimeout = 10.seconds) {
            // Inner timeout: gRPC call
            grpcClient.call(proto)
        }

        convertToHttp(grpcResponse)
    } catch (TimeoutCancellationException e) {
        // Automatically propagates cancellation to child operations
        logTimeout(e)
        return HttpResponse(504, "Gateway Timeout")
    }
}

Each withTimeout automatically cancels child operations on timeout
```

#### 2.8.5 Cancellation in Different Async Patterns

**Pattern 1: Coroutines (Kotlin)**
```kotlin
suspend fun callGrpc(request: Proto): Proto =
    suspendCancellableCoroutine { continuation ->
        val call = asyncStub.method(request, object : StreamObserver<Proto> {
            override fun onNext(value: Proto) {
                continuation.resume(value)
            }
            override fun onError(t: Throwable) {
                continuation.resumeWithException(t)
            }
            override fun onCompleted() {}
        })

        // CRITICAL: Register cancellation handler
        continuation.invokeOnCancellation {
            // Propagate cancellation to gRPC call
            call.cancel("Request cancelled", null)
        }
    }

// Usage: Automatic propagation
launch {
    try {
        val response = callGrpc(request)  // Auto-cancelled if launch cancelled
    } catch (e: CancellationException) {
        // Handle cancellation
    }
}
```

**Pattern 2: CompletableFuture (Java)**
```java
public CompletableFuture<Response> callGrpc(Request request) {
    CompletableFuture<Response> future = new CompletableFuture<>();

    ClientCall<Request, Response> call = channel.newCall(method, CallOptions.DEFAULT);

    call.start(new ClientCall.Listener<Response>() {
        @Override
        public void onMessage(Response response) {
            future.complete(response);
        }
        @Override
        public void onClose(Status status, Metadata trailers) {
            if (!status.isOk()) {
                future.completeExceptionally(status.asRuntimeException());
            }
        }
    }, new Metadata());

    // CRITICAL: Cancel gRPC call when future cancelled
    future.whenComplete((result, error) -> {
        if (future.isCancelled()) {
            call.cancel("Future cancelled", null);
        }
    });

    call.sendMessage(request);
    call.halfClose();
    call.request(1);

    return future;
}

// Usage with timeout
CompletableFuture<Response> response = callGrpc(request)
    .orTimeout(10, TimeUnit.SECONDS)  // Auto-cancels on timeout
    .whenComplete((r, e) -> {
        if (e instanceof TimeoutException) {
            // gRPC call automatically cancelled
        }
    });
```

**Pattern 3: Reactive Streams (Reactor)**
```java
public Mono<Response> callGrpc(Request request) {
    return Mono.create(sink -> {
        ClientCall<Request, Response> call =
            channel.newCall(method, CallOptions.DEFAULT);

        call.start(new ClientCall.Listener<Response>() {
            @Override
            public void onMessage(Response response) {
                sink.success(response);
            }
            @Override
            public void onClose(Status status, Metadata trailers) {
                if (!status.isOk()) {
                    sink.error(status.asRuntimeException());
                }
            }
        }, new Metadata());

        // CRITICAL: Register cancellation handler
        sink.onCancel(() -> {
            call.cancel("Subscriber cancelled", null);
        });

        call.sendMessage(request);
        call.halfClose();
        call.request(1);
    });
}

// Usage: Automatic propagation with operators
callGrpc(request)
    .timeout(Duration.ofSeconds(10))  // Auto-cancels on timeout
    .doOnCancel(() -> log.info("Request cancelled"))
    .subscribe(
        response -> handleResponse(response),
        error -> handleError(error)
    );
```

**Pattern 4: Async/Await (Python with asyncio)**
```python
async def call_grpc(request: Request) -> Response:
    call = stub.Method.future(request, timeout=10)

    try:
        # Wait for response
        response = await asyncio.wrap_future(call)
        return response
    except asyncio.CancelledError:
        # CRITICAL: Propagate cancellation to gRPC
        call.cancel()
        raise

# Usage with timeout
try:
    response = await asyncio.wait_for(
        call_grpc(request),
        timeout=10.0
    )
except asyncio.TimeoutError:
    # Automatically cancelled
    log.error("Request timeout")
```

**Pattern 5: Go Context Cancellation**
```go
func callGrpc(ctx context.Context, request *pb.Request) (*pb.Response, error) {
    // Context automatically propagates to gRPC client
    response, err := client.Method(ctx, request)
    if err != nil {
        if ctx.Err() == context.Canceled {
            // Request was cancelled
            return nil, fmt.Errorf("request cancelled: %w", err)
        }
        return nil, err
    }
    return response, nil
}

// Usage with timeout and cancellation
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

// Cancel ctx from another goroutine when client disconnects
go func() {
    <-httpRequest.Context().Done()  // HTTP context cancelled
    cancel()  // Propagate to gRPC context
}()

response, err := callGrpc(ctx, request)
// gRPC call automatically cancelled if ctx cancelled
```

#### 2.8.6 Cancellation Metrics & Monitoring

**Required Metrics**:
```yaml
metrics:
  cancellation_total:
    type: counter
    labels: [reason, stage]
    reasons:
      - client_disconnect
      - timeout_http
      - timeout_grpc
      - timeout_total
      - circuit_breaker
      - backpressure
      - shutdown
    stages:
      - before_grpc_call
      - during_grpc_call
      - after_grpc_call

  cancellation_propagation_latency:
    type: histogram
    description: "Time from cancellation trigger to gRPC call cancelled"
    buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]

  cancelled_request_resource_freed:
    type: histogram
    description: "Time to free all resources after cancellation"
    buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
```

**Logging Requirements**:
```yaml
cancellation_logging:
  level: info
  fields:
    - request_id
    - cancellation_reason
    - cancellation_stage
    - time_to_cancel_ms
    - grpc_call_cancelled
    - resources_freed

  example:
    message: "Request cancelled"
    request_id: "req-12345"
    reason: "client_disconnect"
    stage: "during_grpc_call"
    time_to_cancel_ms: 15
    grpc_call_cancelled: true
    resources_freed: ["connection", "buffers"]
```

#### 2.8.7 Cancellation Testing Requirements

**Test Scenarios**:
```yaml
cancellation_tests:
  unit:
    - test_coroutine_cancellation_propagates_to_grpc
    - test_future_cancellation_cancels_grpc_call
    - test_timeout_triggers_cancellation
    - test_cancellation_releases_resources

  integration:
    - test_http_disconnect_cancels_grpc_call
    - test_concurrent_cancellations
    - test_cancellation_during_each_pipeline_stage
    - test_graceful_vs_forced_cancellation

  load:
    - test_cancellation_under_high_load
    - test_many_simultaneous_cancellations
    - test_cancellation_doesnt_affect_other_requests

  chaos:
    - test_random_client_disconnects
    - test_network_partition_during_cancellation
```

**Verification Requirements**:
```
For each test:
1. Verify gRPC call actually cancelled (not just ignored)
2. Verify backend receives cancellation signal
3. Verify all resources released (memory, connections, buffers)
4. Verify no resource leaks over time
5. Verify metrics updated correctly
6. Verify other requests not affected
```

#### 2.8.8 Graceful Shutdown with Cancellation

**Shutdown Procedure**:
```
1. Stop accepting new connections
   ├─→ Return 503 to new requests
   └─→ Health check returns not ready

2. Wait for in-flight requests (with timeout)
   ├─→ Allow requests to complete naturally
   ├─→ Maximum wait time: 30 seconds
   └─→ Monitor completion rate

3. Cancel remaining requests
   ├─→ Cancel all pending HTTP requests
   ├─→ Propagate to gRPC calls
   ├─→ Wait for cancellation to complete (max 5s)
   └─→ Force terminate if needed

4. Close connections
   ├─→ Close gRPC channels
   ├─→ Close HTTP connections
   └─→ Release all resources

5. Shutdown complete
```

**Configuration**:
```yaml
shutdown:
  grace_period: 30s           # Wait for natural completion
  cancellation_timeout: 5s    # Time to cancel remaining
  force_shutdown_after: 35s   # Total shutdown time limit

  drain_mode:
    enabled: true
    wait_for_requests: true
    cancel_after_timeout: true
```

#### 2.8.9 Edge Cases & Error Handling

**Edge Case 1: Cancellation During Conversion**
```
Scenario: Client disconnects while converting JSON to Protobuf
Solution: Check cancellation status before gRPC call
Pattern:
  async fun handle(request) {
      val proto = convertJsonToProto(request)  // May take 5ms

      if (isRequestCancelled()) {
          // Don't start gRPC call if already cancelled
          throw CancelledException()
      }

      return grpcClient.call(proto)
  }
```

**Edge Case 2: Cancellation After gRPC Response Received**
```
Scenario: Client disconnects after gRPC returns but before HTTP response sent
Solution: Still complete processing, but don't send HTTP response
Impact: Minimal waste (just JSON conversion)
```

**Edge Case 3: Double Cancellation**
```
Scenario: Timeout and client disconnect happen simultaneously
Solution: Idempotent cancellation (safe to call multiple times)
Pattern:
  val cancelled = AtomicBoolean(false)
  fun cancel() {
      if (cancelled.compareAndSet(false, true)) {
          // Actually cancel (only once)
          grpcCall.cancel()
      }
  }
```

**Edge Case 4: Backend Ignores Cancellation**
```
Scenario: Backend doesn't support cancellation or ignores it
Solution:
  - Proxy still releases resources locally
  - Don't wait for backend response
  - Log warning about unresponsive backend
  - Consider circuit breaker if frequent
```

---

## 3. SYSTEM ARCHITECTURE

### 3.1 High-Level Architecture (Async Flow)

```
┌──────────────┐         ┌─────────────────────────┐         ┌──────────────┐
│              │  HTTP/1.1│   Non-Blocking Proxy    │  gRPC   │              │
│  HTTP Client │─────────→│   (Event Loop Based)    │────────→│  gRPC Server │
│  (1000s)     │   JSON   │                         │ Protobuf│              │
│              │←─────────│   8 Threads Handle      │←────────│              │
└──────────────┘         │   10,000+ Concurrent     │         └──────────────┘
                         └─────────────────────────┘

Internal Architecture:
┌────────────────────────────────────────────────────────────┐
│                    HTTP Server (NIO)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Accept Thread│  │  I/O Thread  │  │  I/O Thread  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼ (dispatch to worker pool)
┌────────────────────────────────────────────────────────────┐
│                  Request Handler Pool                       │
│  ┌───────────┐  ┌───────────┐         ┌───────────┐       │
│  │  Worker   │  │  Worker   │  .....  │  Worker   │       │
│  │  Thread 1 │  │  Thread 2 │         │  Thread N │       │
│  └───────────┘  └───────────┘         └───────────┘       │
│  • Parse JSON           • Convert Protobuf                 │
│  • Initiate async gRPC  • Handle callbacks                 │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼ (async invocation)
┌────────────────────────────────────────────────────────────┐
│              gRPC Client (HTTP/2 Multiplexing)             │
│  ┌────────────────────────────────────────────┐            │
│  │  Single Connection (or small pool)         │            │
│  │  ┌────┐ ┌────┐ ┌────┐         ┌────┐     │            │
│  │  │Str1│ │Str2│ │Str3│  .....  │StrN│     │            │
│  │  └────┘ └────┘ └────┘         └────┘     │            │
│  │  1000s of concurrent streams                │            │
│  └────────────────────────────────────────────┘            │
│  I/O Thread: Async send/receive                            │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Component Model (Non-Blocking Focus)

#### 3.2.1 HTTP Endpoint Layer (Non-Blocking)
**Responsibilities**:
- Accept connections asynchronously (non-blocking accept)
- Read HTTP requests asynchronously (non-blocking read)
- Parse HTTP headers (fast, minimal CPU)
- Dispatch request handling (don't block I/O thread)
- Write responses asynchronously (non-blocking write)

**Technology Requirements**:
- Event-driven HTTP server (Netty, Tokio, libuv, etc.)
- NIO/epoll/kqueue for efficient I/O multiplexing
- Async request/response API

**Performance Characteristics**:
- Accept rate: 10,000+ connections/second
- I/O threads: 2-4 threads handle all connections
- Zero blocking operations

#### 3.2.2 Message Conversion Layer (Offloaded)
**Responsibilities**:
- Parse JSON to intermediate representation
- Convert JSON to Protocol Buffer messages
- Convert Protocol Buffer responses to JSON
- Handle field name transformations

**Concurrency Strategy**:
- Offload to worker thread pool (CPU-bound work)
- OR use async parser if available
- Pool protobuf builders for reuse
- No blocking I/O

**Performance Characteristics**:
- Processing time: 1-5ms per message
- Worker threads: CPU cores × 2
- Parallelizable across multiple requests

#### 3.2.3 gRPC Client Layer (Async)
**Responsibilities**:
- Maintain async gRPC stubs
- Manage HTTP/2 connections and streams
- Execute async RPC calls with callbacks/futures
- Handle response callbacks
- Propagate errors asynchronously

**Concurrency Strategy**:
- **MUST USE**: Async stub (not blocking stub)
- Callback/Future/Promise-based API
- No thread blocking on gRPC call
- HTTP/2 stream multiplexing for concurrency

**Performance Characteristics**:
- Single connection: 1000+ concurrent streams
- Connection pool: 2-4 connections sufficient
- Response callback overhead: < 100μs

#### 3.2.4 Configuration Management
**Concurrency Considerations**:
- Immutable configuration objects (thread-safe)
- Lazy initialization with thread safety
- No blocking I/O during configuration load
- Dynamic reconfiguration support (optional)

### 3.3 Request Flow (Detailed Async)

```
Timeline View (1 request):

Time    Thread          Action
──────────────────────────────────────────────────────────────
0ms     I/O Thread 1    Accept connection (non-blocking)
0.1ms   I/O Thread 1    Read HTTP headers (non-blocking)
0.5ms   I/O Thread 1    Dispatch to worker pool → return
        [Thread freed, handles other requests]

0.6ms   Worker 1        Parse JSON body (2ms)
2.6ms   Worker 1        Convert to Protobuf (1ms)
3.6ms   Worker 1        Call asyncStub.method(req, callback) → return
        [Thread freed, handles other requests]

3.7ms   gRPC I/O Thread Send gRPC request (non-blocking)
        [Waiting for backend - NO threads blocked]
        ... 20ms backend processing time ...

23.7ms  gRPC I/O Thread Receive gRPC response (callback triggered)
23.7ms  gRPC I/O Thread Dispatch callback to worker pool

23.8ms  Worker 2        Convert Protobuf to JSON (2ms)
25.8ms  Worker 2        Write HTTP response (non-blocking) → return
        [Thread freed]

26ms    I/O Thread 2    Flush response to socket (non-blocking)

Total Wall Clock: 26ms
Total Thread Time: 0.5ms (I/O) + 3ms (Worker 1) + 2ms (Worker 2) = 5.5ms
Efficiency: 5.5ms / 26ms = 21% CPU usage (79% waiting on backend)
```

**Concurrency Scalability**:
```
1,000 concurrent requests:
- Wall clock per request: 26ms
- Thread time per request: 5.5ms
- Total thread time needed: 5,500ms
- Spread across 8 threads: 688ms wall clock
- Therefore: 8 threads can handle 1,000 concurrent requests in < 1 second

10,000 concurrent requests:
- Total thread time needed: 55,000ms
- Spread across 8 threads: 6,875ms wall clock
- Therefore: 8 threads can handle 10,000 concurrent requests in ~7 seconds
- Actual throughput: 10,000 / 7 = 1,428 req/s sustained
- With 16 threads: ~2,850 req/s sustained
- With 32 threads: ~5,700 req/s sustained
```

---

## 4. CORE FEATURES & FUNCTIONALITY

### 4.1 HTTP-to-gRPC Request Translation

#### 4.1.1 URL Routing Convention
**Pattern**: `{base_url}/{service_package}.{service_name}/{method_name}`

**Components**:
- `base_url`: Protocol + host + port (e.g., http://localhost:8080)
- `service_package`: Protobuf package name (e.g., "helloworld")
- `service_name`: gRPC service name (e.g., "Greeter")
- `method_name`: RPC method name (e.g., "SayHello")

**Alternative Pattern**: `{base_url}/{proto_file_name}/{kebab-case-method}/{version}`

**Routing Performance**:
- URL parsing: < 10μs per request
- Route matching: Hash-based O(1) lookup
- Zero allocations (reuse route objects)

#### 4.1.2 HTTP Request Format

**Headers**:
- `Content-Type: application/json` (required)
- `Accept: application/json` (optional, always returns JSON)
- `X-Request-ID`: Optional request tracking
- `Authorization`: Pass-through to gRPC metadata (optional)

**Method**: POST (all RPC calls)

**Body**: JSON representation of Protocol Buffer request message

**Async Processing**:
- Body reading: Streamed asynchronously (don't read entire body into memory at once)
- Large payloads: Support streaming JSON parsing
- Timeout: Configurable read timeout (default 30s)

### 4.2 JSON-to-Protobuf Conversion

#### 4.2.1 Field Name Mapping
- **JSON Format**: camelCase (e.g., `userName`, `emailAddress`)
- **Protobuf Format**: snake_case (e.g., `user_name`, `email_address`)
- **Conversion**: Bidirectional, automatic

**Performance Optimization**:
- Cache field name mappings (snake_case ↔ camelCase)
- Reuse protobuf builders from pool
- Parallel conversion for large messages (optional)

#### 4.2.2 Type Mapping

| Protobuf Type | JSON Type | Async Handling |
|---------------|-----------|----------------|
| string | string | Direct copy, no blocking |
| int32, int64 | number | Fast primitive conversion |
| bool | boolean | Direct mapping |
| double, float | number | Fast conversion |
| bytes | string (Base64) | Async decode for large |
| enum | string | Lookup table (fast) |
| message | object | Recursive async |
| repeated | array | Stream processing |
| map | object | Parallel entry processing |

#### 4.2.3 Conversion Performance
- Simple message (< 10 fields): < 1ms
- Complex message (100 fields): < 5ms
- Nested messages: Recursive async processing
- Large arrays: Stream processing to avoid memory spikes

### 4.3 gRPC Call Execution (Async Only)

#### 4.3.1 Supported Call Types
**PRIMARY**: Unary RPC (async invocation)
- Single request → Single response
- **MUST BE ASYNC**: Use async stub, return immediately
- Callback/Future/Promise-based result

**NOT SUPPORTED**:
- Blocking/synchronous gRPC calls (❌ would block threads)
- Server streaming (future enhancement)
- Client streaming (future enhancement)
- Bidirectional streaming (future enhancement)

#### 4.3.2 Async Execution Pattern

**Detailed Async Flow**:
```
Step 1: Create Async Stub
───────────────────────────
val asyncStub = ServiceGrpc.newStub(channel)
// Stub is thread-safe, can be reused

Step 2: Prepare Request Message
───────────────────────────
val request = RequestMessage.newBuilder()
    .setField1(value1)
    .setField2(value2)
    .build()
// Builder not thread-safe, created per-request

Step 3: Invoke Async Call
───────────────────────────
val responseFuture = CompletableFuture<ResponseMessage>()

asyncStub.method(request, object : StreamObserver<ResponseMessage> {
    override fun onNext(response: ResponseMessage) {
        responseFuture.complete(response)
    }
    override fun onError(t: Throwable) {
        responseFuture.completeExceptionally(t)
    }
    override fun onCompleted() {
        // Unary call, already completed in onNext
    }
})
// Returns immediately, no blocking

Step 4: Handle Response Asynchronously
───────────────────────────────────────
responseFuture.thenApply { response ->
    convertToJson(response)
}.thenAccept { json ->
    sendHttpResponse(json)
}.exceptionally { error ->
    sendErrorResponse(error)
    null
}
// All async, no thread blocking
```

**Alternative: Coroutines**:
```kotlin
suspend fun callGrpc(request: RequestProto): ResponseProto {
    return suspendCancellableCoroutine { continuation ->
        asyncStub.method(request, object : StreamObserver<ResponseProto> {
            override fun onNext(value: ResponseProto) {
                continuation.resume(value)
            }
            override fun onError(t: Throwable) {
                continuation.resumeWithException(t)
            }
            override fun onCompleted() {}
        })
    }
}
// Looks synchronous, but fully non-blocking
```

### 4.4 Response Translation (Async)

#### 4.4.1 Protobuf-to-JSON Conversion (Offloaded)
- Dispatch to worker thread pool (CPU-bound)
- Stream large responses (avoid full JSON in memory)
- Use efficient JSON serializer (Jackson, Gson, serde_json, etc.)

#### 4.4.2 HTTP Response Format

**Success Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 123
X-Response-Time-Ms: 25

{"message":"Hello, Alice","timestamp":"2025-11-12T10:30:00Z"}
```

**Async Writing**:
- Write headers immediately (non-blocking)
- Write body in chunks (non-blocking)
- Flush asynchronously
- Close connection gracefully

### 4.5 Error Handling (Async)

#### 4.5.1 Error Categories

**Client Errors (4xx)**: Returned immediately
- 400 Bad Request: Invalid JSON
- 404 Not Found: Unknown route
- 415 Unsupported Media Type: Wrong Content-Type
- 429 Too Many Requests: Rate limit exceeded

**Server Errors (5xx)**: May occur during async processing
- 500 Internal Server Error: Unexpected exception
- 503 Service Unavailable: gRPC backend down
- 504 Gateway Timeout: Backend timeout

#### 4.5.2 Async Error Propagation

**Pattern**:
```
HTTP Request → Parse JSON → Convert Protobuf → gRPC Call → Convert Response → HTTP Response
     ↓ error       ↓ error        ↓ error         ↓ error      ↓ error         ↓
     ├─────────────┴──────────────┴───────────────┴────────────┴───────────────→ Error Handler
                                                                                      ↓
                                                                              HTTP Error Response
```

**Async Exception Handling**:
```pseudo
// Callback-based
asyncStub.method(request, object : StreamObserver<Response> {
    override fun onError(t: Throwable) {
        // Handle error asynchronously
        when (t) {
            is StatusRuntimeException -> mapGrpcError(t)
            else -> sendServerError(t)
        }
    }
})

// Future-based
responseFuture
    .exceptionally { error ->
        handleErrorAsync(error)
        null // or error response
    }

// Coroutine-based
try {
    val response = callGrpc(request)
    sendResponse(response)
} catch (e: Exception) {
    sendErrorResponse(e)
}
```

#### 4.5.3 Timeout Handling (Critical for Non-Blocking)

**Timeout Types**:
1. **HTTP Request Timeout**: Max time to receive full request (30s)
2. **gRPC Call Timeout**: Max time for gRPC backend to respond (10s)
3. **Total Request Timeout**: End-to-end timeout (30s)

**Implementation**:
```yaml
timeouts:
  http_request_read: 30s        # Reading HTTP request
  grpc_call: 10s                # gRPC backend timeout
  http_response_write: 10s      # Writing HTTP response
  total_request: 30s            # End-to-end (enforced)
```

**Async Timeout Pattern**:
```pseudo
val timeoutFuture = scheduler.schedule({
    throw TimeoutException("Request timeout")
}, 30, SECONDS)

val responseFuture = callGrpcAsync(request)

CompletableFuture.anyOf(responseFuture, timeoutFuture)
    .thenApply { result ->
        timeoutFuture.cancel(false)  // Cancel timeout if response received
        result
    }
```

---

## 5. DATA FLOW & PROCESSING

### 5.1 Async Request Processing Pipeline

**Pipeline Stages (All Non-Blocking)**:

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: HTTP Request Reception (I/O Thread)                │
│ ┌─────────────────────────────────────────────────────┐    │
│ │ • Non-blocking socket accept                         │    │
│ │ • Non-blocking read (NIO/epoll)                      │    │
│ │ • Parse HTTP headers (on I/O thread, fast)           │    │
│ │ • Dispatch body reading to async pipeline            │    │
│ └─────────────────────────────────────────────────────┘    │
│ Characteristics: < 0.5ms, fully non-blocking                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (async dispatch)
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Request Parsing (Worker Thread)                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ • Read request body (async, chunked)                    │ │
│ │ • Parse JSON (offloaded to worker thread)               │ │
│ │ • Validate JSON structure                               │ │
│ │ • Extract fields                                        │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Characteristics: 1-3ms, CPU-bound, parallelizable           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (async chain)
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Protobuf Conversion (Worker Thread)                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ • Get protobuf builder (from pool)                      │ │
│ │ • Map JSON fields to protobuf fields                    │ │
│ │ • Transform camelCase → snake_case                      │ │
│ │ • Build protobuf message                                │ │
│ │ • Return builder to pool                                │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Characteristics: 1-2ms, CPU-bound, pooled objects           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (async invocation)
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: gRPC Call (Async, NO Thread Blocking)              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CRITICAL NON-BLOCKING STAGE                             │ │
│ │                                                           │ │
│ │ asyncStub.method(request, responseCallback)             │ │
│ │         ↓                                               │ │
│ │   Returns in < 1μs                                      │ │
│ │         ↓                                               │ │
│ │   Worker thread freed immediately                       │ │
│ │         ↓                                               │ │
│ │   gRPC I/O thread sends request                         │ │
│ │         ↓                                               │ │
│ │   ~~~ Waiting for backend (10-50ms) ~~~                │ │
│ │   ~~~ NO THREADS BLOCKED ~~~                            │ │
│ │         ↓                                               │ │
│ │   Response arrives → callback invoked                   │ │
│ │         ↓                                               │ │
│ │   Dispatch to worker pool for processing                │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Characteristics: 10-50ms latency, ZERO thread blocking      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (callback invoked)
┌─────────────────────────────────────────────────────────────┐
│ Stage 5: Response Conversion (Worker Thread)                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ • Convert protobuf response to JSON                     │ │
│ │ • Transform snake_case → camelCase                      │ │
│ │ • Format JSON (compact, no whitespace)                  │ │
│ │ • Generate HTTP headers                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Characteristics: 1-3ms, CPU-bound, parallelizable           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (async write)
┌─────────────────────────────────────────────────────────────┐
│ Stage 6: HTTP Response Writing (I/O Thread)                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ • Write HTTP status line (non-blocking)                 │ │
│ │ • Write headers (non-blocking)                          │ │
│ │ • Write JSON body (non-blocking, chunked)               │ │
│ │ • Flush socket buffer                                   │ │
│ │ • Close or keep-alive connection                        │ │
│ └─────────────────────────────────────────────────────────┘ │
│ Characteristics: < 1ms, fully non-blocking                  │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Concurrency in Practice

#### 5.2.1 Single Request Timeline
```
Time     What's Happening                           Thread State
─────────────────────────────────────────────────────────────────
0ms      HTTP request arrives                       I/O thread active
0.5ms    Dispatch to worker pool                    I/O thread freed
0.6ms    Worker 1 picks up, parses JSON            Worker 1 active
3.6ms    Worker 1 calls async gRPC, returns        Worker 1 freed
3.7ms    gRPC I/O thread sends request             gRPC I/O active
...      [Backend processing - NO THREADS USED]    All threads free!
23.7ms   gRPC response arrives, callback fires     gRPC I/O dispatches
23.8ms   Worker 2 picks up, converts to JSON       Worker 2 active
25.8ms   Worker 2 writes response, returns         Worker 2 freed
26ms     I/O thread flushes socket                 I/O thread active

Total Thread Time: ~5.5ms
Total Wall Time: 26ms
Thread Efficiency: 21% (rest is waiting, no threads blocked)
```

#### 5.2.2 Concurrent Requests Timeline (10 Requests)

```
Time     Request 1   Request 2   Request 3   ...   Thread Usage
──────────────────────────────────────────────────────────────────
0ms      Arrive      -           -           -     1 I/O thread
0.5ms    Dispatched  Arrive      -           -     1 I/O + 1 worker
1ms      Processing  Dispatched  Arrive      -     1 I/O + 2 workers
1.5ms    Processing  Processing  Dispatched  -     1 I/O + 3 workers
2ms      Processing  Processing  Processing  Arrive 1 I/O + 4 workers
3ms      Async call  Processing  Processing  ...   1 I/O + 3 workers
4ms      [waiting]   Async call  Processing  ...   1 I/O + 2 workers
5ms      [waiting]   [waiting]   Async call  ...   1 I/O + 1 worker
6ms      [waiting]   [waiting]   [waiting]   ...   1 I/O only!

All 10 requests now waiting for gRPC backend
Thread usage: 1 I/O thread active, workers idle/freed
No threads blocked!

20ms     Resp 1      Resp 2      [waiting]   ...   Callbacks trigger
21ms     Convert     Convert     Resp 3      ...   3 workers active
22ms     Done        Done        Convert     ...   1 worker active
23ms     [complete]  [complete]  Done        ...   All processing

Peak thread usage: 1 I/O + 4 workers = 5 threads
Handled 10 concurrent requests with 5 threads
```

#### 5.2.3 High Concurrency (1000 Requests)

```
Scenario: 1000 requests arrive within 1 second

Traditional Blocking Model:
─────────────────────────────
- Need 1000 threads (1 per request)
- Each thread blocks for 20ms on gRPC call
- Context switching overhead: significant
- Memory: 1000 × 1MB stack = 1GB
- Throughput limited by threads

Non-Blocking Model (This System):
──────────────────────────────────
- Use 16 worker threads + 4 I/O threads = 20 threads
- Threads never block, continuously process
- Each request takes 5.5ms of thread time
- 16 threads can process: 16 × (1000ms / 5.5ms) = 2,909 req/s
- All 1000 requests processed in ~350ms of wall clock time
- Memory: 20 threads × 1MB + request buffers = ~100MB
- 10× memory savings, same throughput
```

### 5.3 Backpressure in Data Flow

#### 5.3.1 Backpressure Points

```
HTTP Clients → [BP1] → HTTP Server → [BP2] → Workers → [BP3] → gRPC Backend

BP1: Connection Limit
──────────────────────
When: Too many concurrent connections
Action: Reject new connections (TCP backlog full)
Effect: Clients see connection refused, retry

BP2: Request Queue Limit
─────────────────────────
When: Worker pool queue full
Action: Return 503 Service Unavailable immediately
Effect: Fast failure, don't accept unbounded requests

BP3: gRPC Pending Calls Limit
──────────────────────────────
When: Too many pending gRPC calls
Action: Return 429 Too Many Requests
Effect: Protect backend from overload
```

#### 5.3.2 Backpressure Configuration

```yaml
backpressure:
  http_connections:
    max: 10000                    # Max concurrent connections
    backlog: 1024                 # Accept queue size

  request_queue:
    max: 1000                     # Max pending requests
    strategy: "reject"            # reject | block (reject recommended)

  grpc_calls:
    max_pending: 5000             # Max concurrent gRPC calls
    timeout: 10s                  # Per-call timeout

  circuit_breaker:
    enabled: true
    failure_threshold: 50         # % failures to open circuit
    timeout: 30s                  # Time before retry
```

---

## 6. CONFIGURATION & DEPLOYMENT

### 6.1 Configuration Parameters

#### 6.1.1 Complete Configuration Schema

```yaml
application:
  name: grpc-http1-proxy
  version: 1.0.0

# Concurrency & Threading
concurrency:
  io_threads: 4                     # NIO threads for HTTP/gRPC I/O
  worker_threads: 16                # Worker threads for processing
  grpc_executor_threads: 8          # gRPC executor threads

  thread_pools:
    request_handler:
      type: fixed
      size: 16
      queue_capacity: 1000
      keep_alive: 60s
      rejection_policy: abort       # abort | caller_runs | discard

    grpc_callback:
      type: fixed
      size: 8
      queue_capacity: 500

# HTTP Server Configuration
http:
  server:
    port: 8080
    bind_address: "0.0.0.0"

    # Connection settings
    max_connections: 10000          # Total concurrent connections
    connection_timeout: 30s
    idle_timeout: 60s               # Keep-alive timeout

    # Request settings
    max_request_size: 10MB
    request_timeout: 30s
    header_timeout: 10s

    # Performance tuning
    tcp_nodelay: true               # Disable Nagle's algorithm
    so_backlog: 1024                # Accept queue size
    so_reuseaddr: true

# gRPC Client Configuration
grpc:
  client:
    channels:
      backend:
        address: "backend.example.com:50051"

        # Connection pooling
        pool_size: 4                # Number of HTTP/2 connections
        max_concurrent_streams: 1000 # Per connection

        # Timeouts
        connect_timeout: 10s
        request_timeout: 10s
        idle_timeout: 300s

        # Keep-alive
        keep_alive_time: 30s
        keep_alive_timeout: 10s
        keep_alive_without_calls: true

        # Retry policy
        retry:
          enabled: true
          max_attempts: 3
          backoff: exponential      # exponential | fixed
          initial_backoff: 100ms
          max_backoff: 5s

        # TLS (if required)
        tls:
          enabled: false
          cert_chain: /path/to/cert.pem
          private_key: /path/to/key.pem
          trust_certs: /path/to/ca.pem

  # Disable internal gRPC server (we're client-only)
  server:
    enabled: false

# Backpressure & Circuit Breaking
backpressure:
  max_pending_requests: 5000        # Total in-flight requests
  max_pending_grpc_calls: 5000      # Concurrent gRPC calls

  circuit_breaker:
    enabled: true
    failure_rate_threshold: 50      # % failures to open
    slow_call_rate_threshold: 50    # % slow calls to open
    slow_call_duration: 5s
    wait_duration_open: 30s         # Time before half-open
    sliding_window_size: 100        # Calls to track

# Monitoring & Observability
monitoring:
  metrics:
    enabled: true
    port: 9090
    path: /metrics

  tracing:
    enabled: true
    sampler: probabilistic
    sample_rate: 0.1                # 10% of requests

  logging:
    level: info                     # debug | info | warn | error
    format: json                    # json | text
    include_request_body: false     # Privacy concern
    include_response_body: false

  health:
    enabled: true
    port: 8081
    liveness_path: /health/live
    readiness_path: /health/ready

# Performance & Resource Limits
resources:
  memory:
    max_heap: 2GB                   # JVM max heap (if applicable)
    buffer_pool: 100MB              # For I/O buffers

  limits:
    max_request_rate: 10000         # Per second, per instance
    max_connections_per_ip: 100     # Rate limiting
```

### 6.2 Deployment Configurations

#### 6.2.1 Development Profile
```yaml
# Optimized for fast startup, debugging
concurrency:
  io_threads: 2
  worker_threads: 4

http:
  server:
    port: 8080
    max_connections: 100

grpc:
  client:
    channels:
      backend:
        address: "localhost:50051"
        pool_size: 1

monitoring:
  logging:
    level: debug
```

#### 6.2.2 Production Profile
```yaml
# Optimized for high throughput, low latency
concurrency:
  io_threads: 4
  worker_threads: 32              # 4× CPU cores

http:
  server:
    port: 8080
    max_connections: 10000

grpc:
  client:
    channels:
      backend:
        address: "backend.prod.svc:50051"
        pool_size: 8                # More connections
        max_concurrent_streams: 1000

backpressure:
  max_pending_requests: 10000
  circuit_breaker:
    enabled: true

monitoring:
  logging:
    level: info
  metrics:
    enabled: true
  tracing:
    enabled: true
    sample_rate: 0.01               # 1% to reduce overhead
```

#### 6.2.3 High-Concurrency Profile
```yaml
# Extreme throughput (100K+ req/s across cluster)
concurrency:
  io_threads: 8                     # More I/O threads
  worker_threads: 64                # 8× CPU cores

http:
  server:
    max_connections: 50000          # Higher limit

grpc:
  client:
    channels:
      backend:
        pool_size: 16               # More connections
        max_concurrent_streams: 2000

resources:
  memory:
    max_heap: 8GB                   # More memory
    buffer_pool: 500MB
```

### 6.3 Deployment Modes

#### 6.3.1 Standalone Mode
```
Single instance deployment

Use Case: Development, small-scale production
Characteristics:
- 1 proxy instance
- Direct connection to gRPC backend
- Throughput: 10,000 req/s
- No high availability

Configuration:
- Standard settings
- No load balancing
```

#### 6.3.2 Load-Balanced Mode
```
┌──────────┐
│   LB     │ (HAProxy, nginx, AWS ALB)
└────┬─────┘
     │
     ├────→ [Proxy Instance 1] ──→ [gRPC Backend Pool]
     ├────→ [Proxy Instance 2] ──→ [gRPC Backend Pool]
     └────→ [Proxy Instance N] ──→ [gRPC Backend Pool]

Use Case: Production, high availability
Characteristics:
- Multiple proxy instances (N)
- Load balancer distributes HTTP requests
- Throughput: 10,000 × N req/s
- High availability (instance failure)

Configuration:
- Session affinity: Not required (stateless)
- Health checks: /health/ready endpoint
- Load balancing algorithm: Round-robin or least-connections
```

#### 6.3.3 Sidecar Mode
```
┌───────────────────────────────────┐
│         Kubernetes Pod             │
│  ┌──────────┐    ┌──────────┐    │
│  │  HTTP    │    │  gRPC    │    │
│  │  Service │───→│  Proxy   │    │
│  │          │    │ (Sidecar)│    │
│  └──────────┘    └─────┬────┘    │
└────────────────────────│──────────┘
                         │
                         ├────→ [gRPC Backend 1]
                         ├────→ [gRPC Backend 2]
                         └────→ [gRPC Backend N]

Use Case: Microservices architecture
Characteristics:
- Proxy deployed alongside each service
- Local (in-pod) communication HTTP → Proxy
- Service mesh integration
- Per-service configuration

Configuration:
- Bind to localhost or pod IP
- Smaller resource allocation per sidecar
- Service discovery integration
```

#### 6.3.4 API Gateway Mode
```
                [API Gateway]
                      │
     ┌────────────────┼────────────────┐
     │                │                │
     ▼                ▼                ▼
[HTTP Service 1] [HTTP Service 2] [Proxy] ──→ [gRPC Services]

Use Case: Mixed HTTP/gRPC architecture
Characteristics:
- Proxy as one backend in API gateway
- Route /grpc/* to proxy
- Centralized auth, rate limiting, etc.

Configuration:
- API gateway handles TLS termination
- Proxy receives internal traffic only
- Inherit gateway's monitoring/tracing
```

---

## 7. NON-FUNCTIONAL REQUIREMENTS

### 7.1 Performance Requirements

#### 7.1.1 Throughput Targets (Per Instance)
```yaml
performance:
  throughput:
    minimum: 5000               # req/s, sustained load
    target: 10000               # req/s, normal operation
    peak: 20000                 # req/s, burst capacity (30s)

  latency:
    p50: < 15ms                 # Median (proxy overhead only)
    p95: < 30ms                 # 95th percentile
    p99: < 50ms                 # 99th percentile
    p999: < 100ms               # 99.9th percentile

  concurrency:
    max_concurrent_connections: 10000
    max_concurrent_requests: 10000
    max_concurrent_grpc_calls: 5000

  resources:
    max_threads: 50             # Total application threads
    max_memory: 2GB             # Heap + off-heap
    max_cpu: 8_cores            # Assumed for targets

  efficiency:
    requests_per_thread_per_second: 200
    memory_per_connection: < 100KB
    cpu_per_1000_rps: < 1_core
```

#### 7.1.2 Scalability Characteristics
```
Linear Scaling Requirements:

2× instances = 2× throughput
4× instances = 4× throughput
N× instances = N× throughput (up to backend capacity)

Constraints:
- No shared state between instances
- Stateless request processing
- Independent scaling
```

### 7.2 Reliability Requirements

#### 7.2.1 Availability Targets
```yaml
reliability:
  availability: 99.9%           # 43 minutes downtime/month

  recovery:
    max_downtime: 30s           # Time to restart after crash
    graceful_shutdown: 30s      # Time to drain connections

  error_rate:
    target: < 0.1%              # Errors caused by proxy (not backend)

  fault_tolerance:
    backend_failures: "Continue serving other requests"
    partial_degradation: "Return errors, don't crash"
```

#### 7.2.2 Error Recovery

**Automatic Retry**:
```yaml
retry_policy:
  transient_errors:
    - UNAVAILABLE
    - DEADLINE_EXCEEDED
    - RESOURCE_EXHAUSTED
  max_attempts: 3
  backoff: exponential
  initial_backoff: 100ms
  max_backoff: 5s
  timeout_per_attempt: 10s
```

**Circuit Breaker**:
```
States:
  CLOSED: Normal operation, requests pass through
  OPEN: Too many failures, reject requests immediately (fail-fast)
  HALF_OPEN: Test if backend recovered, allow limited requests

Transitions:
  CLOSED → OPEN: When failure rate > threshold (50%)
  OPEN → HALF_OPEN: After timeout (30s)
  HALF_OPEN → CLOSED: If test requests succeed
  HALF_OPEN → OPEN: If test requests fail
```

**Graceful Degradation**:
- Continue serving healthy backends if one fails
- Return specific errors (don't hang)
- Maintain performance for successful requests

### 7.3 Security Requirements

#### 7.3.1 Transport Security
```yaml
security:
  http:
    tls:
      enabled: false            # Can enable TLS termination
      cert: /path/to/cert.pem
      key: /path/to/key.pem
      min_version: TLSv1.2

  grpc:
    tls:
      enabled: false            # Can enable mTLS
      cert_chain: /path/to/cert.pem
      private_key: /path/to/key.pem
      trust_certs: /path/to/ca.pem
      verify_server_cert: true
```

#### 7.3.2 Authentication & Authorization (Optional)
```yaml
auth:
  enabled: false                # Optional feature

  jwt:
    enabled: false
    issuer: "https://auth.example.com"
    audience: "api"
    public_key: /path/to/public.pem

  api_key:
    enabled: false
    header_name: "X-API-Key"
    validation: "lookup"        # lookup | hash
```

#### 7.3.3 Input Validation
```yaml
validation:
  request:
    max_size: 10MB              # Prevent DoS
    max_json_depth: 10          # Prevent deeply nested JSON
    allowed_content_types:
      - "application/json"

  rate_limiting:
    enabled: true
    per_ip: 100                 # Requests per second
    per_connection: 10          # Requests per second
    burst: 200                  # Burst allowance
```

### 7.4 Observability Requirements

#### 7.4.1 Metrics (Prometheus Format)
```yaml
metrics:
  # Request metrics
  http_requests_total:
    type: counter
    labels: [method, route, status]

  http_request_duration_seconds:
    type: histogram
    labels: [method, route, status]
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]

  # gRPC metrics
  grpc_calls_total:
    type: counter
    labels: [service, method, status]

  grpc_call_duration_seconds:
    type: histogram
    labels: [service, method, status]

  # Resource metrics
  thread_pool_active_threads:
    type: gauge
    labels: [pool_name]

  thread_pool_queue_size:
    type: gauge
    labels: [pool_name]

  grpc_connections_active:
    type: gauge
    labels: [backend]

  grpc_streams_active:
    type: gauge
    labels: [backend]

  # Error metrics
  errors_total:
    type: counter
    labels: [type, cause]
```

#### 7.4.2 Logging
```yaml
logging:
  format: json
  level: info

  access_log:
    enabled: true
    fields:
      - timestamp
      - request_id
      - method
      - path
      - status
      - duration_ms
      - client_ip
      - user_agent

  error_log:
    enabled: true
    include_stacktrace: true

  performance_log:
    enabled: true
    slow_request_threshold: 1000ms
```

#### 7.4.3 Distributed Tracing
```yaml
tracing:
  enabled: true
  exporter: otlp                # OpenTelemetry Protocol
  endpoint: "collector:4317"

  sampling:
    type: probabilistic
    rate: 0.1                   # 10% of requests

  spans:
    - name: "http.request"
      attributes:
        - http.method
        - http.url
        - http.status_code

    - name: "json.parse"
      attributes:
        - message.size

    - name: "grpc.call"
      attributes:
        - grpc.service
        - grpc.method
        - grpc.status_code
```

---

## 8. PERFORMANCE & SCALABILITY

### 8.1 Benchmarking Requirements

#### 8.1.1 Performance Tests
```yaml
benchmarks:
  baseline:
    description: "Simple echo service"
    target_rps: 10000
    duration: 300s
    concurrent_connections: 1000
    message_size: 1KB

  load_test:
    description: "Sustained load"
    target_rps: 8000
    duration: 3600s           # 1 hour
    acceptance:
      p99_latency: < 50ms
      error_rate: < 0.1%

  stress_test:
    description: "Find breaking point"
    ramp_up: 0_to_20000_rps
    duration: 600s
    acceptance:
      find_max_throughput: true
      no_crashes: true

  spike_test:
    description: "Sudden traffic spike"
    baseline_rps: 5000
    spike_rps: 20000
    spike_duration: 60s
    acceptance:
      p99_latency: < 100ms
      no_connection_refused: true
```

#### 8.1.2 Resource Monitoring During Tests
```yaml
monitoring:
  metrics:
    - cpu_usage_percent
    - memory_usage_bytes
    - memory_usage_percent
    - thread_count
    - gc_pause_seconds (if applicable)
    - network_bytes_sent
    - network_bytes_received
    - open_file_descriptors
    - tcp_connections

  alerts:
    - name: "High CPU"
      condition: cpu_usage > 80%
    - name: "High Memory"
      condition: memory_usage > 90%
    - name: "Thread Pool Saturation"
      condition: queue_size > 90% capacity
```

### 8.2 Capacity Planning

#### 8.2.1 Resource Estimates

**Per Instance Capacity**:
```
Hardware Profile: 8 CPU cores, 4GB RAM

Expected Performance:
- Throughput: 10,000 req/s
- Concurrent connections: 10,000
- Concurrent requests: 5,000
- Memory usage: 2GB (50% of available)
- CPU usage: 60% (average)

Resource Breakdown:
- Threads: 32 (4 I/O + 16 workers + 8 gRPC + 4 overhead)
- Memory per connection: 100KB
- Memory per request: 50KB (transient)
- CPU per request: 0.5ms (processing time)
```

**Scaling Formula**:
```
Required Instances = Target RPS / Instance RPS
                   = Target RPS / 10,000

Example:
Target: 100,000 req/s
Instances needed: 100,000 / 10,000 = 10 instances

With 20% headroom:
Instances deployed: 10 × 1.2 = 12 instances
```

#### 8.2.2 Bottleneck Identification

**Potential Bottlenecks**:
```
1. Network I/O
   Symptom: High CPU on I/O threads, low worker thread usage
   Solution: Increase I/O threads, optimize network settings

2. CPU Processing
   Symptom: High worker thread usage, low I/O usage
   Solution: Increase worker threads, optimize JSON/protobuf conversion

3. Memory
   Symptom: Frequent GC pauses, high memory usage
   Solution: Increase heap size, implement object pooling

4. gRPC Backend
   Symptom: High pending gRPC calls, long response times
   Solution: Scale backend, increase gRPC connection pool

5. Thread Pool Saturation
   Symptom: Growing queue size, increasing latency
   Solution: Increase thread pool size, implement backpressure
```

### 8.3 Optimization Techniques

#### 8.3.1 Zero-Copy Optimizations
```
Technique: Minimize data copying between buffers

Implementation:
- Use direct byte buffers (off-heap)
- Netty's ByteBuf with reference counting
- Avoid converting byte[] → String → byte[] unnecessarily
- Stream large payloads without buffering

Benefit: Reduce GC pressure, improve latency
```

#### 8.3.2 Object Pooling
```
Pooled Objects:
- Protocol Buffer builders
- Byte buffers
- JSON parsers/generators
- Thread-local caches

Implementation:
- Use ThreadLocal for per-thread pools
- Use bounded pool with eviction policy
- Return objects to pool in finally block

Benefit: Reduce allocation overhead, less GC
```

#### 8.3.3 Async I/O Optimization
```
Techniques:
- Use NIO/epoll/kqueue for socket I/O
- Batch multiple writes when possible
- Use scatter-gather I/O for headers + body
- Configure TCP_NODELAY and SO_KEEPALIVE

Benefit: Lower latency, higher throughput
```

---

## 9. TESTING STRATEGY

### 9.1 Unit Testing

#### 9.1.1 Component Tests
```yaml
test_suites:
  json_parser:
    tests:
      - test_simple_json_to_protobuf
      - test_nested_objects
      - test_arrays
      - test_field_name_mapping
      - test_invalid_json
      - test_missing_fields

  grpc_client:
    tests:
      - test_async_call_success
      - test_async_call_timeout
      - test_async_call_error
      - test_connection_retry
      - test_circuit_breaker

  http_handler:
    tests:
      - test_route_parsing
      - test_content_type_validation
      - test_timeout_handling
      - test_error_response_format
```

#### 9.1.2 Concurrency Tests
```yaml
concurrency_tests:
  thread_safety:
    tests:
      - test_concurrent_requests
      - test_shared_channel_safety
      - test_connection_pool_safety
      - test_metrics_thread_safety

  async_behavior:
    tests:
      - test_non_blocking_io
      - test_callback_execution
      - test_timeout_cancellation
      - test_resource_cleanup

  stress:
    tests:
      - test_1000_concurrent_requests
      - test_rapid_connection_churn
      - test_memory_leak_detection
```

### 9.2 Integration Testing

#### 9.2.1 End-to-End Tests
```yaml
e2e_tests:
  happy_path:
    - setup: Start mock gRPC server
    - test: Send HTTP request → Verify gRPC call → Check response
    - verify: Status 200, JSON response matches expected

  error_scenarios:
    - test_backend_unavailable
    - test_backend_timeout
    - test_invalid_request
    - test_large_payload

  concurrency:
    - test_100_concurrent_requests
    - test_connection_pooling
    - test_backpressure_handling
```

#### 9.2.2 Performance Tests
```yaml
performance_tests:
  baseline:
    tool: "wrk, gatling, or k6"
    command: "wrk -t4 -c1000 -d60s --latency http://localhost:8080/test"
    acceptance:
      throughput: > 5000 req/s
      p99_latency: < 50ms

  load:
    tool: "k6"
    script: "load-test.js"
    config:
      vus: 1000             # Virtual users
      duration: "5m"
      thresholds:
        http_req_duration: ["p(95)<100"]
        http_req_failed: ["rate<0.01"]

  soak:
    description: "Long-running stability test"
    duration: "24h"
    target_rps: 5000
    acceptance:
      no_memory_leaks: true
      no_crashes: true
      stable_latency: true
```

### 9.3 Chaos Testing

#### 9.3.1 Failure Scenarios
```yaml
chaos_tests:
  backend_failures:
    - kill_backend_pod
    - network_partition
    - slow_responses (latency injection)
    - random_errors (error injection)

  resource_constraints:
    - limit_cpu (50% of normal)
    - limit_memory (70% of normal)
    - network_throttling

  load_spikes:
    - sudden_10x_traffic
    - gradual_ramp_up_to_overload

  cascading_failures:
    - kill_one_instance_while_under_load
    - backend_degradation
```

---

## 10. OPERATIONAL CONSIDERATIONS

### 10.1 Monitoring & Alerting

#### 10.1.1 Health Checks

**Liveness Probe**:
```http
GET /health/live HTTP/1.1

Response:
200 OK (if process alive)
503 Service Unavailable (if deadlocked)

Checks:
- Process is running
- Main thread pool responsive
- No critical deadlocks
```

**Readiness Probe**:
```http
GET /health/ready HTTP/1.1

Response:
200 OK (if ready to serve traffic)
503 Service Unavailable (if not ready)

Checks:
- gRPC backend reachable
- Thread pools available
- Circuit breaker not open
- No critical resource exhaustion
```

#### 10.1.2 Alerting Rules
```yaml
alerts:
  - name: HighErrorRate
    condition: error_rate > 1%
    severity: warning
    duration: 5m

  - name: HighLatency
    condition: p95_latency > 100ms
    severity: warning
    duration: 5m

  - name: BackendDown
    condition: grpc_connection_active == 0
    severity: critical
    duration: 1m

  - name: ThreadPoolSaturated
    condition: thread_pool_queue_size > 90%
    severity: warning
    duration: 2m

  - name: MemoryHigh
    condition: memory_usage > 90%
    severity: critical
    duration: 5m
```

### 10.2 Troubleshooting

#### 10.2.1 Common Issues

**Issue: High Latency**
```
Symptoms:
- P95/P99 latency increasing
- Response times slow

Investigation:
1. Check gRPC backend latency (is backend slow?)
2. Check thread pool usage (are threads saturated?)
3. Check GC pauses (is GC blocking?)
4. Check CPU usage (is CPU saturated?)

Solutions:
- Scale backend if backend is slow
- Increase thread pool size if saturated
- Tune GC settings or increase heap
- Add more instances if CPU saturated
```

**Issue: Connection Refused**
```
Symptoms:
- Clients see connection refused
- TCP backlog full

Investigation:
1. Check current connection count
2. Check accept queue size
3. Check system limits (ulimit -n)

Solutions:
- Increase max_connections setting
- Increase SO_BACKLOG
- Increase file descriptor limit
- Scale horizontally (more instances)
```

**Issue: Memory Leak**
```
Symptoms:
- Memory usage grows over time
- Frequent GC, long GC pauses
- Eventually OOM

Investigation:
1. Take heap dump
2. Analyze with profiler (VisualVM, YourKit, etc.)
3. Look for object retention (large arrays, unclosed connections)

Solutions:
- Fix code leak (close connections, clear references)
- Implement object pooling
- Tune GC settings
- Increase heap size (if legitimate growth)
```

**Issue: Thread Starvation**
```
Symptoms:
- Request queue growing
- Latency increasing
- Thread pool queue full

Investigation:
1. Check thread pool metrics
2. Thread dump to see what threads are doing
3. Check if blocking I/O happening (BUG!)

Solutions:
- Increase thread pool size
- Find and fix blocking I/O (critical bug)
- Implement backpressure (reject requests)
```

### 10.3 Performance Tuning

#### 10.3.1 JVM Tuning (If Applicable)
```bash
JVM_OPTS="
  -Xms2G -Xmx2G                   # Fixed heap size
  -XX:+UseG1GC                     # G1 garbage collector
  -XX:MaxGCPauseMillis=50          # Target GC pause
  -XX:+UseStringDeduplication      # Save memory
  -XX:+ParallelRefProcEnabled      # Parallel reference processing
  -Dio.netty.allocator.type=pooled # Pooled byte buffers
  -Dio.netty.leakDetection.level=simple
"
```

#### 10.3.2 OS Tuning
```bash
# Increase file descriptor limit
ulimit -n 65535

# TCP tuning
sysctl -w net.ipv4.tcp_fin_timeout=30
sysctl -w net.ipv4.tcp_keepalive_time=300
sysctl -w net.ipv4.tcp_keepalive_intvl=30
sysctl -w net.ipv4.tcp_keepalive_probes=3
sysctl -w net.core.somaxconn=4096

# Increase ephemeral port range
sysctl -w net.ipv4.ip_local_port_range="10000 65000"
```

#### 10.3.3 Network Tuning
```yaml
network:
  tcp:
    nodelay: true               # Disable Nagle's algorithm
    quickack: true              # Enable TCP quick ACK
    so_reuseaddr: true          # Reuse address
    so_keepalive: true          # Enable keep-alive

  buffer_sizes:
    send: 256KB                 # SO_SNDBUF
    receive: 256KB              # SO_RCVBUF
```

---

## 11. IMPLEMENTATION PATTERNS

### 11.1 Async HTTP Handler Pattern

**Kotlin Coroutines Example**:
```kotlin
@RestController
class ProxyController(
    private val grpcClient: AsyncGrpcClient
) {
    @PostMapping("/{service}/{method}")
    suspend fun handleRequest(
        @PathVariable service: String,
        @PathVariable method: String,
        @RequestBody json: String
    ): ResponseEntity<String> {
        return try {
            // Non-blocking: Convert JSON to Protobuf
            val protoRequest = convertJsonToProto(service, method, json)

            // Non-blocking: Call gRPC (suspends, doesn't block thread)
            val protoResponse = grpcClient.call(service, method, protoRequest)

            // Non-blocking: Convert Protobuf to JSON
            val jsonResponse = convertProtoToJson(protoResponse)

            ResponseEntity.ok(jsonResponse)
        } catch (e: Exception) {
            handleError(e)
        }
    }
}
```

**Reactive (Project Reactor) Example**:
```kotlin
@RestController
class ProxyController(
    private val grpcClient: ReactiveGrpcClient
) {
    @PostMapping("/{service}/{method}")
    fun handleRequest(
        @PathVariable service: String,
        @PathVariable method: String,
        @RequestBody json: Mono<String>
    ): Mono<ResponseEntity<String>> {
        return json
            .map { convertJsonToProto(service, method, it) }
            .flatMap { grpcClient.call(service, method, it) }
            .map { convertProtoToJson(it) }
            .map { ResponseEntity.ok(it) }
            .onErrorResume { handleError(it) }
    }
}
```

### 11.2 Async gRPC Client Pattern

**Callback-Based**:
```kotlin
class AsyncGrpcClientImpl(
    private val channel: ManagedChannel
) : AsyncGrpcClient {
    override suspend fun call(
        service: String,
        method: String,
        request: Message
    ): Message = suspendCancellableCoroutine { continuation ->
        val stub = getAsyncStub(service)
        val call = stub.call(method, request, object : StreamObserver<Message> {
            override fun onNext(value: Message) {
                continuation.resume(value)
            }

            override fun onError(t: Throwable) {
                continuation.resumeWithException(t)
            }

            override fun onCompleted() {
                // Already completed in onNext
            }
        })

        // Cancel gRPC call if coroutine cancelled
        continuation.invokeOnCancellation {
            call.cancel("Coroutine cancelled", null)
        }
    }
}
```

**Future-Based**:
```kotlin
class FutureGrpcClient(
    private val channel: ManagedChannel
) {
    fun call(
        service: String,
        method: String,
        request: Message
    ): CompletableFuture<Message> {
        val future = CompletableFuture<Message>()
        val stub = getAsyncStub(service)

        stub.call(method, request, object : StreamObserver<Message> {
            override fun onNext(value: Message) {
                future.complete(value)
            }

            override fun onError(t: Throwable) {
                future.completeExceptionally(t)
            }

            override fun onCompleted() {}
        })

        return future
    }
}
```

### 11.3 Connection Pool Pattern

```kotlin
class GrpcChannelPool(
    private val config: GrpcConfig
) {
    private val channels: List<ManagedChannel> = List(config.poolSize) {
        ManagedChannelBuilder
            .forAddress(config.host, config.port)
            .usePlaintext()
            .executor(grpcExecutor)
            .keepAliveTime(30, TimeUnit.SECONDS)
            .keepAliveTimeout(10, TimeUnit.SECONDS)
            .maxInboundMessageSize(10 * 1024 * 1024)
            .build()
    }

    private val counter = AtomicInteger(0)

    fun getChannel(): ManagedChannel {
        // Round-robin selection
        val index = counter.getAndIncrement() % channels.size
        return channels[index]
    }

    fun shutdown() {
        channels.forEach { it.shutdown() }
    }
}
```

### 11.4 Backpressure Pattern

```kotlin
class BackpressureHandler(
    private val maxPendingRequests: Int
) {
    private val pendingRequests = AtomicInteger(0)

    suspend fun <T> executeWithBackpressure(
        block: suspend () -> T
    ): T {
        // Check if we can accept more requests
        val pending = pendingRequests.incrementAndGet()
        if (pending > maxPendingRequests) {
            pendingRequests.decrementAndGet()
            throw TooManyRequestsException("Too many pending requests: $pending")
        }

        return try {
            block()
        } finally {
            pendingRequests.decrementAndGet()
        }
    }
}

// Usage in controller
@PostMapping("/{service}/{method}")
suspend fun handleRequest(...): ResponseEntity<String> {
    return backpressureHandler.executeWithBackpressure {
        // Process request
        processRequest(...)
    }
}
```

### 11.5 Circuit Breaker Pattern

```kotlin
class CircuitBreaker(
    private val config: CircuitBreakerConfig
) {
    private enum class State { CLOSED, OPEN, HALF_OPEN }

    private var state = State.CLOSED
    private val failureCount = AtomicInteger(0)
    private val totalCount = AtomicInteger(0)
    private var lastFailureTime = 0L

    suspend fun <T> execute(block: suspend () -> T): T {
        when (state) {
            State.OPEN -> {
                // Check if timeout elapsed
                if (System.currentTimeMillis() - lastFailureTime > config.timeout) {
                    state = State.HALF_OPEN
                } else {
                    throw CircuitBreakerOpenException("Circuit breaker is OPEN")
                }
            }
            State.HALF_OPEN -> {
                // Allow one test request
            }
            State.CLOSED -> {
                // Normal operation
            }
        }

        return try {
            val result = block()
            onSuccess()
            result
        } catch (e: Exception) {
            onFailure()
            throw e
        }
    }

    private fun onSuccess() {
        if (state == State.HALF_OPEN) {
            state = State.CLOSED
            failureCount.set(0)
            totalCount.set(0)
        }
    }

    private fun onFailure() {
        lastFailureTime = System.currentTimeMillis()
        val failures = failureCount.incrementAndGet()
        val total = totalCount.incrementAndGet()

        val failureRate = failures.toDouble() / total
        if (failureRate > config.threshold && total >= config.minRequests) {
            state = State.OPEN
        }
    }
}
```

---

## 12. CONSTRAINTS & LIMITATIONS

### 12.1 Functional Constraints

1. **Unary RPC Only**: Streaming not supported (major constraint)
2. **POST Method Only**: All HTTP requests must be POST
3. **JSON Format Only**: Binary Protocol Buffer not supported via HTTP
4. **Single Backend**: Each instance connects to one gRPC backend address
5. **No State**: Stateless proxy, no session management

### 12.2 Concurrency Constraints

1. **Non-Blocking Mandatory**: Blocking I/O not acceptable in production
2. **Thread Pool Limits**: Must configure thread pools appropriately for workload
3. **Connection Limits**: OS limits on open connections (file descriptors)
4. **Memory Limits**: In-memory buffering of requests/responses
5. **gRPC Stream Limits**: HTTP/2 max concurrent streams per connection

### 12.3 Performance Constraints

1. **Message Size**: Large messages (> 10MB) may cause memory pressure
2. **Conversion Overhead**: JSON ↔ Protobuf adds 5-10ms latency
3. **Backend Dependency**: Performance limited by slowest backend
4. **Network Latency**: Inter-service latency cannot be eliminated
5. **GC Pauses**: Garbage collection can cause latency spikes (JVM/Go)

### 12.4 Cancellation Constraints

1. **Backend Support**: Backend must respect gRPC cancellation signals for full benefits
2. **Detection Latency**: Client disconnect detection may have 100ms-1s delay (polling-based)
3. **In-Flight Work**: Work completed before cancellation detected cannot be undone
4. **Partial Cancellation**: Cannot cancel individual stages (e.g., JSON parsing alone)
5. **Best Effort**: Cancellation is best-effort; backend may ignore or not support it
6. **Cleanup Overhead**: Cancellation handling adds ~1-5ms overhead per request
7. **Race Conditions**: Response may arrive just as cancellation triggered (handle gracefully)

**Important Notes**:
- Always implement cancellation propagation even if backend doesn't support it
- Proxy-side resource cleanup is mandatory regardless of backend behavior
- Log backends that don't respect cancellation for monitoring
- Consider circuit breaker if backend consistently ignores cancellation

---

## APPENDICES

### APPENDIX A: Concurrency Patterns by Language

#### A.1 Kotlin (Coroutines)
```kotlin
// Suspending function (non-blocking)
suspend fun handleRequest(req: Request): Response {
    val proto = parseJson(req.body)  // Can be suspending
    val result = grpcClient.call(proto)  // Suspends here
    return convertToHttp(result)
}

// Coroutine dispatcher
val dispatcher = Dispatchers.IO.limitedParallelism(16)
```

#### A.2 Java (Virtual Threads)
```java
// Looks blocking, but using virtual threads (non-blocking at platform level)
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

executor.submit(() -> {
    Message proto = parseJson(request.getBody());
    Message result = grpcClient.call(proto);  // Blocks virtual thread (OK)
    return convertToHttp(result);
});
```

#### A.3 Go (Goroutines)
```go
// Goroutine (lightweight, non-blocking)
go func() {
    proto := parseJson(reqBody)
    result, err := grpcClient.Call(ctx, proto)  // Non-blocking at scheduler level
    if err != nil {
        sendError(err)
        return
    }
    sendResponse(convertToHttp(result))
}()
```

#### A.4 Rust (Async/Await)
```rust
// Async function
async fn handle_request(req: Request) -> Result<Response> {
    let proto = parse_json(&req.body).await?;
    let result = grpc_client.call(proto).await?;  // Awaits, doesn't block thread
    Ok(convert_to_http(result))
}

// Tokio runtime
#[tokio::main]
async fn main() {
    // Runtime handles non-blocking I/O
}
```

#### A.5 Python (Asyncio)
```python
# Async function
async def handle_request(request):
    proto = await parse_json(request.body)
    result = await grpc_client.call(proto)  # Awaits, event loop free
    return convert_to_http(result)

# Event loop
asyncio.run(handle_request(req))
```

---

### APPENDIX B: Performance Benchmarks

#### B.1 Expected Metrics

```yaml
single_instance:
  hardware:
    cpu: 8 cores
    memory: 4GB RAM
    network: 10 Gbps

  message_size: 1KB
  backend_latency: 20ms

  results:
    throughput: 10,000 req/s
    p50_latency: 25ms
    p95_latency: 35ms
    p99_latency: 50ms
    cpu_usage: 60%
    memory_usage: 2GB
    thread_count: 32

  efficiency:
    requests_per_core_per_second: 1,250
    memory_per_concurrent_request: 50KB
```

---

### APPENDIX C: Deployment Checklist

#### C.1 Pre-Deployment
```
☐ Configure thread pools for expected load
☐ Set appropriate timeouts (HTTP, gRPC)
☐ Enable monitoring (metrics, logging, tracing)
☐ Configure health check endpoints
☐ Set up alerts for key metrics
☐ Load test under expected traffic
☐ Stress test to find breaking point
☐ Verify graceful shutdown works
☐ Document operational runbook
```

#### C.2 Post-Deployment
```
☐ Monitor error rates
☐ Monitor latency (P50, P95, P99)
☐ Monitor resource usage (CPU, memory, threads)
☐ Monitor gRPC connection health
☐ Verify autoscaling triggers (if enabled)
☐ Test failover (kill one instance)
☐ Verify circuit breaker activates on backend failure
```

---

## GLOSSARY

**Async/Asynchronous**: Non-blocking operation that returns immediately, completing later
**Backpressure**: Mechanism to prevent overwhelming downstream systems
**Blocking I/O**: I/O operation that prevents thread from doing other work
**Cancellation**: Process of stopping an in-progress operation before completion
**Cancellation Propagation**: Passing cancellation signal through operation chain (HTTP → gRPC)
**Circuit Breaker**: Pattern to prevent cascading failures by failing fast
**Coroutine**: Lightweight concurrency primitive (suspendable function)
**Event Loop**: Single-threaded loop that handles I/O events
**Future/Promise**: Placeholder for async result
**Graceful Cancellation**: Allowing operation to cleanup before termination
**Non-Blocking I/O**: I/O operation that returns immediately, notifies when ready
**Reactive Streams**: Async stream processing with backpressure
**Stream Multiplexing**: Multiple logical streams over single connection (HTTP/2)
**Suspending Function**: Function that can pause execution without blocking thread
**Thread Pool**: Fixed set of threads for processing tasks
**Timeout**: Maximum time allowed for operation before cancellation
**Virtual Thread**: Lightweight thread managed by runtime (not OS)

---

## DOCUMENT METADATA

**Version**: 2.1 (Concurrency + Cancellation)
**Date**: 2025-11-12
**Primary Focus**: Non-Blocking, High-Concurrency Architecture with Cancellation Propagation
**Status**: Complete

**Key Changes from v2.0**:
- **Added Section 2.8**: Comprehensive request cancellation & propagation requirements
- HTTP client disconnect detection and handling
- Cancellation propagation patterns for all async models (Coroutines, Futures, Reactive, Go Context, Python asyncio)
- Timeout-based cancellation with multi-level hierarchy
- Cancellation metrics, monitoring, and testing requirements
- Graceful shutdown with cancellation support
- Edge cases and error handling for cancellation scenarios
- Cancellation constraints section (12.4)

**Key Changes from v1.0**:
- Elevated concurrency/non-blocking as primary architectural requirement
- Added detailed async execution patterns and timing diagrams
- Expanded threading model and resource pooling sections
- Added comprehensive backpressure and flow control requirements
- Included detailed performance characteristics and benchmarks
- Added concurrency testing strategies
- Expanded implementation patterns with async examples

---

**END OF DOCUMENT**
