package org.hle.grpchttp1quarkusblocking.gateway

import io.grpc.Channel
import io.quarkus.grpc.GrpcClient
import io.quarkus.runtime.Startup
import jakarta.enterprise.context.ApplicationScoped
import jakarta.enterprise.context.RequestScoped
import jakarta.enterprise.inject.Instance
import org.eclipse.microprofile.config.Config
import org.eclipse.microprofile.config.inject.ConfigProperty
import java.util.Optional

private val LEGAL_NAME = Regex("[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
private val RESERVED_NAMES = setOf("helloworld", "hello-girl")
private const val LOCAL_CHANNEL = "local"

@JvmInline
value class BackendName internal constructor(val value: String)

@RequestScoped
class BackendSelection {
    var name: BackendName? = null

    fun label(): String = name?.value ?: LOCAL_CHANNEL
}

// Application-scoped so the routing interceptor holds a proxy while this bean builds the slot channels.
@Startup
@ApplicationScoped
class Backends(
    @ConfigProperty(name = "proxy.gateway.backends") listed: Optional<List<String>>,
    config: Config,
    @GrpcClient("p1") p1: Instance<Channel>,
    @GrpcClient("p2") p2: Instance<Channel>,
) {
    private val byName: Map<BackendName, Channel>

    init {
        val slots = mapOf("p1" to p1, "p2" to p2)
        // Every client name resolves a localhost host from Quarkus defaults, which sit at the minimum ordinal.
        val configured = slots.keys.filterTo(mutableSetOf()) {
            config.getConfigValue("quarkus.grpc.clients.$it.host").sourceOrdinal > Int.MIN_VALUE
        }
        val names = parseGateway(listed.orElse(emptyList()), slots.keys, configured)
        byName = names.associateWith { slots.getValue(it.value).get() }
    }

    fun configuredName(segment: String): BackendName? = BackendName(segment).takeIf { it in byName }

    fun channel(name: BackendName): Channel = byName.getValue(name)
}

internal class GatewayConfigException(val problems: List<String>) :
    IllegalArgumentException(problems.joinToString("; "))

internal fun parseGateway(raw: List<String>, slots: Set<String>, configured: Set<String>): List<BackendName> {
    val problems = mutableListOf<String>()
    val seen = mutableSetOf<String>()
    for (token in raw) {
        when {
            !seen.add(token) -> problems += "duplicate backend name: $token"
            !LEGAL_NAME.matches(token) -> problems += "illegal backend name: $token"
            token in RESERVED_NAMES -> problems += "reserved backend name: $token"
            token !in slots -> problems += "no gateway slot for backend: $token"
            token !in configured -> problems += "no quarkus.grpc.clients.$token.host for backend: $token"
        }
    }
    if (problems.isNotEmpty()) {
        throw GatewayConfigException(problems)
    }
    return raw.map { BackendName(it) }
}
