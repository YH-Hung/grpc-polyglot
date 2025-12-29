package org.hle.grpchttp1vs.controller

import io.grpc.examples.helloworld.HelloReply
import io.grpc.examples.helloworld.HelloRequest
import org.hle.grpchttp1vs.client.HelloWorldClient
import org.hle.grpchttp1vs.dto.HelloReplyDto
import org.hle.grpchttp1vs.dto.HelloRequestDto
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import org.mockito.Mockito.`when`
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.bean.override.mockito.MockitoBean
import org.springframework.boot.webtestclient.autoconfigure.AutoConfigureWebTestClient
import org.springframework.http.MediaType
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.test.web.reactive.server.expectBody

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class HelloWorldControllerTest {

    @Autowired
    private lateinit var webTestClient: WebTestClient

    @MockitoBean
    private lateinit var helloWorldClient: HelloWorldClient

    @BeforeEach
    fun setup() {
        `when`(helloWorldClient.sayHello(Mockito.any(HelloRequest::class.java) ?: HelloRequest.getDefaultInstance())).thenReturn(
            HelloReply.newBuilder().setMessage("Hello Test User").build()
        )
    }

    @Test
    fun `test helloWorld endpoint`() {
        val requestDto = HelloRequestDto("Test User")

        webTestClient.post()
            .uri("/helloworld/say-hello")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(requestDto)
            .exchange()
            .expectStatus().isOk
            .expectBody<String>()
            .consumeWith { response ->
                val responseBody = response.responseBody
                assert(responseBody != null)
                assert(responseBody!!.contains("Hello Test User"))
            }
    }
}
