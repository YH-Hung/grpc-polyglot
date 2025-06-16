package org.hle.grpchttp1proxy.handler

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.hle.grpchttp1proxy.dto.HelloRequestDto
import org.hle.grpchttp1proxy.dto.HelloReplyDto
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.http.MediaType
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.test.web.reactive.server.expectBody

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class HelloWorldHandlerTest {

    @Autowired
    private lateinit var webTestClient: WebTestClient

    @Test
    fun `test handleHelloWorld endpoint`() {
        val requestDto = HelloRequest.newBuilder().setName("Test User")

        webTestClient.post()
            .uri("/helloworld")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(requestDto)
            .exchange()
            .expectStatus().isOk
            .expectBody<HelloReply>()
            .consumeWith { response ->
                val responseBody = response.responseBody
                assert(responseBody != null)
                assert(responseBody!!.message.contains("Test User"))
            }
    }
}