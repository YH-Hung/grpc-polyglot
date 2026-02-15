package org.hle.grpchttp1vs.config

import io.grpc.ManagedChannel
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.grpc.client.ChannelBuilderOptions
import org.springframework.grpc.client.GrpcChannelFactory

@Configuration
class GrpcConfig {
    @Bean
    fun channel(factory: GrpcChannelFactory): ManagedChannel {
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
        val options = ChannelBuilderOptions.defaults()
            .withCustomizer { _, builder ->
                builder.defaultServiceConfig(serviceConfig).enableRetry()
            }
        return factory.createChannel("local", options)
    }
}
