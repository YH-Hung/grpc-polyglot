package org.hle.grpchttp1proxy.dto

data class HelloRequestDto(
    val name: String
)

data class HelloReplyDto(
    val message: String
)