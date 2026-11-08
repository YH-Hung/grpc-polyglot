package org.hle.grpchttp1quarkusblocking.gateway

import io.smallrye.common.annotation.RunOnVirtualThread
import jakarta.ws.rs.POST
import jakarta.ws.rs.Path
import jakarta.ws.rs.Produces
import jakarta.ws.rs.core.MediaType

@Path("/probe")
class ProbeResource(private val selection: BackendSelection) {
    @POST
    @Path("/who")
    @Produces(MediaType.TEXT_PLAIN)
    @RunOnVirtualThread
    fun who(): String = selection.label()
}
