package org.hle.grpchttp1wfn

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class GrpcHttp1WfnApplication

fun main(args: Array<String>) {
    runApplication<GrpcHttp1WfnApplication>(*args)
}
