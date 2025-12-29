package org.hle.grpchttp1vs.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.converter.protobuf.ProtobufJsonFormatHttpMessageConverter

@Configuration
class WebConfig {

    @Bean
    fun protobufJsonFormatHttpMessageConverter(): ProtobufJsonFormatHttpMessageConverter {
        return ProtobufJsonFormatHttpMessageConverter()
    }
}
