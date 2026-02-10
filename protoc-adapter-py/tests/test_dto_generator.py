from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize
from protoc_adapter.generator.java_dto_generator import generate_dto


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


def _make_match(proto_name, cpp_name, field_pairs) -> MessageMatch:
    """Create a MessageMatch from (proto_field, cpp_field) pairs."""
    proto_msg = Message(proto_name, normalize(proto_name), [], "test.proto")
    cpp_msg = Message(cpp_name, normalize(cpp_name), [], "test.h")
    mappings = [FieldMapping(proto_field=pf, cpp_field=cf) for pf, cf in field_pairs]
    return MessageMatch(proto_message=proto_msg, cpp_message=cpp_msg, field_mappings=mappings)


class TestSimpleDto:
    def test_primitive_fields(self):
        match = _make_match("OrderInfo", "OrderInfo", [
            (_make_field("order_id", "int32"), _make_field("orderId", "int")),
            (_make_field("customer_name", "string"), _make_field("customerName", "string")),
            (_make_field("is_active", "bool"), _make_field("isActive", "bool")),
        ])

        result = generate_dto(match, "com.example")

        assert "package com.example.dto;" in result
        assert "@Getter" in result
        assert "@Setter" in result
        assert "@Builder" in result
        assert "public class OrderInfo {" in result
        assert "private Integer orderId;" in result
        assert "private String customerName;" in result
        assert "private Boolean isActive;" in result
        # Should NOT have List import
        assert "import java.util.List;" not in result
        # Should NOT have NoArgsConstructor or AllArgsConstructor
        assert "NoArgsConstructor" not in result
        assert "AllArgsConstructor" not in result


class TestListDto:
    def test_repeated_field(self):
        match = _make_match("Container", "Container", [
            (
                _make_field("tags", "string", is_repeated=True),
                _make_field("tags", "string", is_repeated=True),
            ),
        ])

        result = generate_dto(match, "com.example")

        assert "import java.util.List;" in result
        assert "private List<String> tags;" in result


class TestNestedDto:
    def test_nested_type_uses_cpp_name(self):
        inner_cpp = Message("InnerDetail", normalize("InnerDetail"), [], "test.h")
        match = _make_match("Outer", "Outer", [
            (_make_field("name", "string"), _make_field("name", "string")),
            (
                _make_field("detail", "Inner", is_nested=True),
                _make_field("detail", "InnerDetail", is_nested=True, nested_type=inner_cpp),
            ),
        ])

        result = generate_dto(match, "com.example")

        assert "private InnerDetail detail;" in result

    def test_repeated_nested(self):
        item_cpp = Message("OrderItem", normalize("OrderItem"), [], "test.h")
        match = _make_match("OrderList", "OrderList", [
            (
                _make_field("items", "OrderItem", is_repeated=True, is_nested=True),
                _make_field("items", "OrderItem", is_repeated=True, is_nested=True, nested_type=item_cpp),
            ),
        ])

        result = generate_dto(match, "com.example")

        assert "import java.util.List;" in result
        assert "private List<OrderItem> items;" in result
