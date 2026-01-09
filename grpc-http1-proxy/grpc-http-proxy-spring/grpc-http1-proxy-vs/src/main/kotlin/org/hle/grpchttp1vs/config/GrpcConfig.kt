package org.hle.grpchttp1vs.config

import io.grpc.ManagedChannel
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.grpc.client.GrpcChannelFactory

@Configuration
class GrpcConfig {
    @Bean
    fun channel(factory: GrpcChannelFactory): ManagedChannel {
        return factory.createChannel("local")
    }
}
