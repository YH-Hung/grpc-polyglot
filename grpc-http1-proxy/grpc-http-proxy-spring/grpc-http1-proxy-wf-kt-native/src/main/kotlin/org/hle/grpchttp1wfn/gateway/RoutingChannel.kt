package org.hle.grpchttp1wfn.gateway

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.MethodDescriptor
import kotlinx.coroutines.asContextElement
import org.springframework.context.annotation.Primary
import org.springframework.stereotype.Component
import kotlin.coroutines.CoroutineContext

private val currentBackend = ThreadLocal<BackendName?>()

// grpc-kotlin calls newCall from inside the caller's coroutine, so the element re-binds the name on every resume.
internal fun backendContext(name: BackendName): CoroutineContext.Element = currentBackend.asContextElement(name)

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
