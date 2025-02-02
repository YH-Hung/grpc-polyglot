package org.hle.user.exception;

public class UnknownUserException extends RuntimeException {
    public static final String MESSAGE = "User [id=%d] is not found";

    public UnknownUserException(Integer userId) {
        super(String.format(MESSAGE, userId));
    }
}
