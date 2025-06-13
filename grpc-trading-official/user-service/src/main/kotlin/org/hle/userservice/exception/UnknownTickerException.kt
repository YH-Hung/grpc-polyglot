package org.hle.userservice.exception

object UnknownTickerException : RuntimeException() {
    const val MESSAGE: String = "Ticker is not found"
}
