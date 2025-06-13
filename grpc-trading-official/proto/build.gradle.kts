import com.google.protobuf.gradle.*

plugins {
    kotlin("jvm") version "1.9.25"
    id("com.google.protobuf") version "0.9.4"
}

group = "org.hle"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

val protobufVersion = "3.24.0"
val grpcVersion = "1.58.0"
val grpcKotlinVersion = "1.3.0"

dependencies {
    // Protobuf
    implementation("com.google.protobuf:protobuf-java:$protobufVersion")
    implementation("com.google.protobuf:protobuf-kotlin:$protobufVersion")

    // gRPC
    implementation("io.grpc:grpc-protobuf:$grpcVersion")
    implementation("io.grpc:grpc-stub:$grpcVersion")
    implementation("io.grpc:grpc-kotlin-stub:$grpcKotlinVersion")

    // Kotlin coroutines for gRPC Kotlin
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")

    // For Java 9+ compatibility
    implementation("javax.annotation:javax.annotation-api:1.3.2")

    testImplementation(kotlin("test"))
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:$protobufVersion"
    }
    plugins {
        id("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:$grpcVersion"
        }
        id("grpckt") {
            artifact = "io.grpc:protoc-gen-grpc-kotlin:$grpcKotlinVersion:jdk8@jar"
        }
    }
    generateProtoTasks {
        all().forEach {
            it.plugins {
                id("grpc")
                id("grpckt")
            }
            it.builtins {
                id("kotlin")
            }
        }
    }
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(21)
}
