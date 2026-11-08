package org.hle.grpchttp1vs.gateway

import jakarta.servlet.DispatcherType
import jakarta.servlet.Filter
import jakarta.servlet.FilterChain
import jakarta.servlet.ServletRequest
import jakarta.servlet.ServletResponse
import jakarta.servlet.http.HttpServletRequest
import org.springframework.boot.servlet.filter.OrderedFilter
import org.springframework.boot.web.servlet.FilterRegistrationBean
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

class BackendPrefixFilter(private val backends: Backends) : Filter {
    override fun doFilter(request: ServletRequest, response: ServletResponse, chain: FilterChain) {
        val http = request as HttpServletRequest
        // A forward enters this filter again and would treat the next segment as another backend.
        if (http.getAttribute(BACKEND_REQUEST_ATTRIBUTE) != null) {
            chain.doFilter(request, response)
            return
        }
        val split = splitPrefix(applicationPath(http))
        val name = split?.let { (segment, _) -> backends.configuredName(segment) }
        if (split == null || name == null) {
            chain.doFilter(request, response)
            return
        }
        http.setAttribute(BACKEND_REQUEST_ATTRIBUTE, name)
        val target = withQuery(split.second, http.queryString)
        http.getRequestDispatcher(target).forward(request, response)
    }
}

@Configuration
class BackendPrefixFilterRegistration {
    @Bean
    fun backendPrefixFilter(backends: Backends): FilterRegistrationBean<BackendPrefixFilter> {
        val registration = FilterRegistrationBean(BackendPrefixFilter(backends))
        registration.setDispatcherTypes(DispatcherType.REQUEST, DispatcherType.FORWARD)
        // OrderedRequestContextFilter sits at MAX - 105. Stay inside it so the forward keeps the request bound.
        registration.order = OrderedFilter.REQUEST_WRAPPER_FILTER_MAX_ORDER - 104
        return registration
    }
}

private fun applicationPath(request: HttpServletRequest): String {
    val context = request.contextPath
    val uri = request.requestURI
    if (context.isNotEmpty() && uri.startsWith(context)) {
        return uri.substring(context.length)
    }
    return uri
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

private fun withQuery(path: String, query: String?): String {
    if (query.isNullOrEmpty()) {
        return path
    }
    return "$path?$query"
}
