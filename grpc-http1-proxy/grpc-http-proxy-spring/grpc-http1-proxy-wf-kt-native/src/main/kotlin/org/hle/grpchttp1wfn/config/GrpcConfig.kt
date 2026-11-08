package org.hle.grpchttp1wfn.config

import io.grpc.ManagedChannel
import org.hle.grpchttp1wfn.gateway.Backends
import org.hle.grpchttp1wfn.gateway.GatewayProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.grpc.client.autoconfigure.GrpcClientProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.grpc.client.GrpcChannelFactory

@Configuration
@EnableConfigurationProperties(GatewayProperties::class)
class GrpcConfig {
    @Bean
    fun channel(factory: GrpcChannelFactory): ManagedChannel =
        factory.createChannel("local")

    @Bean
    fun backends(
        channel: ManagedChannel,
        factory: GrpcChannelFactory,
        grpc: GrpcClientProperties,
        gateway: GatewayProperties,
    ): Backends = Backends.open(channel, gateway, grpc.channels.keys) { name ->
        factory.createChannel(name)
    }
}
