# Protobuf to Java Adapter Tool

A Python CLI that generates Java DTOs and Mapper classes by matching Protobuf `.proto` messages against C++ header structs. Generated Java code uses **C++ naming conventions** and is structurally compatible with Protobuf messages.

## Quick Start

```bash
# From protoc-adapter-py/ directory
cd protoc-adapter-py

# Install dependencies
uv sync

# Run with the included sample files
uv run python -m protoc_adapter \
  --working-path sample \
  --java-package com.trading.adapter

# Check generated output
ls sample/dto/     # TradeOrder.java, TradeExecution.java, TradeFee.java, AccountInfo.java
ls sample/mapper/  # TradeServiceMapper.java
```

## Usage

```bash
uv run python -m protoc_adapter --working-path <PATH> --java-package <PACKAGE>
```

| Argument | Description |
|---|---|
| `--working-path` | Directory to scan for `.proto` and `.h`/`.hpp` files (recursive). Output `dto/` and `mapper/` directories are created here. |
| `--java-package` | Java package name for generated code (e.g., `com.example.myservice`). |

## How It Works

### 1. Parsing
The tool recursively scans `--working-path` for `.proto` and C++ header files, then parses them using **brace-counting state machines** (not regex-only) to correctly handle nested messages/structs.

### 2. Matching
Messages and structs are matched by **normalized name** (remove underscores, uppercase):

| Proto | C++ | Normalized |
|---|---|---|
| `mask_group_id` | `maskGroupId` | `MASKGROUPID` |
| `OrderInfo` | `OrderInfo` | `ORDERINFO` |

**Strict validation**: Every field in a matched proto message **must** have a corresponding C++ field. Unmatched fields cause a fatal error.

### 3. Code Generation

**DTOs** use Lombok `@Data` + `@Builder`, with field names from C++:
```java
@Data
@Builder
public class TradeOrder {
    private Integer orderId;
    private String instrumentCode;
    private List<TradeFee> fees;
}
```

**Mappers** generate overloaded `proto2Dto` methods (one per matched message):
```java
public class TradeServiceMapper {
    public static TradeOrder proto2Dto(TradeServiceProto.TradeOrder proto) {
        return TradeOrder.builder()
            .orderId(proto.getOrderId())
            .fees(proto.getFeesList().stream()
                .map(TradeServiceMapper::proto2Dto)
                .collect(Collectors.toList()))
            .build();
    }
}
```

## C++ Type Mapping

| C++ Type | Java Type | Notes |
|---|---|---|
| `int` | `Integer` | |
| `long` | `Long` | |
| `float` | `Float` | |
| `double` | `Double` | |
| `bool` | `Boolean` | |
| `char name[N]` | `String` | Char arrays treated as strings |
| `Type items[N]` | `List<Type>` | C-style arrays treated as repeated |
| `std::string` | `String` | Also supported |
| `std::vector<T>` | `List<T>` | Also supported |
| Nested struct | Struct name | Recursive mapper call |

## Advanced C Features

### Type Aliases

`typedef` aliases are resolved to their underlying types during parsing:

```c
typedef int UserId;
typedef double Price;

struct Order {
    UserId id;       // resolved to int -> Integer
    Price unitPrice; // resolved to double -> Double
};
```

Chained aliases are also supported (`typedef int A; typedef A B;` resolves `B` to `int`).
Struct aliases work too (`typedef struct TradeOrder TradeAlias;`).

### Anonymous Structs

**Top-level anonymous typedef structs** are parsed using the name after the closing brace:

```c
typedef struct {
    int id;
    char venue[64];
} ExecutionReport; // parsed as struct "ExecutionReport"
```

**Nested anonymous structs** generate a synthetic type name by capitalizing the field name:

```c
struct Order {
    struct {
        int traderId;
        char traderName[64];
    } traderInfo; // generates struct "TraderInfo"
    int orderId;
};
```

The matching proto would define `TraderInfo` as a nested message:

```protobuf
message Order {
    TraderInfo trader_info = 1;
    message TraderInfo {
        int32 trader_id = 1;
        string trader_name = 2;
    }
    int32 order_id = 2;
}
```

