package org.hle.grpchttp1quarkusblocking.gateway

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class ParseGatewayTest {

    private val slots = setOf("p1", "p2")

    @Test
    fun `accepts configured slots and an empty list`() {
        assertEquals(listOf("p1", "p2"), parseGateway(listOf("p1", "p2"), slots, slots).map { it.value })
        assertEquals(emptyList<BackendName>(), parseGateway(emptyList(), slots, emptySet()))
    }

    @Test
    fun `collects duplicate syntax reserved unknown slot and missing host`() {
        val failure = assertThrows<GatewayConfigException> {
            parseGateway(
                listOf("p1", "p1", "Bad", "helloworld", "hello-girl", "p9", "p2"),
                slots,
                setOf("p1"),
            )
        }

        val problems = failure.problems
        assertEquals(6, problems.size)
        assertTrue(problems.any { it.contains("duplicate") && it.contains("p1") })
        assertTrue(problems.any { it.contains("illegal") && it.contains("Bad") })
        assertTrue(problems.any { it.contains("reserved") && it.contains("helloworld") })
        assertTrue(problems.any { it.contains("reserved") && it.contains("hello-girl") })
        assertTrue(problems.any { it.contains("slot") && it.contains("p9") })
        assertTrue(problems.any { it.contains("host") && it.contains("p2") })
    }

    @Test
    fun `split keeps the remaining raw path under the base`() {
        assertEquals("p1" to "/helloworld/say-hello", splitPrefix("/", "/p1/helloworld/say-hello"))
        assertEquals("p1" to "/", splitPrefix("/", "/p1"))
        assertEquals("p1" to "/api/a%2Fb", splitPrefix("/api/", "/api/p1/a%2Fb"))
        assertNull(splitPrefix("/", "/"))
        assertNull(splitPrefix("/", "//x"))
    }
}
