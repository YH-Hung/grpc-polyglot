import os
import shutil
import tempfile

from protoc_adapter.main import run


PROTO_CONTENT = """\
syntax = "proto3";

package order;

message OrderInfo {
    int32 order_id = 1;
    string customer_name = 2;
    bool is_active = 3;
    repeated OrderItem items = 4;

    message OrderItem {
        int32 item_id = 1;
        string item_name = 2;
        double price = 3;
    }
}

message ShippingAddress {
    string street = 1;
    string city = 2;
    int32 zip_code = 3;
}
"""

CPP_HEADER_CONTENT = """\
#pragma once

struct OrderItem {
    int itemId;
    char itemName[64];
    double price;
};

struct OrderInfo {
    int orderId;
    char customerName[128];
    bool isActive;
    OrderItem items[50];
};

struct ShippingAddress {
    char street[256];
    char city[128];
    int zipCode;
};
"""


class TestFullPipeline:
    def setup_method(self):
        self.work_dir = tempfile.mkdtemp()
        # Write proto file
        proto_path = os.path.join(self.work_dir, "order_service.proto")
        with open(proto_path, "w") as f:
            f.write(PROTO_CONTENT)
        # Write C++ header
        header_path = os.path.join(self.work_dir, "order.h")
        with open(header_path, "w") as f:
            f.write(CPP_HEADER_CONTENT)

    def teardown_method(self):
        shutil.rmtree(self.work_dir)

    def test_generates_dto_files(self):
        run(self.work_dir, "com.example")

        dto_dir = os.path.join(self.work_dir, "dto")
        assert os.path.isdir(dto_dir)

        dto_files = sorted(os.listdir(dto_dir))
        assert "OrderInfo.java" in dto_files
        assert "OrderItem.java" in dto_files
        assert "ShippingAddress.java" in dto_files

    def test_generates_mapper_file(self):
        run(self.work_dir, "com.example")

        mapper_dir = os.path.join(self.work_dir, "mapper")
        assert os.path.isdir(mapper_dir)

        mapper_files = os.listdir(mapper_dir)
        assert "OrderServiceMapper.java" in mapper_files

    def test_dto_content_correctness(self):
        run(self.work_dir, "com.example")

        # Check OrderInfo DTO
        dto_path = os.path.join(self.work_dir, "dto", "OrderInfo.java")
        content = open(dto_path).read()

        assert "package com.example.dto;" in content
        assert "@Getter" in content
        assert "@Setter" in content
        assert "@Builder" in content
        assert "public class OrderInfo {" in content
        assert "private Integer orderId;" in content
        assert "private String customerName;" in content  # char[] -> String
        assert "private Boolean isActive;" in content
        assert "private List<OrderItem> items;" in content  # array -> List
        assert "import java.util.List;" in content

        # Check no bad annotations
        assert "NoArgsConstructor" not in content
        assert "AllArgsConstructor" not in content

    def test_dto_char_array_maps_to_string(self):
        """char[] fields in C++ should become String in Java DTOs."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "ShippingAddress.java")
        content = open(dto_path).read()

        assert "private String street;" in content
        assert "private String city;" in content
        assert "private Integer zipCode;" in content

    def test_dto_array_maps_to_list(self):
        """C-style array fields should become List<T> in Java DTOs."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "OrderInfo.java")
        content = open(dto_path).read()

        assert "private List<OrderItem> items;" in content

    def test_mapper_content_correctness(self):
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(self.work_dir, "mapper", "OrderServiceMapper.java")
        content = open(mapper_path).read()

        assert "package com.example.mapper;" in content
        assert "public class OrderServiceMapper {" in content

        # Should have overloaded proto2Dto methods
        assert "proto2Dto(OrderServiceProto.OrderInfo proto)" in content
        assert "proto2Dto(OrderServiceProto.OrderItem proto)" in content
        assert "proto2Dto(OrderServiceProto.ShippingAddress proto)" in content

        # Check primitive field mapping
        assert ".orderId(proto.getOrderId())" in content
        assert ".customerName(proto.getCustomerName())" in content

        # Check repeated nested field mapping (items)
        assert ".items(proto.getItemsList().stream()" in content
        assert ".map(OrderServiceMapper::proto2Dto)" in content
        assert ".collect(Collectors.toList()))" in content

        # Check nested item fields
        assert ".itemId(proto.getItemId())" in content
        assert ".itemName(proto.getItemName())" in content

    def test_dto_uses_cpp_naming(self):
        """Field names in DTOs must use C++ casing, not proto casing."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "OrderInfo.java")
        content = open(dto_path).read()

        # Should use C++ camelCase, not proto snake_case
        assert "orderId" in content
        assert "order_id" not in content
        assert "customerName" in content
        assert "customer_name" not in content


ADVANCED_PROTO_CONTENT = """\
syntax = "proto3";

package advanced;

message ExecutionReport {
    int32 id = 1;
    string venue = 2;
    double fill_price = 3;
    int32 fill_quantity = 4;
    int64 fill_time = 5;
}

