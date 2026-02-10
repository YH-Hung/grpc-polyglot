import os
import re
import shutil
import tempfile

from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize
from protoc_adapter.generator.java_dto_generator import generate_dto, generate_dtos
from protoc_adapter.main import run


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


# --- One-Class-Per-File Test Cases ---

ONE_CLASS_PROTO = """\
syntax = "proto3";
package test;

message ExecutionReport {
    int32 id = 1;
    string venue = 2;
}

message TradeOrder {
    int32 order_id = 1;
    string instrument_code = 2;
    TradeExecution execution = 3;

    message TradeExecution {
        int64 execution_id = 1;
        double fill_price = 2;
    }

    repeated TradeFee fees = 4;

    message TradeFee {
        string fee_type = 1;
        double amount = 2;
    }

    ExecutionReport report = 5;
}
"""

ONE_CLASS_CPP = """\
#pragma once

struct ExecutionReport {
    int id;
    char venue[64];
};

struct TradeExecution {
    long executionId;
    double fillPrice;
};

struct TradeFee {
    char feeType[32];
    double amount;
};

struct TradeOrder {
    int orderId;
    char instrumentCode[32];
    TradeExecution execution;
    TradeFee fees[20];
    ExecutionReport report;
};
"""

JAVA_PRIMITIVES = {"Integer", "Long", "Float", "Double", "Boolean", "String", "byte[]"}


class TestOneClassPerFile:
    def setup_method(self):
        self.work_dir = tempfile.mkdtemp()
        proto_path = os.path.join(self.work_dir, "test_service.proto")
        with open(proto_path, "w") as f:
            f.write(ONE_CLASS_PROTO)
        header_path = os.path.join(self.work_dir, "test_types.h")
        with open(header_path, "w") as f:
            f.write(ONE_CLASS_CPP)
        run(self.work_dir, "com.test")
        self.dto_dir = os.path.join(self.work_dir, "dto")

    def teardown_method(self):
        shutil.rmtree(self.work_dir)

    def test_each_file_has_exactly_one_public_class(self):
        """Each generated .java file must contain exactly one 'public class' declaration."""
        dto_files = [f for f in os.listdir(self.dto_dir) if f.endswith(".java")]
        assert len(dto_files) > 0, "No DTO files generated"

        for fname in dto_files:
            content = open(os.path.join(self.dto_dir, fname)).read()
            count = len(re.findall(r"\bpublic\s+class\s+", content))
            assert count == 1, (
                f"{fname} contains {count} 'public class' declarations, expected 1"
            )

    def test_no_inner_class_definitions(self):
        """No generated DTO file should contain inner/nested class definitions."""
        dto_files = [f for f in os.listdir(self.dto_dir) if f.endswith(".java")]
        for fname in dto_files:
            content = open(os.path.join(self.dto_dir, fname)).read()
            # After the first "public class ... {", there should be no more class defs
            lines = content.split("\n")
            found_outer = False
            for line in lines:
                stripped = line.strip()
                if re.match(r"^public\s+class\s+", stripped):
                    found_outer = True
                    continue
                if found_outer:
                    assert not re.match(r"^(public\s+|private\s+|protected\s+|static\s+)*class\s+", stripped), (
                        f"{fname} contains an inner class definition: {stripped}"
                    )

    def test_file_count_matches_matched_messages(self):
        """Number of generated DTO files must equal number of matched structs."""
        dto_files = [f for f in os.listdir(self.dto_dir) if f.endswith(".java")]
        # 4 matched structs: ExecutionReport, TradeOrder, TradeExecution, TradeFee
        assert len(dto_files) == 4, (
            f"Expected 4 DTO files, got {len(dto_files)}: {dto_files}"
        )

    def test_file_name_matches_class_name(self):
        """File stem must match the class name inside the file."""
        dto_files = [f for f in os.listdir(self.dto_dir) if f.endswith(".java")]
        for fname in dto_files:
            stem = fname.replace(".java", "")
            content = open(os.path.join(self.dto_dir, fname)).read()
            assert f"public class {stem} {{" in content, (
                f"File {fname} does not contain 'public class {stem}'"
            )

    def test_nested_messages_produce_separate_files(self):
        """Nested proto message definitions (TradeExecution, TradeFee) get their own files."""
        dto_files = os.listdir(self.dto_dir)
        assert "TradeExecution.java" in dto_files
        assert "TradeFee.java" in dto_files
        assert "TradeOrder.java" in dto_files

        # TradeOrder.java must NOT contain TradeExecution or TradeFee class defs
        trade_order = open(os.path.join(self.dto_dir, "TradeOrder.java")).read()
        assert "class TradeExecution" not in trade_order
        assert "class TradeFee" not in trade_order

    def test_all_non_primitive_field_types_have_own_files(self):
        """Every non-primitive field type referenced in a DTO must have its own .java file."""
        dto_files = [f for f in os.listdir(self.dto_dir) if f.endswith(".java")]
        available_types = {f.replace(".java", "") for f in dto_files}

        for fname in dto_files:
            content = open(os.path.join(self.dto_dir, fname)).read()
            # Find all field declarations: private <Type> <name>;
            fields = re.findall(r"private\s+([\w<>]+)\s+\w+;", content)
            for java_type in fields:
                # Extract base type (handle List<Type>)
                list_match = re.match(r"List<(\w+)>", java_type)
                base_type = list_match.group(1) if list_match else java_type
                if base_type not in JAVA_PRIMITIVES:
                    assert base_type in available_types, (
                        f"{fname} references type '{base_type}' but no "
                        f"{base_type}.java exists. Available: {available_types}"
                    )

    def test_cross_message_references_produce_separate_files(self):
        """Top-level ExecutionReport referenced from TradeOrder gets its own file."""
        dto_files = os.listdir(self.dto_dir)
        assert "ExecutionReport.java" in dto_files
        assert "TradeOrder.java" in dto_files

        trade_order = open(os.path.join(self.dto_dir, "TradeOrder.java")).read()
        assert "private ExecutionReport report;" in trade_order
