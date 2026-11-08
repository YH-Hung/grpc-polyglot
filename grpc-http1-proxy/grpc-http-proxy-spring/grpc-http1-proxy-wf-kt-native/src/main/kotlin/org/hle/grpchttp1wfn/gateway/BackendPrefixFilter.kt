package org.hle.grpchttp1wfn.gateway

import kotlinx.coroutines.withContext
import org.springframework.stereotype.Component
import org.springframework.web.server.CoWebFilter
import org.springframework.web.server.CoWebFilterChain
import org.springframework.web.server.ServerWebExchange

// CoWebFilter hands its coroutine context to suspend handler methods, which is how the controller's stub call sees the name.
@Component
class BackendPrefixFilter(private val backends: Backends) : CoWebFilter() {
    override suspend fun filter(exchange: ServerWebExchange, chain: CoWebFilterChain) {
        val path = exchange.request.path
        val (segment, rest) = splitPrefix(path.pathWithinApplication().value()) ?: return chain.filter(exchange)
        val name = backends.configuredName(segment) ?: return chain.filter(exchange)
        val rewritten = exchange.mutate()
            .request { it.path(path.contextPath().value() + rest) }
            .build()
        withContext(backendContext(name)) {
            chain.filter(rewritten)
        }
    }
}

private fun splitPrefix(path: String): Pair<String, String>? {
    if (!path.startsWith("/") || path.length < 2) {
        return null
    }
    val slash = path.indexOf('/', 1)
    if (slash == 1) {
        return null
    }
    if (slash < 0) {
        return path.substring(1) to "/"
    }
    return path.substring(1, slash) to path.substring(slash)
}
