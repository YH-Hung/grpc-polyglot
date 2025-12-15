use prometheus::{Encoder, Gauge, HistogramVec, IntCounterVec, TextEncoder};
use std::net::SocketAddr;
use std::time::Instant;
use tonic::{transport::Server, Request, Response, Status};

pub mod helloworld {
    tonic::include_proto!("helloworld");
}

use helloworld::greeter_server::{Greeter, GreeterServer};
use helloworld::{HelloReply, HelloRequest};

lazy_static::lazy_static! {
    static ref REQUESTS_TOTAL: IntCounterVec = prometheus::register_int_counter_vec!(
        "grpc_requests_total",
        "Total number of gRPC requests",
        &["method", "status"]
    ).unwrap();

    static ref REQUEST_DURATION: HistogramVec = prometheus::register_histogram_vec!(
        "grpc_request_duration_seconds",
        "Duration of gRPC requests in seconds",
        &["method"]
    ).unwrap();

    static ref ACTIVE_CONNECTIONS: Gauge = prometheus::register_gauge!(
        "grpc_active_connections",
        "Number of active gRPC connections"
    ).unwrap();
}

const SERVER_NAME: &str = "Rust Server";
const VERSION: &str = "v2";

#[derive(Debug, Default)]
pub struct GreeterService {}

#[tonic::async_trait]
impl Greeter for GreeterService {
    async fn say_hello(
        &self,
        request: Request<HelloRequest>,
    ) -> Result<Response<HelloReply>, Status> {
        let start = Instant::now();

        ACTIVE_CONNECTIONS.inc();
        let _guard = scopeguard::guard((), |_| {
            ACTIVE_CONNECTIONS.dec();
        });

        let name = request.into_inner().name;
        println!("Received request from: {}", name);

        // Get architecture info
        let arch = format!("{}/{}", std::env::consts::OS, std::env::consts::ARCH);

        let reply = HelloReply {
            message: format!("Hello {}! Greetings from {} {}", name, SERVER_NAME, VERSION),
            server_name: SERVER_NAME.to_string(),
            server_version: VERSION.to_string(),
            architecture: arch,
        };

        // Record metrics
        REQUESTS_TOTAL
            .with_label_values(&["SayHello", "success"])
            .inc();
        REQUEST_DURATION
            .with_label_values(&["SayHello"])
            .observe(start.elapsed().as_secs_f64());

        Ok(Response::new(reply))
    }
}

async fn metrics_handler() -> Result<String, hyper::http::Error> {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();
    encoder.encode(&metric_families, &mut buffer).unwrap();

    Ok(String::from_utf8(buffer).unwrap())
}

async fn health_handler() -> Result<&'static str, hyper::http::Error> {
    Ok("OK")
}

async fn run_metrics_server(addr: SocketAddr) {
    use hyper::server::conn::http1;
    use hyper::service::service_fn;
    use hyper::{body::Incoming, Request as HyperRequest, Response as HyperResponse};
    use hyper_util::rt::TokioIo;
    use std::convert::Infallible;
    use tokio::net::TcpListener;

    async fn handle_request(
        req: HyperRequest<Incoming>,
    ) -> Result<HyperResponse<String>, Infallible> {
        let response = match req.uri().path() {
            "/metrics" => match metrics_handler().await {
                Ok(body) => HyperResponse::new(body),
                Err(_) => {
                    let mut resp = HyperResponse::new("Error".to_string());
                    *resp.status_mut() = hyper::StatusCode::INTERNAL_SERVER_ERROR;
                    resp
                }
            },
            "/health" => match health_handler().await {
                Ok(body) => HyperResponse::new(body.to_string()),
                Err(_) => {
                    let mut resp = HyperResponse::new("Error".to_string());
                    *resp.status_mut() = hyper::StatusCode::INTERNAL_SERVER_ERROR;
                    resp
                }
            },
            _ => {
                let mut resp = HyperResponse::new("Not Found".to_string());
                *resp.status_mut() = hyper::StatusCode::NOT_FOUND;
                resp
            }
        };

        Ok(response)
    }

    let listener = TcpListener::bind(addr).await.unwrap();
    println!("Metrics server listening on {}", addr);

    loop {
        let (stream, _) = listener.accept().await.unwrap();
        let io = TokioIo::new(stream);
        tokio::task::spawn(async move {
            if let Err(err) = http1::Builder::new()
                .serve_connection(io, service_fn(handle_request))
                .await
            {
                eprintln!("Error serving connection: {:?}", err);
            }
        });
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Log startup info
    println!("Starting {} {}", SERVER_NAME, VERSION);
    println!(
        "Runtime architecture: {}/{}",
        std::env::consts::OS,
        std::env::consts::ARCH
    );

    let grpc_addr = "[::]:50052".parse()?;
    let metrics_addr: SocketAddr = "0.0.0.0:9092".parse()?;

    let greeter = GreeterService::default();

    // Start metrics server in background
    tokio::spawn(async move {
        run_metrics_server(metrics_addr).await;
    });

    println!("gRPC server listening on {}", grpc_addr);

    // Start gRPC server with graceful shutdown
    Server::builder()
        .add_service(GreeterServer::new(greeter))
        .serve_with_shutdown(grpc_addr, async {
            tokio::signal::ctrl_c()
                .await
                .expect("failed to listen for shutdown signal");
            println!("Shutting down gracefully...");
        })
        .await?;

    Ok(())
}