message AdvancedOrder {
    int32 order_id = 1;
    string instrument_code = 2;
    double quantity = 3;
    double unit_price = 4;
    bool is_buy = 5;

    TraderInfo trader_info = 6;

    message TraderInfo {
        int32 oder_id = 1;
        string trader_name = 2;
    }

    Fee fee = 7;

    message Fee {
        string fee_type = 1;
        double amount = 2;
    }

    ExecutionReport execution = 8;
}
"""

ADVANCED_CPP_CONTENT = """\
#pragma once

typedef int UserId;
typedef double Price;
typedef long Timestamp;

typedef struct {
    UserId id;
    char venue[64];
    Price fillPrice;
    int fillQuantity;
    Timestamp fillTime;
} ExecutionReport;

struct AdvancedOrder {
    int orderId;
    char instrumentCode[32];
    Price quantity;
    Price unitPrice;
    bool isBuy;
    struct {
        UserId oderId;
        char traderName[64];
    } traderInfo;
    struct {
        char feeType[32];
        Price amount;
    } fee;
    ExecutionReport execution;
};
"""


class TestAdvancedTypesPipeline:
    """E2E tests for anonymous structs and type aliases."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp()
        proto_path = os.path.join(self.work_dir, "advanced_service.proto")
        with open(proto_path, "w") as f:
            f.write(ADVANCED_PROTO_CONTENT)
        header_path = os.path.join(self.work_dir, "advanced_types.h")
        with open(header_path, "w") as f:
            f.write(ADVANCED_CPP_CONTENT)

    def teardown_method(self):
        shutil.rmtree(self.work_dir)

    def test_generates_dto_files(self):
        """DTOs generated for anonymous typedef struct and nested anonymous structs."""
        run(self.work_dir, "com.example")

        dto_dir = os.path.join(self.work_dir, "dto")
        assert os.path.isdir(dto_dir)
        dto_files = sorted(os.listdir(dto_dir))
        assert "ExecutionReport.java" in dto_files
        assert "AdvancedOrder.java" in dto_files
        assert "TraderInfo.java" in dto_files
        assert "Fee.java" in dto_files

    def test_generates_mapper_file(self):
        run(self.work_dir, "com.example")

        mapper_dir = os.path.join(self.work_dir, "mapper")
        assert os.path.isdir(mapper_dir)
        mapper_files = os.listdir(mapper_dir)
        assert "AdvancedServiceMapper.java" in mapper_files

    def test_type_alias_resolved_in_dto(self):
        """Fields using type aliases should resolve to primitive types in DTOs."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "ExecutionReport.java")
        content = open(dto_path).read()

        # UserId -> int -> Integer
        assert "private Integer id;" in content
        # Price -> double -> Double
        assert "private Double fillPrice;" in content
        # Timestamp -> long -> Long
        assert "private Long fillTime;" in content
        assert "private String venue;" in content

    def test_anonymous_nested_struct_dto(self):
        """Nested anonymous struct fields should become nested DTOs."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "AdvancedOrder.java")
        content = open(dto_path).read()

        assert "private TraderInfo traderInfo;" in content
        assert "private Fee fee;" in content
        assert "private ExecutionReport execution;" in content
        # Type aliases resolved: Price -> double -> Double
        assert "private Double quantity;" in content
        assert "private Double unitPrice;" in content

    def test_anonymous_nested_struct_dto_content(self):
        """TraderInfo and Fee DTOs generated from anonymous structs have correct fields."""
        run(self.work_dir, "com.example")

        trader_path = os.path.join(self.work_dir, "dto", "TraderInfo.java")
        trader = open(trader_path).read()
        assert "private Integer oderId;" in trader
        assert "private String traderName;" in trader

        fee_path = os.path.join(self.work_dir, "dto", "Fee.java")
        fee = open(fee_path).read()
        assert "private String feeType;" in fee
        assert "private Double amount;" in fee

    def test_mapper_content(self):
        """Mapper should handle type-aliased and anonymous-struct fields."""
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(
            self.work_dir, "mapper", "AdvancedServiceMapper.java"
        )
        content = open(mapper_path).read()

        assert "package com.example.mapper;" in content
        assert "public class AdvancedServiceMapper {" in content

        # Should have proto2Dto methods for all matched messages
        assert "proto2Dto(AdvancedServiceProto.ExecutionReport proto)" in content
        assert "proto2Dto(AdvancedServiceProto.AdvancedOrder proto)" in content
        assert "proto2Dto(AdvancedServiceProto.TraderInfo proto)" in content
        assert "proto2Dto(AdvancedServiceProto.Fee proto)" in content

        # Nested field mappings should call proto2Dto
        assert "proto2Dto(proto.getTraderInfo())" in content
        assert "proto2Dto(proto.getFee())" in content
        # ExecutionReport is a non-primitive type, so mapper calls proto2Dto
        assert ".execution(proto2Dto(proto.getExecution()))" in content


# --- Rep* Message Tests ---

