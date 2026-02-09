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
        assert "@Data" in content
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
        # ExecutionReport is a top-level message (not nested in AdvancedOrder),
        # so it uses direct getter, not proto2Dto
        assert ".execution(proto.getExecution())" in content
