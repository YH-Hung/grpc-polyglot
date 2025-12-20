package org.hle.grpchttp1vs

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class GrpcHttp1VsApplication

fun main(args: Array<String>) {
    runApplication<GrpcHttp1VsApplication>(*args)
}
