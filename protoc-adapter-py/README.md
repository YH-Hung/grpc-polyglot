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

# Also generate MapStruct mapper interfaces
uv run python -m protoc_adapter \
  --working-path sample \
  --java-package com.trading.adapter \
  --mapstruct

# Check MapStruct output
ls sample/mapstruct_mapper/  # TradeServiceMapStructMapper.java, spi/, META-INF/, MAVEN_INTEGRATION.md
```

## Usage

```bash
uv run python -m protoc_adapter --working-path <PATH> --java-package <PACKAGE> [--mapstruct]
```

| Argument | Description |
|---|---|
| `--working-path` | Directory to scan for `.proto` and `.h`/`.hpp` files (recursive). Output directories are created here. |
| `--java-package` | Java package name for generated code (e.g., `com.example.myservice`). |
| `--mapstruct` | *(Optional)* Also generate MapStruct `@Mapper` interfaces with a custom naming strategy. See [MapStruct Mapper Generation](#mapstruct-mapper-generation). |

## How It Works

### 1. Parsing
The tool recursively scans `--working-path` for `.proto` and C++ header files, then parses them using a three-stage **AST pipeline** for each language: **Tokenizer** (single-pass character scanner) → **Recursive Descent Parser** (produces typed AST nodes) → **Transformer** (converts AST to shared `Message`/`Field` models). This cleanly handles nested messages/structs, type aliases, and anonymous definitions.

### 2. Matching
Messages and structs are matched by **normalized name** (remove underscores, uppercase):

| Proto | C++ | Normalized |
|---|---|---|
| `mask_group_id` | `maskGroupId` | `MASKGROUPID` |
| `OrderInfo` | `OrderInfo` | `ORDERINFO` |

**Strict validation**: Every field in a matched proto message **must** have a corresponding C++ field. Unmatched fields cause a fatal error.

### 3. Code Generation

**DTOs** use Lombok `@Getter` + `@Setter` + `@Builder`, with field names from C++:
```java
@Getter
@Setter
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

## Rep\* Message Handling

Proto messages whose names start with `Rep` (e.g., `RepOrderInfo`, `RepAccountStatus`) receive special handling for the `msgHeader` field. This field has no C++ counterpart — instead, the tool generates a `WebServiceReplyHeader` DTO with renamed fields.

### Field Rename Mapping

| `msgHeader` field | `WebServiceReplyHeader` field |
|---|---|
| `retCode` | `returnCode` |
| `msgOwnId` | `returnMessage` |

Only these two fields are included in `WebServiceReplyHeader`. Other `msgHeader` fields are excluded.

### Example

**Proto** (`rep_service.proto`):
```protobuf
message msgHeader {
    int32 retCode = 1;
    string msgOwnId = 2;
    string timestamp = 3;
    int32 seqNum = 4;
}

message RepOrderInfo {
    msgHeader msgHeader = 1;
    int32 orderId = 2;
    string instrumentCode = 3;
}
```

**C++** (`rep_types.h`) — no `msgHeader` field:
```cpp
struct RepOrderInfo {
    int orderId;
    char instrumentCode[32];
};
```

**Generated DTO** (`dto/WebServiceReplyHeader.java`):
```java
@Getter
@Setter
@Builder
public class WebServiceReplyHeader {
    private Integer returnCode;
    private String returnMessage;
}
```

**Generated DTO** (`dto/RepOrderInfo.java`):
```java
@Getter
@Setter
@Builder
public class RepOrderInfo {
    private WebServiceReplyHeader msgHeader;
    private Integer orderId;
    private String instrumentCode;
}
```

**Generated Mapper** — uses builder pattern for `msgHeader` instead of `proto2Dto`:
```java
public static RepOrderInfo proto2Dto(RepServiceProto.RepOrderInfo proto) {
    return RepOrderInfo.builder()
        .msgHeader(WebServiceReplyHeader.builder()
            .returnCode(proto.getMsgHeader().getRetCode())
            .returnMessage(proto.getMsgHeader().getMsgOwnId())
            .build())
        .orderId(proto.getOrderId())
        .instrumentCode(proto.getInstrumentCode())
        .build();
}
```

Non-Rep messages (e.g., `OrderRequest`) are unaffected and follow the standard mapping pipeline.

## MapStruct Mapper Generation

When `--mapstruct` is passed, the tool generates MapStruct `@Mapper` interfaces as an alternative to the hand-written static mapper classes. The key design principle: **no `@Mapping` annotations** — all field matching is handled by a custom `AccessorNamingStrategy` (MapStruct SPI).

### Generated Output

All files below are generated at runtime inside `mapstruct_mapper/` under the working path. The `MAVEN_INTEGRATION.md` and `ProtobufAccessorNamingStrategy.java` are rendered from Jinja2 templates with the `--java-package` value substituted, so package declarations and SPI references match your project.

```
mapstruct_mapper/
├── TradeServiceMapStructMapper.java       # @Mapper interface (one per proto file)
├── spi/
│   └── ProtobufAccessorNamingStrategy.java  # Custom naming strategy
├── META-INF/
│   └── services/
│       └── org.mapstruct.ap.spi.AccessorNamingStrategy  # SPI registration
└── MAVEN_INTEGRATION.md                   # Step-by-step Maven setup guide
```

### Example: Generated MapStruct Interface

```java
@Mapper
public interface TradeServiceMapStructMapper {

    TradeServiceMapStructMapper INSTANCE = Mappers.getMapper(TradeServiceMapStructMapper.class);

    TradeOrder toDto(TradeServiceProto.TradeOrder proto);

    TradeExecution toDto(TradeServiceProto.TradeExecution proto);

    TradeFee toDto(TradeServiceProto.TradeFee proto);
}
```

