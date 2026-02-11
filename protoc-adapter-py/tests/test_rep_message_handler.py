from protoc_adapter.models import Field, FieldMapping, Message, MessageMatch, normalize
from protoc_adapter.rep_message_handler import (
    HEADER_FIELD_RENAMES,
    WEB_SERVICE_REPLY_HEADER_CLASS,
    _camel_case_getter,
    build_web_service_reply_header_match,
    find_msg_header_field,
    inject_header_field_mappings,
    is_rep_message,
    resolve_msg_header_definition,
    strip_msg_header_fields,
)


def _make_field(name, type_name, is_repeated=False, is_nested=False, nested_type=None):
    return Field(
        original_name=name,
        normalized_name=normalize(name),
        type_name=type_name,
        is_repeated=is_repeated,
        is_nested=is_nested,
        nested_type=nested_type,
    )


def _make_message(name, fields, source_file="test.proto"):
    return Message(
        original_name=name,
        normalized_name=normalize(name),
        fields=fields,
        source_file=source_file,
    )


class TestCamelCaseGetter:
    def test_camel_case_field(self):
        assert _camel_case_getter("retCode") == "RetCode"

    def test_camel_case_field_msg(self):
        assert _camel_case_getter("msgOwnId") == "MsgOwnId"

    def test_simple_field(self):
        assert _camel_case_getter("name") == "Name"

    def test_empty_string(self):
        assert _camel_case_getter("") == ""


class TestIsRepMessage:
    def test_rep_prefix(self):
        msg = _make_message("RepOrderInfo", [])
        assert is_rep_message(msg) is True

    def test_non_rep_prefix(self):
        msg = _make_message("OrderInfo", [])
        assert is_rep_message(msg) is False

    def test_rep_exact(self):
        msg = _make_message("Rep", [])
        assert is_rep_message(msg) is True

    def test_rep_lowercase(self):
        msg = _make_message("repOrderInfo", [])
        assert is_rep_message(msg) is False

    def test_reply_not_rep(self):
        msg = _make_message("ReplyInfo", [])
        assert is_rep_message(msg) is True


class TestFindMsgHeaderField:
    def test_finds_msg_header(self):
        header_field = _make_field("msgHeader", "msgHeader", is_nested=True)
        msg = _make_message("RepOrderInfo", [
            header_field,
            _make_field("orderId", "int32"),
        ])
        result = find_msg_header_field(msg)
        assert result is header_field

    def test_no_msg_header(self):
        msg = _make_message("RepOrderInfo", [
            _make_field("orderId", "int32"),
        ])
        result = find_msg_header_field(msg)
        assert result is None

    def test_non_nested_msg_header_not_found(self):
        """msgHeader must be a nested (non-primitive) field."""
        msg = _make_message("RepOrderInfo", [
            _make_field("msgHeader", "msgHeader", is_nested=False),
        ])
        result = find_msg_header_field(msg)
        assert result is None


class TestStripMsgHeaderFields:
    def test_strips_from_rep_message(self):
        header_field = _make_field("msgHeader", "msgHeader", is_nested=True)
        rep_msg = _make_message("RepOrderInfo", [
            header_field,
            _make_field("orderId", "int32"),
        ])
        non_rep_msg = _make_message("OrderInfo", [
            _make_field("orderId", "int32"),
        ])
        messages = [rep_msg, non_rep_msg]

        result_msgs, stripped = strip_msg_header_fields(messages)

        # Rep message should have msgHeader stripped
        assert len(rep_msg.fields) == 1
        assert rep_msg.fields[0].original_name == "orderId"
        # Stripped dict has the field
        assert "RepOrderInfo" in stripped
        assert stripped["RepOrderInfo"] is header_field
        # Non-Rep message unchanged
        assert len(non_rep_msg.fields) == 1

    def test_preserves_non_rep_message(self):
        msg = _make_message("OrderInfo", [
            _make_field("msgHeader", "msgHeader", is_nested=True),
            _make_field("orderId", "int32"),
        ])
        _, stripped = strip_msg_header_fields([msg])

        assert len(msg.fields) == 2
        assert len(stripped) == 0

    def test_rep_without_msg_header(self):
        msg = _make_message("RepOrderInfo", [
            _make_field("orderId", "int32"),
        ])
        _, stripped = strip_msg_header_fields([msg])

        assert len(msg.fields) == 1
        assert len(stripped) == 0


