import tempfile
import os
from protoc_adapter.parser.cpp_parser import parse_cpp_header


def _write_temp_header(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".h")
    os.write(fd, content.encode())
    os.close(fd)
    return path


class TestSimpleStruct:
    def test_single_struct_with_char_arrays(self):
        """Real-world pattern: strings are char arrays, not std::string."""
        header = """\
#pragma once

struct OrderInfo {
    int orderId;
    char customerName[64];
    bool isActive;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            assert len(messages) == 1
            msg = messages[0]
            assert msg.original_name == "OrderInfo"
            assert msg.normalized_name == "ORDERINFO"
            assert len(msg.fields) == 3

            assert msg.fields[0].original_name == "orderId"
            assert msg.fields[0].type_name == "int"
            assert msg.fields[0].is_repeated is False

            assert msg.fields[1].original_name == "customerName"
            assert msg.fields[1].type_name == "char"
            assert msg.fields[1].is_repeated is False  # char[] is a string, NOT repeated

            assert msg.fields[2].original_name == "isActive"
            assert msg.fields[2].type_name == "bool"
        finally:
            os.unlink(path)

    def test_std_string_still_works(self):
        """Fallback: std::string should still be parsed."""
        header = """\
struct Foo {
    std::string name;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            assert len(messages) == 1
            assert messages[0].fields[0].type_name == "string"
            assert messages[0].fields[0].is_repeated is False
        finally:
            os.unlink(path)

    def test_multiple_structs(self):
        header = """\
struct Foo {
    int id;
};

struct Bar {
    double value;
    char name[128];
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            top_level = [m for m in messages if m.original_name in ("Foo", "Bar")]
            assert len(top_level) == 2
            bar = next(m for m in messages if m.original_name == "Bar")
            assert bar.fields[1].type_name == "char"
            assert bar.fields[1].is_repeated is False
        finally:
            os.unlink(path)


class TestArrayFields:
    def test_char_array_is_string_not_repeated(self):
        """char name[N] should be treated as a string field, NOT a repeated field."""
        header = """\
struct Person {
    char firstName[32];
    char lastName[32];
    int age;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            msg = messages[0]
            assert len(msg.fields) == 3
            assert msg.fields[0].type_name == "char"
            assert msg.fields[0].is_repeated is False
            assert msg.fields[1].type_name == "char"
            assert msg.fields[1].is_repeated is False
            assert msg.fields[2].type_name == "int"
        finally:
            os.unlink(path)

    def test_c_style_array_is_repeated(self):
        """Type name[N] (non-char) should be treated as repeated."""
        header = """\
struct Container {
    int scores[10];
    double values[20];
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            msg = messages[0]
            assert len(msg.fields) == 2
            assert msg.fields[0].type_name == "int"
            assert msg.fields[0].is_repeated is True
            assert msg.fields[1].type_name == "double"
            assert msg.fields[1].is_repeated is True
        finally:
            os.unlink(path)

    def test_array_of_nested_struct(self):
        """StructType items[N] should be treated as repeated nested."""
        header = """\
struct OrderList {
    struct OrderItem {
        int itemId;
        char itemName[64];
    };
    OrderItem items[50];
    char listName[128];
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            order_list = next(m for m in messages if m.original_name == "OrderList")
            items_field = next(f for f in order_list.fields if f.original_name == "items")
            assert items_field.is_repeated is True
            assert items_field.type_name == "OrderItem"
            assert items_field.is_nested is True

            list_name = next(f for f in order_list.fields if f.original_name == "listName")
            assert list_name.type_name == "char"
            assert list_name.is_repeated is False
        finally:
            os.unlink(path)


class TestVectorFields:
    def test_std_vector_still_works(self):
        """std::vector should still be supported as fallback."""
        header = """\
struct Container {
    std::vector<int> scores;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            assert messages[0].fields[0].is_repeated is True
            assert messages[0].fields[0].type_name == "int"
        finally:
            os.unlink(path)

    def test_vector_without_std_prefix(self):
        header = """\
struct Container {
    vector<int> numbers;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            msg_field = messages[0].fields[0]
            assert msg_field.is_repeated is True
            assert msg_field.type_name == "int"
        finally:
            os.unlink(path)


class TestNestedStructs:
    def test_nested_struct(self):
        header = """\
struct Outer {
    char name[64];
    struct Inner {
        int value;
    };
    Inner detail;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            outer = next(m for m in messages if m.original_name == "Outer")
            inner = next(m for m in messages if m.original_name == "Inner")

            detail_field = next(f for f in outer.fields if f.original_name == "detail")
            assert detail_field.type_name == "Inner"
            assert detail_field.is_nested is True
            assert detail_field.nested_type is inner
        finally:
            os.unlink(path)

    def test_vector_of_nested(self):
        header = """\
struct OrderList {
    struct OrderItem {
        int itemId;
        char itemName[64];
    };
    std::vector<OrderItem> items;
    char listName[128];
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            order_list = next(m for m in messages if m.original_name == "OrderList")
            items_field = next(f for f in order_list.fields if f.original_name == "items")
            assert items_field.is_repeated is True
            assert items_field.type_name == "OrderItem"
        finally:
            os.unlink(path)


class TestEdgeCases:
    def test_skips_comments_and_preprocessor(self):
        header = """\
#pragma once
#include <string>

// This is a comment
struct Test {
    // field comment
    int id;
    char name[64];
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            assert len(messages) == 1
            assert len(messages[0].fields) == 2
        finally:
            os.unlink(path)

    def test_struct_with_brace_on_next_line(self):
        header = """\
struct Test
{
    int id;
};
"""
        path = _write_temp_header(header)
        try:
            messages = parse_cpp_header(path)
            assert len(messages) == 1
            assert messages[0].original_name == "Test"
            assert len(messages[0].fields) == 1
        finally:
            os.unlink(path)
