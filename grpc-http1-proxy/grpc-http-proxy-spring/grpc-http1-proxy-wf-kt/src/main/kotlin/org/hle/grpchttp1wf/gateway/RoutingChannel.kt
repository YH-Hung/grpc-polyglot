package org.hle.grpchttp1wf.gateway

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.MethodDescriptor
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Component

@Primary
@Component
class RoutingChannel(private val backends: Backends) : Channel() {
    override fun <ReqT, RespT> newCall(
        methodDescriptor: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
    ): ClientCall<ReqT, RespT> = backends.channel(currentBackend.get()).newCall(methodDescriptor, callOptions)

    override fun authority(): String = backends.channel(currentBackend.get()).authority()

    internal fun selectedName(): String = backends.label(currentBackend.get())
}
