package org.hle.userservice.exception

class InsufficientSharesException(userId: Int?) : RuntimeException(String.format(MESSAGE, userId)) {
    companion object {
        const val MESSAGE: String = "User [id=%d] does not have enough shares to complete the transaction"
    }
}
