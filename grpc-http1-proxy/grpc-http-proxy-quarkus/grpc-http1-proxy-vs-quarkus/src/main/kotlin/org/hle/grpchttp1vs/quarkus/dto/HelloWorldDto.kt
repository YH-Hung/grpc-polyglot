package org.hle.grpchttp1vs.quarkus.dto

data class HelloRequestDto(
    var name: String = ""
)

data class HelloReplyDto(
    var message: String = ""
)
