package org.hle.grpchttp1quarkusblocking.gateway

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.ClientInterceptor
import io.grpc.MethodDescriptor
import io.quarkus.arc.Arc
import io.quarkus.grpc.GlobalInterceptor
import jakarta.enterprise.inject.spi.Prioritized
import jakarta.inject.Singleton

// The slot channels carry this interceptor too, so a routed call must pass through on arrival.
private val ROUTED = CallOptions.Key.createWithDefault("org.hle.gateway.routed", false)

@GlobalInterceptor
@Singleton
class BackendRoutingInterceptor(
    private val backends: Backends,
    private val selection: BackendSelection,
) : ClientInterceptor, Prioritized {

    // Outermost, so a redirected call skips this channel's other interceptors and gets the slot's own once.
    override fun getPriority(): Int = Int.MAX_VALUE

    override fun <ReqT, RespT> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel,
    ): ClientCall<ReqT, RespT> {
        val name = selected()
        if (name == null || callOptions.getOption(ROUTED)) {
            return next.newCall(method, callOptions)
        }
        return backends.channel(name).newCall(method, callOptions.withOption(ROUTED, true))
    }

    private fun selected(): BackendName? {
        if (!Arc.container().requestContext().isActive) {
            return null
        }
        return selection.name
    }
}
