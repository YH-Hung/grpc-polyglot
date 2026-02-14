package org.hle.grpchttp1quarkusblocking.interceptor

import io.grpc.CallOptions
import io.grpc.Channel
import io.grpc.ClientCall
import io.grpc.ClientInterceptor
import io.grpc.ForwardingClientCall.SimpleForwardingClientCall
import io.grpc.Metadata
import io.grpc.MethodDescriptor
import io.quarkus.grpc.GlobalInterceptor
import jakarta.enterprise.context.ApplicationScoped

@GlobalInterceptor
@ApplicationScoped
class SpecialMsgInterceptor : ClientInterceptor {

    override fun <ReqT, RespT> interceptCall(
        method: MethodDescriptor<ReqT, RespT>,
        callOptions: CallOptions,
        next: Channel,
    ): ClientCall<ReqT, RespT> {
        return object : SimpleForwardingClientCall<ReqT, RespT>(next.newCall(method, callOptions)) {
            override fun start(responseListener: Listener<RespT>, headers: Metadata) {
                headers.put(
                    Metadata.Key.of("special_msg", Metadata.ASCII_STRING_MARSHALLER),
                    "greetings-from-girl-java-client"
                )
                super.start(responseListener, headers)
            }
        }
    }
}
