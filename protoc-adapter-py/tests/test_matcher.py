import pytest
from protoc_adapter.models import Field, Message, normalize
from protoc_adapter.matcher import match_messages, MatchError


def _make_proto_msg(name: str, fields: list) -> Message:
    return Message(
        original_name=name,
        normalized_name=normalize(name),
        fields=fields,
        source_file="test.proto",
    )


def _make_cpp_msg(name: str, fields: list) -> Message:
    return Message(
        original_name=name,
        normalized_name=normalize(name),
        fields=fields,
        source_file="test.h",
    )


def _make_field(name: str, type_name: str = "int32", is_repeated: bool = False,
                is_nested: bool = False, nested_type: Message = None) -> Field:
    return Field(
        original_name=name,
        normalized_name=normalize(name),
        type_name=type_name,
        is_repeated=is_repeated,
        is_nested=is_nested,
        nested_type=nested_type,
    )


class TestSuccessfulMatch:
    def test_simple_match(self):
        proto_msgs = [
            _make_proto_msg("OrderInfo", [
                _make_field("order_id", "int32"),
                _make_field("customer_name", "string"),
            ])
        ]
        cpp_msgs = [
            _make_cpp_msg("OrderInfo", [
                _make_field("orderId", "int"),
                _make_field("customerName", "string"),
            ])
        ]

        matches = match_messages(proto_msgs, cpp_msgs)
        assert len(matches) == 1
        assert matches[0].proto_message.original_name == "OrderInfo"
        assert matches[0].cpp_message.original_name == "OrderInfo"
        assert len(matches[0].field_mappings) == 2

        # Verify field mapping
        assert matches[0].field_mappings[0].proto_field.original_name == "order_id"
        assert matches[0].field_mappings[0].cpp_field.original_name == "orderId"

    def test_different_casing_match(self):
        """Proto uses snake_case, C++ uses camelCase — should match via normalization."""
        proto_msgs = [
            _make_proto_msg("mask_group", [
                _make_field("mask_group_id", "int32"),
            ])
        ]
        cpp_msgs = [
            _make_cpp_msg("MaskGroup", [
                _make_field("maskGroupId", "int"),
            ])
        ]

        matches = match_messages(proto_msgs, cpp_msgs)
        assert len(matches) == 1

    def test_no_match_skips_proto(self):
        """Proto messages with no C++ match are silently skipped."""
        proto_msgs = [_make_proto_msg("NoMatch", [_make_field("id")])]
        cpp_msgs = [_make_cpp_msg("Other", [_make_field("id")])]

        matches = match_messages(proto_msgs, cpp_msgs)
        assert len(matches) == 0


class TestUnmatchedFieldError:
    def test_unmatched_proto_field_raises(self):
        proto_msgs = [
            _make_proto_msg("Order", [
                _make_field("order_id", "int32"),
                _make_field("missing_field", "string"),
            ])
        ]
        cpp_msgs = [
            _make_cpp_msg("Order", [
                _make_field("orderId", "int"),
            ])
        ]

        with pytest.raises(MatchError, match="missing_field"):
            match_messages(proto_msgs, cpp_msgs)


class TestNestedMatch:
    def test_nested_type_resolved(self):
        inner_proto = _make_proto_msg("Inner", [_make_field("value", "int32")])
        inner_cpp = _make_cpp_msg("Inner", [_make_field("value", "int")])

        proto_msgs = [
            _make_proto_msg("Outer", [
                _make_field("name", "string"),
                _make_field("detail", "Inner", is_nested=True, nested_type=inner_proto),
            ]),
            inner_proto,
        ]
        cpp_msgs = [
            _make_cpp_msg("Outer", [
                _make_field("name", "string"),
                _make_field("detail", "Inner"),
            ]),
            inner_cpp,
        ]

        matches = match_messages(proto_msgs, cpp_msgs)
        assert len(matches) == 2  # Both Outer and Inner matched
        outer_match = next(m for m in matches if m.proto_message.original_name == "Outer")
        detail_mapping = next(
            fm for fm in outer_match.field_mappings if fm.proto_field.original_name == "detail"
        )
        assert detail_mapping.cpp_field.is_nested is True


class TestRepeatedMatch:
    def test_repeated_field_matched(self):
        proto_msgs = [
            _make_proto_msg("Container", [
                _make_field("tags", "string", is_repeated=True),
            ])
        ]
        cpp_msgs = [
            _make_cpp_msg("Container", [
                _make_field("tags", "string", is_repeated=True),
            ])
        ]

        matches = match_messages(proto_msgs, cpp_msgs)
        assert len(matches) == 1
        assert matches[0].field_mappings[0].proto_field.is_repeated is True
