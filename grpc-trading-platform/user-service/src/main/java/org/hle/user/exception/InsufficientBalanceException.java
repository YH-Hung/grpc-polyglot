package org.hle.user.exception;

public class InsufficientBalanceException extends RuntimeException {
    public static final String MESSAGE = "User [id=%d] does not have enough fund to complete the transaction.";

    public InsufficientBalanceException(Integer userId) {
        super(String.format(MESSAGE, userId));
    }
}
