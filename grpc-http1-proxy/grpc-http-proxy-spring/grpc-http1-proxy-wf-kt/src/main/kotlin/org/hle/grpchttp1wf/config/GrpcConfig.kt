package org.hle.grpchttp1wf.config

import io.grpc.ManagedChannel
import org.hle.grpchttp1wf.gateway.Backends
import org.hle.grpchttp1wf.gateway.GatewayProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.grpc.client.autoconfigure.GrpcClientProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.grpc.client.GrpcChannelFactory

@Configuration
@EnableConfigurationProperties(GatewayProperties::class)
class GrpcConfig {
    @Bean
    fun channel(factory: GrpcChannelFactory): ManagedChannel {
        return factory.createChannel("local")
    }

    @Bean
    fun backends(
        channel: ManagedChannel,
        factory: GrpcChannelFactory,
        grpc: GrpcClientProperties,
        gateway: GatewayProperties,
    ): Backends {
        return Backends.open(channel, gateway, grpc.channels.keys) { name ->
            factory.createChannel(name)
        }
    }
}
