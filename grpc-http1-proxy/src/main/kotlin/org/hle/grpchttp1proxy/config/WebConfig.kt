package org.hle.grpchttp1proxy.config

import org.springframework.context.annotation.Bean
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
         configurer.customCodecs().register(ProtobufJsonEncoder());
         configurer.customCodecs().register(ProtobufJsonDecoder());
    }
//    @Bean
//    fun proxyRouter(helloWorldHandler: HelloWorldHandler): RouterFunction<ServerResponse> {
//        return coRouter {
//            POST("/helloworld", helloWorldHandler::handleHelloWorld)
//        }
//    }
}
