package org.hle.clientmockserver.client;

import io.grpc.ManagedChannel;
import lombok.extern.slf4j.Slf4j;
import org.hle.clientmockserver.model.GirlRequest;
import org.hle.clientmockserver.model.Girl;
import org.hle.clientmockserver.model.GirlServiceGrpc;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class GirlClient {

    private final GirlServiceGrpc.GirlServiceBlockingStub girlServiceStub;

    public GirlClient(ManagedChannel grpcChannel) {
        // Create a blocking stub using the injected gRPC channel
        this.girlServiceStub = GirlServiceGrpc.newBlockingStub(grpcChannel);
    }

    /**
     * Fetches a Girl by ID via gRPC call.
     *
     * @param girlId the ID of the girl to fetch
     * @return Girl object returned by the server
     */
    public Girl getGirlById(int girlId) {
        // Build the request
        GirlRequest request = GirlRequest.newBuilder()
                .setGirlId(girlId)
                .build();

        // Perform the gRPC call to the server
        Girl girl = girlServiceStub.getGirlById(request);
        log.info("Fetching Girl with ID {} get {}", request.getGirlId(), girl);

        return girl;
    }
}