import tempfile
import os
from protoc_adapter.parser.proto_parser import parse_proto_file


def _write_temp_proto(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".proto")
    os.write(fd, content.encode())
    os.close(fd)
    return path


class TestSimpleMessage:
    def test_single_message_with_primitives(self):
        proto = """\
syntax = "proto3";

message OrderInfo {
    int32 order_id = 1;
    string customer_name = 2;
    bool is_active = 3;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            assert len(messages) == 1
            msg = messages[0]
            assert msg.original_name == "OrderInfo"
            assert msg.normalized_name == "ORDERINFO"
            assert len(msg.fields) == 3

            assert msg.fields[0].original_name == "order_id"
            assert msg.fields[0].normalized_name == "ORDERID"
            assert msg.fields[0].type_name == "int32"
            assert msg.fields[0].is_repeated is False

            assert msg.fields[1].original_name == "customer_name"
            assert msg.fields[1].type_name == "string"

            assert msg.fields[2].original_name == "is_active"
            assert msg.fields[2].type_name == "bool"
        finally:
            os.unlink(path)

    def test_multiple_messages(self):
        proto = """\
syntax = "proto3";

message Foo {
    int32 id = 1;
}

message Bar {
    string name = 1;
    double value = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            top_level = [m for m in messages if m.original_name in ("Foo", "Bar")]
            assert len(top_level) == 2
            assert top_level[0].original_name == "Foo"
            assert top_level[1].original_name == "Bar"
            assert len(top_level[1].fields) == 2
        finally:
            os.unlink(path)


class TestRepeatedFields:
    def test_repeated_field(self):
        proto = """\
syntax = "proto3";

message Container {
    repeated string tags = 1;
    repeated int32 scores = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            assert len(messages) == 1
            msg = messages[0]
            assert len(msg.fields) == 2
            assert msg.fields[0].is_repeated is True
            assert msg.fields[0].type_name == "string"
            assert msg.fields[1].is_repeated is True
            assert msg.fields[1].type_name == "int32"
        finally:
            os.unlink(path)


class TestNestedMessages:
    def test_nested_message(self):
        proto = """\
syntax = "proto3";

message Outer {
    string name = 1;
    message Inner {
        int32 value = 1;
    }
    Inner detail = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            # Should have Outer and Inner
            outer = next(m for m in messages if m.original_name == "Outer")
            inner = next(m for m in messages if m.original_name == "Inner")

            assert len(outer.fields) == 2
            detail_field = next(f for f in outer.fields if f.original_name == "detail")
            assert detail_field.type_name == "Inner"
            assert detail_field.is_nested is True
            assert detail_field.nested_type is inner

            assert len(inner.fields) == 1
            assert inner.fields[0].original_name == "value"
        finally:
            os.unlink(path)

    def test_repeated_nested(self):
        proto = """\
syntax = "proto3";

message OrderList {
    message OrderItem {
        int32 item_id = 1;
        string item_name = 2;
    }
    repeated OrderItem items = 1;
    string list_name = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            order_list = next(m for m in messages if m.original_name == "OrderList")
            items_field = next(f for f in order_list.fields if f.original_name == "items")
            assert items_field.is_repeated is True
            assert items_field.is_nested is True
            assert items_field.nested_type.original_name == "OrderItem"
        finally:
            os.unlink(path)


class TestEdgeCases:
    def test_skips_comments_and_options(self):
        proto = """\
syntax = "proto3";

option java_package = "com.example";

// This is a comment
message Test {
    // another comment
    int32 id = 1;
    option deprecated = true;
    string name = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            assert len(messages) == 1
            assert len(messages[0].fields) == 2
        finally:
            os.unlink(path)

    def test_empty_message(self):
        proto = """\
syntax = "proto3";

message Empty {
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            assert len(messages) == 1
            assert len(messages[0].fields) == 0
        finally:
            os.unlink(path)


class TestNonPrimitiveFields:
    def test_external_message_reference_is_nested(self):
        """A field referencing a top-level message (not nested definition) has is_nested=True."""
        proto = """\
syntax = "proto3";

message Inner {
    int32 value = 1;
}

message Outer {
    string name = 1;
    Inner detail = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            outer = next(m for m in messages if m.original_name == "Outer")
            detail = next(f for f in outer.fields if f.original_name == "detail")
            assert detail.is_nested is True
            # nested_type is None because Inner is defined at top level, not inside Outer
            assert detail.nested_type is None
        finally:
            os.unlink(path)

    def test_primitive_fields_not_nested(self):
        """Primitive-typed fields must have is_nested=False."""
        proto = """\
syntax = "proto3";

message Simple {
    int32 id = 1;
    string name = 2;
    bool active = 3;
    double score = 4;
    int64 timestamp = 5;
    float ratio = 6;
    bytes data = 7;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            msg = messages[0]
            for field in msg.fields:
                assert field.is_nested is False, (
                    f"Primitive field '{field.original_name}' (type={field.type_name}) "
                    f"should not be nested"
                )
        finally:
            os.unlink(path)

    def test_nested_definition_field_still_linked(self):
        """A field referencing a nested message definition has is_nested=True and nested_type set."""
        proto = """\
syntax = "proto3";

message Outer {
    string name = 1;
    message Inner {
        int32 value = 1;
    }
    Inner detail = 2;
}
"""
        path = _write_temp_proto(proto)
        try:
            messages = parse_proto_file(path)
            outer = next(m for m in messages if m.original_name == "Outer")
            inner = next(m for m in messages if m.original_name == "Inner")
            detail = next(f for f in outer.fields if f.original_name == "detail")
            assert detail.is_nested is True
            assert detail.nested_type is inner
        finally:
            os.unlink(path)
