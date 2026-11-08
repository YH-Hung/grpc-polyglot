package org.hle.grpchttp1vs.config

import io.grpc.ManagedChannel
import org.hle.grpchttp1vs.gateway.Backends
import org.hle.grpchttp1vs.gateway.GatewayProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.boot.grpc.client.autoconfigure.GrpcClientProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.grpc.client.ChannelBuilderOptions
import org.springframework.grpc.client.GrpcChannelFactory

@Configuration
@EnableConfigurationProperties(GatewayProperties::class)
class GrpcConfig {
    @Bean
    fun channel(factory: GrpcChannelFactory): ManagedChannel {
        return factory.createChannel("local", options())
    }

    @Bean
    fun backends(
        channel: ManagedChannel,
        factory: GrpcChannelFactory,
        grpc: GrpcClientProperties,
        gateway: GatewayProperties,
    ): Backends {
        return Backends.open(channel, gateway, grpc.channels.keys) { name ->
            factory.createChannel(name, options())
        }
    }

    private fun options(): ChannelBuilderOptions {
        val retryPolicy = mapOf(
            "maxAttempts" to 4.0,
            "initialBackoff" to "0.1s",
            "maxBackoff" to "1s",
            "backoffMultiplier" to 2.0,
            "retryableStatusCodes" to listOf("UNAVAILABLE")
        )
        val serviceConfig = mapOf(
            "methodConfig" to listOf(
                mapOf(
                    "name" to listOf(mapOf<String, Any>()),
                    "retryPolicy" to retryPolicy
                )
            )
        )
        return ChannelBuilderOptions.defaults()
            .withCustomizer { _, builder ->
                builder.defaultServiceConfig(serviceConfig).enableRetry()
            }
    }
}