No field-level `@Mapping` annotations — MapStruct auto-matches fields using the custom naming strategy at compile time.

### Custom Naming Strategy

The `ProtobufAccessorNamingStrategy` handles three issues that would otherwise prevent automatic field matching:

1. **Repeated field renaming**: Proto generates `getFeesList()` for repeated fields. The strategy strips the `List` suffix (when return type is `java.util.List`) so the property name `fees` matches the DTO field.

2. **Proto internal method filtering**: Excludes proto-generated methods that are not user fields — `getXxxOrBuilder()`, `getXxxBytes()`, `getXxxCount()`, `getAllFields()`, `getDescriptorForType()`, etc.

3. **Casing normalization**: Property names are normalized (underscores removed, lowercased) on both source and target types. This overcomes casing differences between proto accessors (e.g., `orderId`) and C++ DTO fields (e.g., `orderID`) — both normalize to `orderid`. MapStruct uses normalized names only for matching; the generated code still calls the original methods.

### Rep\* Messages

For Rep\* messages with `msgHeader`, a `default` method maps `msgHeader` to `WebServiceReplyHeader` manually:

```java
default WebServiceReplyHeader toDto(RepServiceProto.msgHeader proto) {
    if (proto == null) {
        return null;
    }
    return WebServiceReplyHeader.builder()
        .returnCode(proto.getRetCode())
        .returnMessage(proto.getMsgOwnId())
        .build();
}
```

MapStruct auto-discovers this method for type-level conversion when it encounters the `msgHeader` → `WebServiceReplyHeader` type mismatch.

### Maven Integration

The generated `MAVEN_INTEGRATION.md` provides full setup instructions, but the key points are:

1. Add `mapstruct` and `lombok` dependencies
2. Configure annotation processor ordering in `maven-compiler-plugin` — **Lombok must run before MapStruct** (use `lombok-mapstruct-binding`)
3. Place `ProtobufAccessorNamingStrategy.java` in `src/main/java` and the SPI file in `src/main/resources/META-INF/services/`

```java
// Usage after Maven compilation:
TradeServiceMapStructMapper mapper = TradeServiceMapStructMapper.INSTANCE;
TradeOrder dto = mapper.toDto(protoTradeOrder);
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

import lombok.Getter;
import lombok.Setter;
import lombok.Builder;
import java.util.List;

@Getter
@Setter
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

# Run all tests
uv run pytest -v

# Run specific test modules
uv run pytest tests/test_proto_parser.py -v         # 7 tests - proto parsing
uv run pytest tests/test_cpp_parser.py -v           # 22 tests - C++ parsing (char[], arrays, vector, nested, anonymous structs, type aliases)
uv run pytest tests/test_matcher.py -v              # 6 tests - name matching & validation
uv run pytest tests/test_dto_generator.py -v        # 4 tests - DTO generation
uv run pytest tests/test_mapper_generator.py -v     # 7 tests - Mapper generation
uv run pytest tests/test_mapstruct_generator.py -v  # 14 tests - MapStruct mapper generation
uv run pytest tests/test_rep_message_handler.py -v  # Rep* message handling unit tests
uv run pytest tests/test_integration.py -v          # full end-to-end pipeline (incl. MapStruct)
```

## Project Structure

```
protoc-adapter-py/
├── pyproject.toml
├── sample/                          # Sample input files for testing
│   ├── trade_service.proto
│   ├── trade_types.h
│   ├── advanced_service.proto       # Anonymous structs & type aliases
│   ├── advanced_types.h
│   ├── rep_service.proto            # Rep* messages with msgHeader
│   └── rep_types.h
├── src/protoc_adapter/
│   ├── __main__.py                  # CLI entry point
│   ├── main.py                      # Orchestration & arg parsing
│   ├── models.py                    # Field, Message dataclasses
│   ├── parser/
│   │   ├── proto_parser.py          # Proto parsing entry point
│   │   ├── proto_ast.py             # Proto AST node definitions
│   │   ├── proto_tokenizer.py       # Proto tokenizer
│   │   ├── proto_ast_parser.py      # Proto recursive descent parser
│   │   ├── proto_transform.py       # Proto AST → Message transform
│   │   ├── cpp_parser.py            # C++ parsing entry point
│   │   ├── cpp_ast.py               # C++ AST node definitions
│   │   ├── cpp_tokenizer.py         # C++ tokenizer
│   │   ├── cpp_ast_parser.py        # C++ recursive descent parser
│   │   └── cpp_transform.py         # C++ AST → Message transform
│   ├── matcher.py                   # Normalization & strict matching
│   ├── rep_message_handler.py       # Rep* message → WebServiceReplyHeader
│   ├── generator/
│   │   ├── java_dto_generator.py         # Jinja2 DTO renderer
│   │   ├── java_mapper_generator.py      # Jinja2 Mapper renderer
│   │   └── java_mapstruct_generator.py   # MapStruct interface & SPI generator
│   └── templates/
│       ├── dto.java.j2
│       ├── mapper.java.j2
│       ├── mapstruct_mapper.java.j2                    # MapStruct @Mapper interface
│       ├── protobuf_accessor_naming_strategy.java.j2   # Custom SPI naming strategy
│       └── mapstruct_maven_integration.md.j2           # Maven integration guide
└── tests/
    ├── test_proto_parser.py
    ├── test_cpp_parser.py
    ├── test_matcher.py
    ├── test_dto_generator.py
    ├── test_mapper_generator.py
    ├── test_mapstruct_generator.py
    ├── test_rep_message_handler.py
    └── test_integration.py
```
