package org.hle.clientmockserver;

import org.hle.clientmockserver.client.GirlClient;
import org.hle.clientmockserver.model.Girl;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.grpc.test.autoconfigure.AutoConfigureInProcessTransport;
import org.springframework.boot.test.context.SpringBootTest;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Exercises the gRPC {@link GirlClient} against the {@code GirlService} running on the
 * in-process gRPC server started by {@link AutoConfigureInProcessTransport}.
 */
@SpringBootTest
@AutoConfigureInProcessTransport
class ClientMockServerApplicationTests {

    @Autowired
    GirlClient client;

    @Test
    void getGirlById_returnsGirlFromInProcessServer() {
        Girl girl = client.getGirlById(1);

        assertThat(girl.getId()).isEqualTo(1);
        assertThat(girl.getName()).isEqualTo("Test Girl");
        assertThat(girl.getStyle()).isEqualTo("Classic");
        assertThat(girl.getRating()).isEqualTo(5);
    }

    @Test
    void getGirlById_echoesRequestedId() {
        assertThat(client.getGirlById(42).getId()).isEqualTo(42);
    }
}
