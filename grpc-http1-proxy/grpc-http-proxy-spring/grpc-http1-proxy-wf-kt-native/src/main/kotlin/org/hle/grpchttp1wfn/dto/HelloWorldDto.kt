package org.hle.grpchttp1wfn.dto

data class HelloRequestDto(
    val name: String
)

data class HelloReplyDto(
    val message: String
)
