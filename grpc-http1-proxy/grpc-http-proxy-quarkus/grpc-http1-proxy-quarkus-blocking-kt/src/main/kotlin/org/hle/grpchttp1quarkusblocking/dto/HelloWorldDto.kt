package org.hle.grpchttp1quarkusblocking.dto

data class HelloRequestDto(
    var name: String = ""
)

data class HelloReplyDto(
    var message: String = ""
)
