package org.hle.clientmockserver;

import org.awaitility.Awaitility;
import org.hle.clientmockserver.client.GirlClient;
import org.hle.clientmockserver.job.LongRunJob;
import org.hle.clientmockserver.server.GrpcServer;
import org.hle.clientmockserver.service.GirlService;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.io.IOException;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@SpringBootTest
class ClientMockServerApplicationTests {
    private final GrpcServer server = GrpcServer.create(6565, new GirlService());

    @Autowired
    GirlClient client;

    @BeforeAll
    public void beforeAll() throws IOException {
        server.start();
    }

    @AfterAll
    public void afterAll() {
        server.stop();
    }

    @Test
    void contextLoads() {
        client.getGirlById(1);
    }

    @Test
    void long_run_test() {
        var job = new LongRunJob(5_000);
        CompletableFuture.runAsync(job::longRun);
        Awaitility.await().until(job::isCompleted);
        assertThat(job.isCompleted()).isTrue();
    }
}
