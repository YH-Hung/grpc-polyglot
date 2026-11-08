package org.hle.grpchttp1wf.gateway

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class ParseGatewayTest {

    @Test
    fun `accepts p1 and p2`() {
        val names = parseGateway(listOf("p1", "p2"), setOf("local", "p1", "p2"))

        assertEquals(listOf("p1", "p2"), names.map { it.value })
    }

    @Test
    fun `collects duplicate syntax reserved and missing channel`() {
        val failure = assertThrows<GatewayConfigException> {
            parseGateway(
                listOf("p1", "p1", "Bad", "helloworld", "hello-girl", "missing"),
                setOf("local", "p1", "helloworld", "hello-girl"),
            )
        }

        val problems = failure.problems
        assertEquals(5, problems.size)
        assertTrue(problems.any { it.contains("duplicate") && it.contains("p1") })
        assertTrue(problems.any { it.contains("illegal") && it.contains("Bad") })
        assertTrue(problems.any { it.contains("reserved") && it.contains("helloworld") })
        assertTrue(problems.any { it.contains("reserved") && it.contains("hello-girl") })
        assertTrue(problems.any { it.contains("missing") })
    }
}
