package org.hle.grpchttp1vs.gateway

import io.grpc.Channel
import org.springframework.boot.context.properties.ConfigurationProperties

private val LEGAL_NAME = Regex("[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
private val RESERVED_NAMES = setOf("helloworld", "hello-girl")
private const val LOCAL_CHANNEL = "local"

internal const val BACKEND_REQUEST_ATTRIBUTE = "org.hle.grpchttp1vs.gateway.BackendName"

@JvmInline
value class BackendName internal constructor(val value: String) {
    companion object {
        internal fun takeIfLegal(raw: String): BackendName? {
            if (!LEGAL_NAME.matches(raw)) {
                return null
            }
            return BackendName(raw)
        }
    }
}

@ConfigurationProperties("proxy.gateway")
class GatewayProperties {
    var backends: List<String> = emptyList()
}

class Backends private constructor(
    private val local: Channel,
    private val byName: Map<BackendName, Channel>,
) {
    fun channel(name: BackendName?): Channel {
        if (name == null) {
            return local
        }
        return byName.getValue(name)
    }

    fun configuredName(segment: String): BackendName? {
        val name = BackendName.takeIfLegal(segment) ?: return null
        if (name !in byName) {
            return null
        }
        return name
    }

    fun label(name: BackendName?): String = name?.value ?: LOCAL_CHANNEL

    companion object {
        fun open(
            local: Channel,
            gateway: GatewayProperties,
            configuredChannelNames: Set<String>,
            open: (String) -> Channel,
        ): Backends {
            val names = parseGateway(gateway.backends, configuredChannelNames)
            val byName = names.associateWith { name ->
                if (name.value == LOCAL_CHANNEL) {
                    local
                } else {
                    open(name.value)
                }
            }
            return Backends(local, byName)
        }
    }
}

internal class GatewayConfigException(val problems: List<String>) :
    IllegalArgumentException(problems.joinToString("; "))

internal fun parseGateway(raw: List<String>, configuredChannels: Set<String>): List<BackendName> {
    val problems = mutableListOf<String>()
    val seen = mutableSetOf<String>()
    for (token in raw) {
        if (!seen.add(token)) {
            problems += "duplicate backend name: $token"
            continue
        }
        if (!LEGAL_NAME.matches(token)) {
            problems += "illegal backend name: $token"
            continue
        }
        if (token in RESERVED_NAMES) {
            problems += "reserved backend name: $token"
            continue
        }
        // An unknown name would otherwise dial spring-grpc's default localhost:9090.
        if (token !in configuredChannels) {
            problems += "no channel block for backend: $token"
        }
    }
    if (problems.isNotEmpty()) {
        throw GatewayConfigException(problems)
    }
    return raw.map { BackendName(it) }
}
