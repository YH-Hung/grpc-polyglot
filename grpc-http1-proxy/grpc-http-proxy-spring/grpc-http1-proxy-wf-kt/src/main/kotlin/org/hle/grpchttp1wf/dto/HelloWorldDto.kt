package org.hle.grpchttp1wf.dto

data class HelloRequestDto(
    val name: String
)

data class HelloReplyDto(
    val message: String
)