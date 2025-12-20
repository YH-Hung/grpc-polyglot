package org.hle.grpchttp1wf.config

import com.google.protobuf.util.JsonFormat
import org.springframework.context.annotation.Configuration
import org.springframework.http.codec.ServerCodecConfigurer
import org.springframework.http.codec.protobuf.ProtobufJsonDecoder
import org.springframework.http.codec.protobuf.ProtobufJsonEncoder
import org.springframework.web.reactive.config.WebFluxConfigurer

@Configuration
class WebConfig : WebFluxConfigurer {

    override fun configureHttpMessageCodecs(configurer: ServerCodecConfigurer) {
        // For treating protobuf message as json payload
        // Similar functionality with Spring Web MVC ProtobufJsonFormatHttpMessageConverter
         configurer.customCodecs().register(ProtobufJsonEncoder(JsonFormat.printer().omittingInsignificantWhitespace()))
         configurer.customCodecs().register(ProtobufJsonDecoder(JsonFormat.parser().ignoringUnknownFields()))
    }
}
