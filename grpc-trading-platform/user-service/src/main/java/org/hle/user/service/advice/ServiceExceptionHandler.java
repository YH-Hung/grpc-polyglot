package org.hle.user.service.advice;

import org.hle.user.exception.InsufficientBalanceException;
import org.hle.user.exception.InsufficientSharesException;
import org.hle.user.exception.UnknownTickerException;
import org.hle.user.exception.UnknownUserException;
import io.grpc.Status;
import net.devh.boot.grpc.server.advice.GrpcAdvice;
import net.devh.boot.grpc.server.advice.GrpcExceptionHandler;

@GrpcAdvice
public class ServiceExceptionHandler {
    @GrpcExceptionHandler(UnknownTickerException.class)
    public Status handleInvalidArguments(UnknownTickerException ex) {
        return Status.INVALID_ARGUMENT.withDescription(ex.getMessage()).withCause(ex.getCause());
    }

    @GrpcExceptionHandler(UnknownUserException.class)
    public Status handleUnknownUser(UnknownUserException ex) {
        return Status.NOT_FOUND.withDescription(ex.getMessage()).withCause(ex.getCause());
    }

    @GrpcExceptionHandler({InsufficientBalanceException.class, InsufficientSharesException.class})
    public Status handlePreconditionFailures(Exception ex) {
        return Status.FAILED_PRECONDITION.withDescription(ex.getMessage()).withCause(ex.getCause());
    }
}
