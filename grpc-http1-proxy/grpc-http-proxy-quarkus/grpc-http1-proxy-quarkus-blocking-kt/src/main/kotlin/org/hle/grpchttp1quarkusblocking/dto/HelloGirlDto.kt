package org.hle.grpchttp1quarkusblocking.dto

data class HelloGirlRequestDto(
    var name: String = "",
    var spouse: String = "",
    var firstRound: Int = 0
)

data class HelloGirlReplyDto(
    var message: String = "",
    var marriage: String = "",
    var size: Int = 0
)
