package org.hle.clientmockserver.client;

import lombok.extern.slf4j.Slf4j;
import org.hle.clientmockserver.model.GirlRequest;
import org.hle.clientmockserver.model.Girl;
import org.hle.clientmockserver.model.GirlServiceGrpc;
import org.springframework.grpc.client.GrpcChannelFactory;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class GirlClient {

    private final GirlServiceGrpc.GirlServiceBlockingStub girlServiceStub;

    public GirlClient(GrpcChannelFactory channels) {
        // Build a blocking stub over the "girl" channel (configured to target the in-process server)
        this.girlServiceStub = GirlServiceGrpc.newBlockingStub(channels.createChannel("girl"));
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