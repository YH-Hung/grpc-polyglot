package org.hle.grpchttp1wf.gateway

import kotlinx.coroutines.asContextElement
import kotlinx.coroutines.withContext
import org.springframework.core.Ordered
import org.springframework.core.annotation.Order
import org.springframework.stereotype.Component
import org.springframework.web.server.CoWebFilter
import org.springframework.web.server.CoWebFilterChain
import org.springframework.web.server.ServerWebExchange

// Suspending handlers run in the context this filter leaves on the exchange, and
// withContext(Dispatchers.IO) inherits the element, so the blocking stub sees the name on its IO thread.
@Order(Ordered.HIGHEST_PRECEDENCE)
@Component
class BackendPrefixFilter(private val backends: Backends) : CoWebFilter() {
    override suspend fun filter(exchange: ServerWebExchange, chain: CoWebFilterChain) {
        val path = exchange.request.path
        val split = splitPrefix(path.pathWithinApplication().value())
        val name = split?.let { (segment, _) -> backends.configuredName(segment) }
        if (split == null || name == null) {
            chain.filter(exchange)
            return
        }
        val request = exchange.request.mutate()
            .path(path.contextPath().value() + split.second)
            .build()
        withContext(currentBackend.asContextElement(name)) {
            chain.filter(exchange.mutate().request(request).build())
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
