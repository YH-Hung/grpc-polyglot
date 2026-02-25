package org.hle.grpchttp1quarkusblocking.provider

import com.google.protobuf.Message
import com.google.protobuf.util.JsonFormat
import jakarta.ws.rs.Consumes
import jakarta.ws.rs.Produces
import jakarta.ws.rs.core.MediaType
import jakarta.ws.rs.core.MultivaluedMap
import jakarta.ws.rs.ext.MessageBodyReader
import jakarta.ws.rs.ext.MessageBodyWriter
import jakarta.ws.rs.ext.Provider
import java.io.InputStream
import java.io.OutputStream
import java.lang.reflect.Type

@Provider
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
class ProtobufJsonProvider : MessageBodyReader<Message>, MessageBodyWriter<Message> {

    private val parser = JsonFormat.parser().ignoringUnknownFields()
    private val printer = JsonFormat.printer().omittingInsignificantWhitespace()

    override fun isReadable(
        type: Class<*>,
        genericType: Type,
        annotations: Array<Annotation>,
        mediaType: MediaType,
    ): Boolean = Message::class.java.isAssignableFrom(type)

    override fun readFrom(
        type: Class<Message>,
        genericType: Type,
        annotations: Array<Annotation>,
        mediaType: MediaType,
        httpHeaders: MultivaluedMap<String, String>,
        entityStream: InputStream,
    ): Message {
        val json = entityStream.bufferedReader().readText()
        val builder = type.getMethod("newBuilder").invoke(null) as Message.Builder
        parser.merge(json, builder)
        return builder.build()
    }

    override fun isWriteable(
        type: Class<*>,
        genericType: Type,
        annotations: Array<Annotation>,
        mediaType: MediaType,
    ): Boolean = Message::class.java.isAssignableFrom(type)

    override fun writeTo(
        message: Message,
        type: Class<*>,
        genericType: Type,
        annotations: Array<Annotation>,
        mediaType: MediaType,
        httpHeaders: MultivaluedMap<String, Any>,
        entityStream: OutputStream,
    ) {
        entityStream.write(printer.print(message).toByteArray())
    }
}
