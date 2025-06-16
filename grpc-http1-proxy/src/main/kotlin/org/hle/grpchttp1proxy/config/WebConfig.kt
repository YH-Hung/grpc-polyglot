package org.hle.grpchttp1proxy.config

import org.hle.grpchttp1proxy.handler.HelloWorldHandler
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.reactive.config.WebFluxConfigurer
import org.springframework.web.reactive.function.server.RouterFunction
import org.springframework.web.reactive.function.server.ServerResponse
import org.springframework.web.reactive.function.server.coRouter

@Configuration
class WebConfig : WebFluxConfigurer {

//    @Bean
//    fun proxyRouter(helloWorldHandler: HelloWorldHandler): RouterFunction<ServerResponse> {
//        return coRouter {
//            POST("/helloworld", helloWorldHandler::handleHelloWorld)
//        }
//    }
}