class TestResolveMsgHeaderDefinition:
    def test_finds_definition(self):
        msg_header = _make_message("msgHeader", [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
        ])
        other = _make_message("OrderInfo", [_make_field("id", "int32")])
        result = resolve_msg_header_definition([other, msg_header])
        assert result is msg_header

    def test_not_found(self):
        other = _make_message("OrderInfo", [_make_field("id", "int32")])
        result = resolve_msg_header_definition([other])
        assert result is None


class TestBuildWebServiceReplyHeaderMatch:
    def test_creates_synthetic_match(self):
        msg_header = _make_message("msgHeader", [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
            _make_field("timestamp", "string"),
            _make_field("seqNum", "int32"),
        ])

        match = build_web_service_reply_header_match(msg_header)

        assert match.cpp_message.original_name == WEB_SERVICE_REPLY_HEADER_CLASS
        # Only 2 fields (retCode and msgOwnId), not all 4
        assert len(match.field_mappings) == 2

    def test_renames_applied(self):
        msg_header = _make_message("msgHeader", [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
        ])

        match = build_web_service_reply_header_match(msg_header)

        cpp_names = {fm.cpp_field.original_name for fm in match.field_mappings}
        assert cpp_names == {"returnCode", "returnMessage"}

    def test_field_types_preserved(self):
        msg_header = _make_message("msgHeader", [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
        ])

        match = build_web_service_reply_header_match(msg_header)

        type_map = {fm.cpp_field.original_name: fm.cpp_field.type_name for fm in match.field_mappings}
        assert type_map["returnCode"] == "int32"
        assert type_map["returnMessage"] == "string"


class TestInjectHeaderFieldMappings:
    def test_injects_into_rep_match(self):
        msg_header_def = _make_message("msgHeader", [
            _make_field("retCode", "int32"),
            _make_field("msgOwnId", "string"),
        ])
        header_field = _make_field("msgHeader", "msgHeader", is_nested=True)

        proto_msg = _make_message("RepOrderInfo", [_make_field("orderId", "int32")])
        cpp_msg = _make_message("RepOrderInfo", [_make_field("orderId", "int")])
        match = MessageMatch(
            proto_message=proto_msg,
            cpp_message=cpp_msg,
            field_mappings=[
                FieldMapping(
                    proto_field=_make_field("orderId", "int32"),
                    cpp_field=_make_field("orderId", "int"),
                )
            ],
        )

        stripped = {"RepOrderInfo": header_field}
        inject_header_field_mappings([match], stripped, msg_header_def)

        assert len(match.field_mappings) == 2
        # Reply header mapping should be first
        reply_mapping = match.field_mappings[0]
        assert reply_mapping.is_reply_header is True
        assert reply_mapping.cpp_field.type_name == WEB_SERVICE_REPLY_HEADER_CLASS
        assert reply_mapping.cpp_field.original_name == "msgHeader"
        # nested_type should be linked
        assert reply_mapping.proto_field.nested_type is msg_header_def

    def test_skips_non_rep_match(self):
        proto_msg = _make_message("OrderInfo", [_make_field("orderId", "int32")])
        cpp_msg = _make_message("OrderInfo", [_make_field("orderId", "int")])
        match = MessageMatch(
            proto_message=proto_msg,
            cpp_message=cpp_msg,
            field_mappings=[
                FieldMapping(
                    proto_field=_make_field("orderId", "int32"),
                    cpp_field=_make_field("orderId", "int"),
                )
            ],
        )

        inject_header_field_mappings([match], {}, None)

        assert len(match.field_mappings) == 1
        assert match.field_mappings[0].is_reply_header is False
