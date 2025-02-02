package org.hle.user.exception;

public class InsufficientSharesException extends RuntimeException {
    public static final String MESSAGE = "User [id=%d] does not have enough shares to complete the transaction";

    public InsufficientSharesException(Integer userId) {
        super(MESSAGE.formatted(userId));
    }
}