REP_PROTO_CONTENT = """\
syntax = "proto3";

package reply;

message msgHeader {
    int32 retCode = 1;
    string msgOwnId = 2;
    string timestamp = 3;
    int32 seqNum = 4;
}

message RepOrderInfo {
    msgHeader msg_header = 1;
    int32 order_id = 2;
    string instrument_code = 3;
    double quantity = 4;
}

message RepAccountStatus {
    msgHeader msg_header = 1;
    int32 account_id = 2;
    double balance = 3;
}

message OrderRequest {
    int32 order_id = 1;
    string instrument_code = 2;
    double quantity = 3;
}
"""

REP_CPP_CONTENT = """\
#pragma once

struct RepOrderInfo {
    int orderId;
    char instrumentCode[32];
    double quantity;
};

struct RepAccountStatus {
    int accountId;
    double balance;
};

struct OrderRequest {
    int orderId;
    char instrumentCode[32];
    double quantity;
};
"""


class TestRepMessagePipeline:
    """E2E tests for Rep* message -> WebServiceReplyHeader handling."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp()
        proto_path = os.path.join(self.work_dir, "rep_service.proto")
        with open(proto_path, "w") as f:
            f.write(REP_PROTO_CONTENT)
        header_path = os.path.join(self.work_dir, "rep_types.h")
        with open(header_path, "w") as f:
            f.write(REP_CPP_CONTENT)

    def teardown_method(self):
        shutil.rmtree(self.work_dir)

    def test_web_service_reply_header_dto_generated(self):
        """WebServiceReplyHeader.java is generated with renamed fields."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "WebServiceReplyHeader.java")
        assert os.path.isfile(dto_path)

        content = open(dto_path).read()
        assert "public class WebServiceReplyHeader {" in content
        assert "private Integer returnCode;" in content
        assert "private String returnMessage;" in content
        # Should NOT contain original field names
        assert "retCode" not in content
        assert "msgOwnId" not in content
        # Should NOT contain extra fields from msgHeader
        assert "timestamp" not in content
        assert "seqNum" not in content

    def test_rep_message_dto_has_header_field(self):
        """Rep* DTOs include a WebServiceReplyHeader msgHeader field."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "RepOrderInfo.java")
        content = open(dto_path).read()
        assert "private WebServiceReplyHeader msgHeader;" in content
        assert "private Integer orderId;" in content
        assert "private String instrumentCode;" in content
        assert "private Double quantity;" in content

    def test_rep_account_status_dto_has_header_field(self):
        """Multiple Rep* messages all get the WebServiceReplyHeader field."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "RepAccountStatus.java")
        content = open(dto_path).read()
        assert "private WebServiceReplyHeader msgHeader;" in content
        assert "private Integer accountId;" in content
        assert "private Double balance;" in content

    def test_non_rep_message_unaffected(self):
        """Non-Rep messages are generated normally without WebServiceReplyHeader."""
        run(self.work_dir, "com.example")

        dto_path = os.path.join(self.work_dir, "dto", "OrderRequest.java")
        content = open(dto_path).read()
        assert "WebServiceReplyHeader" not in content
        assert "private Integer orderId;" in content
        assert "private String instrumentCode;" in content
        assert "private Double quantity;" in content

    def test_mapper_uses_builder_for_header(self):
        """Mapper generates builder pattern for msgHeader, not proto2Dto."""
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(self.work_dir, "mapper", "RepServiceMapper.java")
        content = open(mapper_path).read()

        # Should use builder pattern for msgHeader
        assert ".msgHeader(WebServiceReplyHeader.builder()" in content
        assert ".returnCode(proto.getMsgHeader().getRetCode())" in content
        assert ".returnMessage(proto.getMsgHeader().getMsgOwnId())" in content
        # Should NOT use proto2Dto for the header field
        assert "proto2Dto(proto.getMsgHeader())" not in content

    def test_mapper_non_rep_fields_normal(self):
        """Non-header fields in Rep* messages use normal getter mapping."""
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(self.work_dir, "mapper", "RepServiceMapper.java")
        content = open(mapper_path).read()

        assert ".orderId(proto.getOrderId())" in content
        assert ".instrumentCode(proto.getInstrumentCode())" in content

    def test_mapper_non_rep_message_normal(self):
        """Non-Rep message mapper uses normal proto2Dto mapping."""
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(self.work_dir, "mapper", "RepServiceMapper.java")
        content = open(mapper_path).read()

        assert "proto2Dto(RepServiceProto.OrderRequest proto)" in content

    def test_no_proto2dto_for_msg_header(self):
        """No proto2Dto method should be generated for msgHeader."""
        run(self.work_dir, "com.example")

        mapper_path = os.path.join(self.work_dir, "mapper", "RepServiceMapper.java")
        content = open(mapper_path).read()

        assert "proto2Dto(RepServiceProto.msgHeader proto)" not in content

    def test_generates_all_expected_dto_files(self):
        """All expected DTO files are generated."""
        run(self.work_dir, "com.example")

        dto_dir = os.path.join(self.work_dir, "dto")
        dto_files = sorted(os.listdir(dto_dir))
        assert "OrderRequest.java" in dto_files
        assert "RepAccountStatus.java" in dto_files
        assert "RepOrderInfo.java" in dto_files
        assert "WebServiceReplyHeader.java" in dto_files
