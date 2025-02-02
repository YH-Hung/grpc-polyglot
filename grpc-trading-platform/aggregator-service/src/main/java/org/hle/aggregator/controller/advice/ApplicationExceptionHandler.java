package org.hle.aggregator.controller.advice;

import io.grpc.StatusRuntimeException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;

@ControllerAdvice
public class ApplicationExceptionHandler {

    @ExceptionHandler(StatusRuntimeException.class)
    public ResponseEntity<String> handleStatusRuntimeException(StatusRuntimeException ex){
        return switch (ex.getStatus().getCode()) {
            case INVALID_ARGUMENT, FAILED_PRECONDITION -> ResponseEntity.badRequest().body(ex.getStatus().getDescription());
            case NOT_FOUND -> ResponseEntity.notFound().build();
            default -> ResponseEntity.internalServerError().body(ex.getMessage());
        };
    }
}
