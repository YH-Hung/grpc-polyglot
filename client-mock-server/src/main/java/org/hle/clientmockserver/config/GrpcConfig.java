package org.hle.clientmockserver.config;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GrpcConfig {
    @Value("${grpc.server.url}")
    private String grpcServerUrl;

    @Value("${grpc.server.port}")
    private int grpcServerPort;

    @Bean
    public ManagedChannel grpcChannel() {

        return ManagedChannelBuilder.forAddress(grpcServerUrl, grpcServerPort)
                .usePlaintext()
                .build();
    }
}
