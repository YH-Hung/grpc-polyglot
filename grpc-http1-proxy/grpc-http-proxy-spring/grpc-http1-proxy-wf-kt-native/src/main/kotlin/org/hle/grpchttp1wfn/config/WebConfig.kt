package org.hle.grpchttp1wfn.config

import com.google.protobuf.util.JsonFormat
import org.springframework.context.annotation.Configuration
import org.springframework.http.codec.ServerCodecConfigurer
import org.springframework.http.codec.protobuf.ProtobufJsonDecoder
import org.springframework.http.codec.protobuf.ProtobufJsonEncoder
import org.springframework.web.reactive.config.WebFluxConfigurer

@Configuration
class WebConfig : WebFluxConfigurer {

    override fun configureHttpMessageCodecs(configurer: ServerCodecConfigurer) {
        configurer.customCodecs().apply {
            register(ProtobufJsonEncoder(JsonFormat.printer().omittingInsignificantWhitespace()))
            register(ProtobufJsonDecoder(JsonFormat.parser().ignoringUnknownFields()))
        }
    }
}
