package org.hle.grpchttp1vs.gateway

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.MethodDescriptor
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Component
import org.springframework.web.context.request.RequestContextHolder
import org.springframework.web.context.request.ServletRequestAttributes

@Primary
@Component
class RoutingChannel(private val backends: Backends) : Channel() {
    override fun <ReqT, RespT> newCall(
        methodDescriptor: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
    ): ClientCall<ReqT, RespT> = backends.channel(current()).newCall(methodDescriptor, callOptions)

    override fun authority(): String = backends.channel(current()).authority()

    internal fun selectedName(): String = backends.label(current())

    private fun current(): BackendName? {
        val request = (RequestContextHolder.getRequestAttributes() as? ServletRequestAttributes)?.request
            ?: return null
        return request.getAttribute(BACKEND_REQUEST_ATTRIBUTE) as? BackendName
    }
}
