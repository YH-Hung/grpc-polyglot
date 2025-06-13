package org.hle.userservice.exception

class InsufficientBalanceException(userId: Int?) : RuntimeException(String.format(MESSAGE, userId)) {
    companion object {
        const val MESSAGE: String = "User [id=%d] does not have enough fund to complete the transaction."
    }
}
