package org.hle.grpchttp1proxy

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class GrpcHttp1ProxyApplication

fun main(args: Array<String>) {
    runApplication<GrpcHttp1ProxyApplication>(*args)
}
