package org.hle.clientmockserver.server;

import io.grpc.*;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.util.Arrays;

@Slf4j
public class GrpcServer {
    private final Server server;

    private GrpcServer(Server server) {
        this.server = server;
    }

    public static GrpcServer create(int port, BindableService... services) {
        var builder = ServerBuilder.forPort(port);
        Arrays.asList(services).forEach(builder::addService);

        return new GrpcServer(builder.build());
    }

    @PostConstruct
    public GrpcServer start() throws IOException {
        var services = server.getServices().stream()
                .map(ServerServiceDefinition::getServiceDescriptor)
                .map(ServiceDescriptor::getName)
                .toList();

        server.start();
        log.info("Server started on port {}, services{}", server.getPort(), services);

        return this;
    }

    public void await() throws InterruptedException {
        server.awaitTermination();     // block and wait someone call shutdown
    }

    @PreDestroy
    public void stop() {
        server.shutdownNow();
        log.info("Server stopped");
    }

}
