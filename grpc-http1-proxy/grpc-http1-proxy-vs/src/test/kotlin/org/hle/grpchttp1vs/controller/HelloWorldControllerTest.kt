package org.hle.grpchttp1vs.controller

import org.hle.grpchttp1vs.dto.HelloReplyDto
import org.hle.grpchttp1vs.dto.HelloRequestDto
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webtestclient.autoconfigure.AutoConfigureWebTestClient
import org.springframework.http.MediaType
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.test.web.reactive.server.expectBody

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class HelloWorldControllerTest {

    @Autowired
    private lateinit var webTestClient: WebTestClient

    @Test
    fun `test helloWorld endpoint`() {
        val requestDto = HelloRequestDto("Test User")

        webTestClient.post()
            .uri("/helloworld/say-hello")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(requestDto)
            .exchange()
            .expectBody<HelloReplyDto>()
            .consumeWith { response ->
                val responseBody = response.responseBody
                assert(responseBody != null)
                assert(responseBody!!.message.contains("Test User"))
            }
    }
}
