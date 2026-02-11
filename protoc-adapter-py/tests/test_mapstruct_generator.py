from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize
from protoc_adapter.generator.java_mapstruct_generator import (
    generate_mapstruct_mapper,
    generate_naming_strategy,
    generate_maven_integration_doc,
)


def _make_field(name: str, type_name: str, is_repeated: bool = False,
                is_nested: bool = False, nested_type=None) -> Field:
    return Field(
        original_name=name,
        normalized_name=normalize(name),
        type_name=type_name,
        is_repeated=is_repeated,
        is_nested=is_nested,
        nested_type=nested_type,
    )


def _make_match(proto_name, cpp_name, field_pairs, source="test.proto") -> MessageMatch:
    proto_msg = Message(proto_name, normalize(proto_name), [], source)
    cpp_msg = Message(cpp_name, normalize(cpp_name), [], "test.h")
    mappings = [FieldMapping(proto_field=pf, cpp_field=cf) for pf, cf in field_pairs]
    return MessageMatch(proto_message=proto_msg, cpp_message=cpp_msg, field_mappings=mappings)


class TestMapStructInterface:
    def test_generates_interface_not_class(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "public interface OrderServiceMapStructMapper {" in result
        assert "public class" not in result

    def test_has_mapper_annotation(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "@Mapper" in result
        assert "import org.mapstruct.Mapper;" in result

    def test_has_instance_field(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert (
            "OrderServiceMapStructMapper INSTANCE = "
            "Mappers.getMapper(OrderServiceMapStructMapper.class);"
        ) in result
        assert "import org.mapstruct.factory.Mappers;" in result

    def test_no_mapping_annotations(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
                (_make_field("customer_name", "string"), _make_field("customerName", "string")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "@Mapping" not in result

    def test_package_name(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "test.proto", "com.example")

        assert "package com.example.mapstruct_mapper;" in result

    def test_imports_dto_package(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "test.proto", "com.acme.trade")

        assert "import com.acme.trade.dto.*;" in result


class TestMapStructMethodSignatures:
    def test_method_signature_uses_toDto(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "OrderInfo toDto(OrderServiceProto.OrderInfo proto);" in result

    def test_multiple_matches_produce_multiple_toDto_methods(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ]),
            _make_match("OrderItem", "OrderItem", [
                (_make_field("item_id", "int32"), _make_field("itemId", "int")),
            ]),
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "OrderInfo toDto(OrderServiceProto.OrderInfo proto);" in result
        assert "OrderItem toDto(OrderServiceProto.OrderItem proto);" in result


class TestMapStructClassName:
    def test_snake_case_file_name(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "my_cool_service.proto", "com.example")

        assert "public interface MyCoolServiceMapStructMapper {" in result

    def test_simple_file_name(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "Orders.proto", "com.example")

        assert "public interface OrdersMapStructMapper {" in result


class TestMapStructReplyHeader:
    def test_reply_header_generates_default_method(self):
        from protoc_adapter.rep_message_handler import WEB_SERVICE_REPLY_HEADER_CLASS

        msg_header_def = Message("msgHeader", normalize("msgHeader"), [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
        ], "rep_service.proto")

        header_field = _make_field(
            "msg_header", "msgHeader", is_nested=True, nested_type=msg_header_def
        )

        synthetic_cpp_field = _make_field(
            "msgHeader", WEB_SERVICE_REPLY_HEADER_CLASS, is_nested=True
        )

        proto_msg = Message("RepOrderInfo", normalize("RepOrderInfo"), [], "rep_service.proto")
        cpp_msg = Message("RepOrderInfo", normalize("RepOrderInfo"), [], "test.h")

        mappings = [
            FieldMapping(
                proto_field=header_field,
                cpp_field=synthetic_cpp_field,
                is_reply_header=True,
            ),
            FieldMapping(
                proto_field=_make_field("order_id", "int32"),
                cpp_field=_make_field("orderId", "int"),
            ),
        ]
        match = MessageMatch(
            proto_message=proto_msg, cpp_message=cpp_msg, field_mappings=mappings
        )

        result = generate_mapstruct_mapper([match], "rep_service.proto", "com.example")

        assert "default WebServiceReplyHeader toDto(" in result
        assert "RepServiceProto.msgHeader proto)" in result
        assert ".returnCode(proto.getRetCode())" in result
        assert ".returnMessage(proto.getMsgOwnId())" in result
        assert "WebServiceReplyHeader.builder()" in result

    def test_non_reply_header_has_no_default_method(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ])
        ]
        result = generate_mapstruct_mapper(matches, "order_service.proto", "com.example")

        assert "default" not in result
        assert "WebServiceReplyHeader" not in result


class TestNamingStrategy:
    def test_generates_naming_strategy_file(self, tmp_path):
        files = generate_naming_strategy("com.example", str(tmp_path))

        assert len(files) == 2

        spi_file = tmp_path / "mapstruct_mapper" / "spi" / "ProtobufAccessorNamingStrategy.java"
        assert spi_file.exists()

        content = spi_file.read_text()
        assert "package com.example.mapstruct_mapper.spi;" in content
        assert "class ProtobufAccessorNamingStrategy extends DefaultAccessorNamingStrategy" in content
        assert "isGetterMethod" in content
        assert "getPropertyName" in content

    def test_naming_strategy_has_normalization(self, tmp_path):
        generate_naming_strategy("com.example", str(tmp_path))

        spi_file = tmp_path / "mapstruct_mapper" / "spi" / "ProtobufAccessorNamingStrategy.java"
        content = spi_file.read_text()

        # Must normalize property names for casing mismatch resolution
        assert '.replace("_", "").toLowerCase()' in content

    def test_naming_strategy_has_list_stripping(self, tmp_path):
        generate_naming_strategy("com.example", str(tmp_path))

        spi_file = tmp_path / "mapstruct_mapper" / "spi" / "ProtobufAccessorNamingStrategy.java"
        content = spi_file.read_text()

        assert 'endsWith("List")' in content
        assert "isListType" in content

    def test_naming_strategy_has_proto_method_filtering(self, tmp_path):
        generate_naming_strategy("com.example", str(tmp_path))

        spi_file = tmp_path / "mapstruct_mapper" / "spi" / "ProtobufAccessorNamingStrategy.java"
        content = spi_file.read_text()

        assert "OrBuilder" in content
        assert "Bytes" in content
        assert "getAllFields" in content

    def test_generates_spi_service_file(self, tmp_path):
        files = generate_naming_strategy("com.example", str(tmp_path))

        service_file = (
            tmp_path / "mapstruct_mapper" / "META-INF" / "services"
            / "org.mapstruct.ap.spi.AccessorNamingStrategy"
        )
        assert service_file.exists()

        content = service_file.read_text()
        assert "com.example.mapstruct_mapper.spi.ProtobufAccessorNamingStrategy" in content

    def test_naming_strategy_package_varies(self, tmp_path):
        generate_naming_strategy("com.acme.trade", str(tmp_path))

        spi_file = tmp_path / "mapstruct_mapper" / "spi" / "ProtobufAccessorNamingStrategy.java"
        content = spi_file.read_text()
        assert "package com.acme.trade.mapstruct_mapper.spi;" in content

        service_file = (
            tmp_path / "mapstruct_mapper" / "META-INF" / "services"
            / "org.mapstruct.ap.spi.AccessorNamingStrategy"
        )
        content = service_file.read_text()
        assert "com.acme.trade.mapstruct_mapper.spi.ProtobufAccessorNamingStrategy" in content


class TestMavenIntegrationDoc:
    def _make_matches_by_proto(self):
        """Build a minimal matches_by_proto dict for template rendering."""
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ], source="order_service.proto")
        ]
        return {"order_service.proto": matches}

    def test_generates_doc_file(self, tmp_path):
        matches_by_proto = self._make_matches_by_proto()
        file_path = generate_maven_integration_doc(matches_by_proto, "com.example", str(tmp_path))

        assert file_path.endswith("MAVEN_INTEGRATION.md")
        assert (tmp_path / "mapstruct_mapper" / "MAVEN_INTEGRATION.md").exists()

    def test_doc_contains_package_specific_info(self, tmp_path):
        matches_by_proto = self._make_matches_by_proto()
        generate_maven_integration_doc(matches_by_proto, "com.acme.trade", str(tmp_path))

        doc_file = tmp_path / "mapstruct_mapper" / "MAVEN_INTEGRATION.md"
        content = doc_file.read_text()

        assert "com.acme.trade" in content
        assert "com/acme/trade" in content
        assert "mapstruct" in content.lower()
        assert "lombok" in content.lower()

    def test_doc_uses_actual_class_names(self, tmp_path):
        matches_by_proto = self._make_matches_by_proto()
        generate_maven_integration_doc(matches_by_proto, "com.example", str(tmp_path))

        doc_file = tmp_path / "mapstruct_mapper" / "MAVEN_INTEGRATION.md"
        content = doc_file.read_text()

        assert "OrderServiceMapStructMapper" in content
        assert "OrderInfo" in content
