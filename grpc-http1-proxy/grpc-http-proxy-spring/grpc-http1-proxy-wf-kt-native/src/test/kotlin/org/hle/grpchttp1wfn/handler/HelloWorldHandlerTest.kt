package org.hle.grpchttp1wfn.handler

import io.grpc.examples.helloworld.HelloRequest
import io.grpc.examples.helloworld.HelloReply
import kotlinx.coroutines.runBlocking
import org.hle.grpchttp1wfn.client.HelloWorldClient
import org.hle.grpchttp1wfn.dto.HelloReplyDto
import org.hle.grpchttp1wfn.dto.HelloRequestDto
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import org.mockito.Mockito.`when`
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webtestclient.autoconfigure.AutoConfigureWebTestClient
import org.springframework.http.MediaType
import org.springframework.test.context.bean.override.mockito.MockitoBean
import org.springframework.test.web.reactive.server.WebTestClient
import org.springframework.test.web.reactive.server.expectBody

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class HelloWorldHandlerTest {

    @Autowired
    private lateinit var webTestClient: WebTestClient

    @MockitoBean
    private lateinit var helloWorldClient: HelloWorldClient

    @BeforeEach
    fun setup() {
        runBlocking {
            `when`(helloWorldClient.sayHello(Mockito.any(HelloRequest::class.java) ?: HelloRequest.getDefaultInstance())).thenReturn(
                HelloReply.newBuilder().setMessage("Hello Test User").build()
            )
        }
    }

    @Test
    fun `test handleHelloWorld endpoint`() {
        val requestDto = HelloRequestDto("Test User")

        webTestClient.post()
            .uri("/helloworld/say-hello")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(requestDto)
            .exchange()
            .expectStatus().isOk
            .expectBody<HelloReplyDto>()
            .consumeWith { response ->
                val responseBody = response.responseBody
                assert(responseBody != null)
                assert(responseBody!!.message.contains("Test User"))
            }
    }
}
