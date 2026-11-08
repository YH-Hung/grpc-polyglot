package org.hle.grpchttp1wf.gateway

import org.hle.grpchttp1wf.GrpcHttp1WfApplication
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.springframework.boot.SpringApplication
import org.springframework.context.ConfigurableApplicationContext

class GatewayStartupFailureTest {

    @Test
    fun `missing channel block fails context load`() {
        val application = SpringApplication(GrpcHttp1WfApplication::class.java)
        application.setRegisterShutdownHook(false)
        var context: ConfigurableApplicationContext? = null
        val failure = assertThrows<Exception> {
            context = application.run("--proxy.gateway.backends=missing", "--server.port=0")
        }
        context?.close()

        val chain = generateSequence<Throwable>(failure) { it.cause }.toList()
        assertTrue(
            chain.any { it is GatewayConfigException && it.problems.any { problem -> problem.contains("missing") } },
            chain.joinToString(" | ") { "${it.javaClass.name}: ${it.message}" },
        )
    }
}