## Sample Input/Output

### Input: `trade_service.proto`
```protobuf
syntax = "proto3";

message TradeOrder {
    int32 order_id = 1;
    string instrument_code = 2;
    double quantity = 3;
    bool is_buy = 4;
    TradeExecution execution = 5;
    repeated TradeFee fees = 6;

    message TradeExecution {
        int64 execution_id = 1;
        string execution_venue = 2;
    }

    message TradeFee {
        string fee_type = 1;
        double amount = 2;
    }
}
```

### Input: `trade_types.h`
```cpp
#pragma once

struct TradeExecution {
    long executionId;
    char executionVenue[64];
};

struct TradeFee {
    char feeType[32];
    double amount;
};

struct TradeOrder {
    int orderId;
    char instrumentCode[32];
    double quantity;
    bool isBuy;
    TradeExecution execution;
    TradeFee fees[20];
};
```

### Output: `dto/TradeOrder.java`
```java
package com.trading.adapter.dto;

import lombok.Data;
import lombok.Builder;
import java.util.List;

@Data
@Builder
public class TradeOrder {
    private Integer orderId;
    private String instrumentCode;
    private Double quantity;
    private Boolean isBuy;
    private TradeExecution execution;
    private List<TradeFee> fees;
}
```

### Output: `mapper/TradeServiceMapper.java`
```java
package com.trading.adapter.mapper;

import com.trading.adapter.dto.*;
import java.util.stream.Collectors;

public class TradeServiceMapper {

    public static TradeOrder proto2Dto(TradeServiceProto.TradeOrder proto) {
        return TradeOrder.builder()
            .orderId(proto.getOrderId())
            .instrumentCode(proto.getInstrumentCode())
            .quantity(proto.getQuantity())
            .isBuy(proto.getIsBuy())
            .execution(proto2Dto(proto.getExecution()))
            .fees(proto.getFeesList().stream()
                .map(TradeServiceMapper::proto2Dto)
                .collect(Collectors.toList()))
            .build();
    }

    public static TradeExecution proto2Dto(TradeServiceProto.TradeExecution proto) { ... }
    public static TradeFee proto2Dto(TradeServiceProto.TradeFee proto) { ... }
}
```

## Running Tests

```bash
cd protoc-adapter-py

# Run all 59 tests
uv run pytest -v

# Run specific test modules
uv run pytest tests/test_proto_parser.py -v     # 7 tests - proto parsing
uv run pytest tests/test_cpp_parser.py -v       # 22 tests - C++ parsing (char[], arrays, vector, nested, anonymous structs, type aliases)
uv run pytest tests/test_matcher.py -v          # 6 tests - name matching & validation
uv run pytest tests/test_dto_generator.py -v    # 4 tests - DTO generation
uv run pytest tests/test_mapper_generator.py -v # 7 tests - Mapper generation
uv run pytest tests/test_integration.py -v      # 13 tests - full end-to-end pipeline
```

## Project Structure

```
protoc-adapter-py/
├── pyproject.toml
├── sample/                          # Sample input files for testing
│   ├── trade_service.proto
│   ├── trade_types.h
│   ├── advanced_service.proto       # Anonymous structs & type aliases
│   └── advanced_types.h
├── src/protoc_adapter/
│   ├── __main__.py                  # CLI entry point
│   ├── main.py                      # Orchestration & arg parsing
│   ├── models.py                    # Field, Message dataclasses
│   ├── parser/
│   │   ├── proto_parser.py          # Brace-counting proto parser
│   │   └── cpp_parser.py            # Brace-counting C++ parser
│   ├── matcher.py                   # Normalization & strict matching
│   ├── generator/
│   │   ├── java_dto_generator.py    # Jinja2 DTO renderer
│   │   └── java_mapper_generator.py # Jinja2 Mapper renderer
│   └── templates/
│       ├── dto.java.j2
│       └── mapper.java.j2
└── tests/                           # 59 tests total
    ├── test_proto_parser.py
    ├── test_cpp_parser.py
    ├── test_matcher.py
    ├── test_dto_generator.py
    ├── test_mapper_generator.py
    └── test_integration.py
```
