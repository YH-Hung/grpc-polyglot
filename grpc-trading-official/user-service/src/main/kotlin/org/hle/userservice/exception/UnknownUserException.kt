package org.hle.userservice.exception

class UnknownUserException(userId: Int?) : RuntimeException(String.format(MESSAGE, userId)) {
    companion object {
        const val MESSAGE: String = "User [id=%d] is not found"
    }
}
