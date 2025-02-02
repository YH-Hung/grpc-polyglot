package org.hle.user.exception;

public class UnknownTickerException extends RuntimeException {
    public static final String MESSAGE = "Ticker is not found";

    public UnknownTickerException() {
        super(MESSAGE);
    }
}
