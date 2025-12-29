package org.hle.grpchttp1wf

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class GrpcHttp1WfApplication

fun main(args: Array<String>) {
    runApplication<GrpcHttp1WfApplication>(*args)
}
