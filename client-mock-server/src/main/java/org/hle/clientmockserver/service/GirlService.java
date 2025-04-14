package org.hle.clientmockserver.service;

import io.grpc.stub.StreamObserver;
import org.hle.clientmockserver.model.Girl;
import org.hle.clientmockserver.model.GirlRequest;
import org.hle.clientmockserver.model.GirlServiceGrpc;

public class GirlService extends GirlServiceGrpc.GirlServiceImplBase {
    @Override
    public void getGirlById(GirlRequest request, StreamObserver<Girl> responseObserver) {
        Girl girl = Girl.newBuilder()
                .setId(request.getGirlId())
                .setName("Test Girl")
                .setStyle("Classic")
                .setRating(5)
                .build();

        responseObserver.onNext(girl);
        responseObserver.onCompleted();
    }
}
