from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize
from protoc_adapter.generator.java_mapper_generator import generate_mapper


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


class TestPrimitiveMapper:
    def test_simple_primitive_fields(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
                (_make_field("customer_name", "string"), _make_field("customerName", "string")),
            ])
        ]

        result = generate_mapper(matches, "order_service.proto", "com.example")

        assert "package com.example.mapper;" in result
        assert "public class OrderServiceMapper {" in result
        assert "public static OrderInfo proto2Dto(OrderServiceProto.OrderInfo proto)" in result
        assert ".orderId(proto.getOrderId())" in result
        assert ".customerName(proto.getCustomerName())" in result
        assert ".build();" in result


class TestNestedMapper:
    def test_nested_field_calls_proto2dto(self):
        inner_cpp = Message("InnerDetail", normalize("InnerDetail"), [], "test.h")
        matches = [
            _make_match("Outer", "Outer", [
                (_make_field("name", "string"), _make_field("name", "string")),
                (
                    _make_field("detail", "Inner", is_nested=True),
                    _make_field("detail", "InnerDetail", is_nested=True, nested_type=inner_cpp),
                ),
            ])
        ]

        result = generate_mapper(matches, "my_service.proto", "com.example")

        assert ".detail(proto2Dto(proto.getDetail()))" in result


class TestRepeatedMapper:
    def test_repeated_primitive(self):
        matches = [
            _make_match("Container", "Container", [
                (
                    _make_field("tags", "string", is_repeated=True),
                    _make_field("tags", "string", is_repeated=True),
                ),
            ])
        ]

        result = generate_mapper(matches, "data.proto", "com.example")

        assert ".tags(proto.getTagsList())" in result
        # Should NOT have Collectors import for non-nested repeated
        assert "Collectors" not in result

    def test_repeated_nested(self):
        item_cpp = Message("OrderItem", normalize("OrderItem"), [], "test.h")
        matches = [
            _make_match("OrderList", "OrderList", [
                (
                    _make_field("items", "OrderItem", is_repeated=True, is_nested=True),
                    _make_field("items", "OrderItem", is_repeated=True, is_nested=True, nested_type=item_cpp),
                ),
            ])
        ]

        result = generate_mapper(matches, "order_service.proto", "com.example")

        assert "import java.util.stream.Collectors;" in result
        assert ".items(proto.getItemsList().stream()" in result
        assert ".map(OrderServiceMapper::proto2Dto)" in result
        assert ".collect(Collectors.toList()))" in result


class TestMultipleMethods:
    def test_multiple_matches_produce_overloaded_methods(self):
        matches = [
            _make_match("OrderInfo", "OrderInfo", [
                (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            ]),
            _make_match("OrderItem", "OrderItem", [
                (_make_field("item_id", "int32"), _make_field("itemId", "int")),
            ]),
        ]

        result = generate_mapper(matches, "order_service.proto", "com.example")

        # Should have two proto2Dto methods (overloaded)
        assert result.count("public static") == 2
        assert "proto2Dto(OrderServiceProto.OrderInfo proto)" in result
        assert "proto2Dto(OrderServiceProto.OrderItem proto)" in result


class TestMapperClassName:
    def test_snake_case_file_name(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]

        result = generate_mapper(matches, "my_cool_service.proto", "com.example")

        assert "public class MyCoolServiceMapper {" in result

    def test_simple_file_name(self):
        matches = [
            _make_match("Foo", "Foo", [
                (_make_field("id", "int32"), _make_field("id", "int")),
            ])
        ]

        result = generate_mapper(matches, "Orders.proto", "com.example")

        assert "public class OrdersMapper {" in result
