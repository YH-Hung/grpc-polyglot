package org.hle.grpchttp1quarkusblocking.gateway

import jakarta.ws.rs.container.ContainerRequestContext
import jakarta.ws.rs.container.ContainerRequestFilter
import jakarta.ws.rs.container.PreMatching
import jakarta.ws.rs.ext.Provider

@Provider
@PreMatching
class BackendPrefixFilter(
    private val backends: Backends,
    private val selection: BackendSelection,
) : ContainerRequestFilter {
    override fun filter(request: ContainerRequestContext) {
        val uri = request.uriInfo
        val (segment, rest) = splitPrefix(uri.baseUri.rawPath, uri.requestUri.rawPath) ?: return
        val name = backends.configuredName(segment) ?: return
        selection.name = name
        request.setRequestUri(uri.requestUriBuilder.replacePath(rest).build())
    }
}

internal fun splitPrefix(basePath: String, rawPath: String): Pair<String, String>? {
    if (!rawPath.startsWith(basePath)) {
        return null
    }
    val relative = rawPath.substring(basePath.length)
    val slash = relative.indexOf('/')
    if (relative.isEmpty() || slash == 0) {
        return null
    }
    if (slash < 0) {
        return relative to basePath
    }
    return relative.substring(0, slash) to basePath + relative.substring(slash + 1)
}
