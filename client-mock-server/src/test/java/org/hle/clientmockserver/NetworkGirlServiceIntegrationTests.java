package org.hle.clientmockserver;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.hle.clientmockserver.client.GirlClient;
import org.hle.clientmockserver.model.Girl;
import org.hle.clientmockserver.model.GirlRequest;
import org.hle.clientmockserver.model.GirlServiceGrpc;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.util.TestSocketUtils;

import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Boots the application under the {@code network} profile, which runs
 * {@code GirlService} on a real Netty gRPC server bound to a TCP port. Verifies
 * that both a standalone external client and the embedded {@link GirlClient}
 * reach the service over the network.
 */
@SpringBootTest
@ActiveProfiles("network")
class NetworkGirlServiceIntegrationTests {

    // One free port, shared by the server bind and both clients.
    static final int PORT = TestSocketUtils.findAvailableTcpPort();

    @DynamicPropertySource
    static void grpcProperties(DynamicPropertyRegistry registry) {
        // Bind the network server to the free port...
        registry.add("spring.grpc.server.port", () -> PORT);
        // ...and point the dogfooded client channel at the same port.
        registry.add("spring.grpc.client.channels.girl.address", () -> "static://localhost:" + PORT);
    }

    @Autowired
    GirlClient client;

    @Test
    void externalClient_connectsOverTcp() throws InterruptedException {
        // A standalone channel, independent of any Spring bean — a real external client.
        ManagedChannel channel = ManagedChannelBuilder
                .forAddress("localhost", PORT)
                .usePlaintext()
                .build();
        try {
            GirlServiceGrpc.GirlServiceBlockingStub stub = GirlServiceGrpc.newBlockingStub(channel);

            Girl girl = stub.getGirlById(GirlRequest.newBuilder().setGirlId(7).build());

            assertThat(girl.getId()).isEqualTo(7);
            assertThat(girl.getName()).isEqualTo("Test Girl");
            assertThat(girl.getStyle()).isEqualTo("Classic");
            assertThat(girl.getRating()).isEqualTo(5);
        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }

    @Test
    void embeddedClient_roundTripsOverNetwork() {
        Girl girl = client.getGirlById(1);

        assertThat(girl.getId()).isEqualTo(1);
        assertThat(girl.getName()).isEqualTo("Test Girl");
        assertThat(girl.getStyle()).isEqualTo("Classic");
        assertThat(girl.getRating()).isEqualTo(5);
    }
}
