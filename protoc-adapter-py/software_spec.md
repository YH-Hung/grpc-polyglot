# Software Specification: Protobuf to Java Adapter Tool

## 1. Overview
The **Protobuf to Java Adapter Tool** is a Python-based utility designed to automate the generation of Java DTOs and Mapping functions. It bridges the gap between Protobuf message definitions and legacy C++ header files by strictly adhering to C++ naming conventions for the generated Java code while ensuring structural compatibility with Protobuf messages.

## 2. Terminology
- **Proto**: Google Protobuf definition file (`.proto`).
- **CppHeader**: C++ header file (`.h` or `.hpp`) containing struct/class definitions.
- **Normalization**: The process of transforming a name string by removing all underscores (`_`) and converting all characters to uppercase for strict comparison.
  - Example: `mask_group_id` -> `MASKGROUPID`
- **Matching**: The process of linking a Proto message/field to a CppHeader struct/field based on their Normalized names.

## 3. Requirements

### 3.1 Functional Requirements
1.  **Input Parsing**:
    - Recursively scan a provided `working-path` for all `.proto` files and C++ header files.
    - **Parsing Strategy**: A tokenizer + recursive descent AST parser pipeline is used for each language. The tokenizer performs single-pass lexical analysis (stripping comments and preprocessor directives), the recursive descent parser builds a typed AST, and a transformer converts AST nodes into the shared data model. This approach cleanly handles nested structures, type aliases, and anonymous definitions.
    - **C++ Header Style Support**: The C++ parser supports legacy C-style header conventions in addition to C++ idioms. The four supported patterns are:
        - **String Fields (`char field[N]`)**: A `char` array declaration (e.g., `char venue[64];`) is parsed as a scalar string field, **not** as a repeated field. The array size is discarded. Maps to `string` in Proto matching and `String` in Java.
        - **Repeated Fields (C-style arrays)**: A non-char array declaration (e.g., `TradeFee fees[20];` or `int scores[10];`) is treated as a repeated field. The array size is discarded. Maps to `repeated T` in Proto matching and `List<T>` in Java. This is the C-style equivalent of `std::vector<T>`, which is also supported.
        - **Struct Definitions (C Anonymous Structs)**: Two forms are supported:
            - **Top-level anonymous typedef**: `typedef struct { ... } Name;` — the struct takes the typedef name as its identifier.
            - **Inline anonymous struct**: `struct { ... } fieldName;` — nested inside a parent struct, the anonymous struct is auto-named by capitalizing the first letter of the field name (e.g., field `traderInfo` produces a synthetic struct named `TraderInfo`).
        - **Type Aliases (`typedef`)**: Supported forms:
            1. Scalar alias: `typedef int UserId;` — `UserId` resolves to `int` during type matching.
            2. Struct alias: `typedef struct TradeOrder TradeAlias;` — `TradeAlias` resolves to `TradeOrder`.
            3. Anonymous typedef struct: `typedef struct { ... } Name;` (covered above).
            4. Chained aliases: `typedef int A; typedef A B;` — resolved recursively with cycle detection; `B` resolves to `int`.
2.  **Mapping Logic**:
    - **Class Matching**: A Proto message maps to a CppHeader struct if their Normalized names are identical.
    - **Field Matching**: A Proto field maps to a CppHeader field if their Normalized names are identical.
    - **Data Types**:
        - **Primitives**: Direct mapping (e.g., `int32` -> `int`). In C++ headers, `char field[N]` maps to `string` in Proto (treated as a C-string, not a repeated char).
        - **Repeated**: `repeated T` in Proto maps to `List<T>` in Java. On the C++ side, both `std::vector<T>` and C-style arrays (`Type field[N]`, where Type is not `char`) are recognized as repeated fields.
        - **Non-Primitive (Nested)**: A field whose type references another message or struct (i.e., any type that is not a scalar primitive). These fields must be matched recursively. This refers to the field's type being non-primitive, not to whether the message definition is structurally nested inside another message.
        - **Type Aliases**: C++ `typedef` aliases are resolved to their base types before matching. Chained aliases (e.g., `typedef int A; typedef A B;`) are resolved recursively. This is transparent to the matching logic — a field typed `UserId` (aliased to `int`) matches a Proto `int32` field normally.
    - **Strict Validation**: **EVERY** field in a mapped Proto message must have a corresponding matched field in the C++ Header. If any field (including nested or repeated ones) is unmatched, the tool must raise a fatal error.
3.  **Code Generation**:
    - **Java DTOs**:
        - Generate a Java class for each matched CppHeader struct.
        - **One Class Per File**: Each generated `.java` file must contain exactly one public class. The file name must match the class name (e.g., `TradeOrder.java` contains `public class TradeOrder`).
        - **Naming**: Class and Field names must **strictly** match the casing found in the C++ Header (e.g., if C++ has `UsErId`, Java must have `UsErId`).
        - **Lombok**: Use `@Getter`, `@Setter`, and `@Builder` attributes. **Do NOT** use `@NoArgsConstructor` or `@AllArgsConstructor`.
    - **Java Mappers**:
        - Generate a Mapper class for each Proto file group.
        - Implement static mapping methods to convert between Proto objects and Java DTOs.
        - **Complex Types**:
            - Recursively call mapping methods for nested objects.
            - Transform lists for repeated fields.
        - Use the Builder pattern for instantiation.
4.  **CLI Interface**:
    - Command: `python -m protoc_adapter --working-path <PATH> --java-package <PACKAGE> [--mapstruct]`
5.  **Output Structure**:
    - Generate `dto` and `mapper` directories under the `working-path`.
    - When `--mapstruct` is enabled, also generate a `mapstruct_mapper` directory (see §3.1.7).
6.  **Rep\* Message Handling**:
    - Proto messages whose names start with `Rep` may contain a field of type `msgHeader`. This field has no C++ counterpart.
    - The tool generates a `WebServiceReplyHeader` DTO in the `dto/` directory with renamed fields derived from the proto `msgHeader` definition: `retCode` → `returnCode`, `msgOwnId` → `returnMessage`. Only these two fields are included; other `msgHeader` fields are excluded.
    - In Rep\* DTOs, the `msgHeader` field type is `WebServiceReplyHeader` (not `msgHeader`).
    - In Rep\* Mappers, the `msgHeader` field uses a builder pattern with renamed sub-field accessors instead of a recursive `proto2Dto` call.
    - Non-Rep messages are unaffected by this logic.
7.  **MapStruct Mapper Generation** (optional, enabled via `--mapstruct`):
    - Generates MapStruct `@Mapper` annotation-based **interfaces** (not concrete classes) as an alternative to the hand-written static mapper classes.
    - **No `@Mapping` annotations**: Field mappings are NOT explicitly listed. Instead, a custom `AccessorNamingStrategy` (MapStruct SPI) resolves all naming mismatches at annotation-processing time.
    - **Custom Naming Strategy** (`ProtobufAccessorNamingStrategy`):
        - **Repeated field renaming**: Proto generates `getFeesList()` for repeated fields. The strategy strips the `List` suffix when the return type is `java.util.List`, producing property name `fees` to match the DTO field.
        - **Proto internal method filtering**: Excludes proto-generated methods that are not user fields — suffix patterns (`OrBuilder`, `OrBuilderList`, `Bytes`, `Count`) and exact base-class methods (`getAllFields`, `getDescriptorForType`, `getUnknownFields`, etc.).
        - **Casing normalization**: Property names are normalized (underscores removed, lowercased) on both source and target types. This overcomes casing differences between proto-generated accessors (e.g., `orderId`) and C++-convention DTO fields (e.g., `orderID`) — both normalize to `orderid`. MapStruct uses these names only for matching; generated code still calls the original methods.
    - **Rep\* Message Handling**: For Rep\* messages with `msgHeader`, a `default` method is generated in the interface that manually maps `msgHeader` to `WebServiceReplyHeader` using the builder pattern with renamed fields. MapStruct auto-discovers this method for type-level conversion.
    - **Output Structure** (all files generated at runtime under `mapstruct_mapper/`; `ProtobufAccessorNamingStrategy.java` and `MAVEN_INTEGRATION.md` are rendered from Jinja2 templates with the `--java-package` value substituted):
        - `{PascalStem}MapStructMapper.java` — one interface per proto file, with `toDto()` method declarations for each matched message.
        - `spi/ProtobufAccessorNamingStrategy.java` — the custom naming strategy class (package declaration uses `--java-package`).
        - `META-INF/services/org.mapstruct.ap.spi.AccessorNamingStrategy` — SPI service registration file (references fully-qualified naming strategy class name).
        - `MAVEN_INTEGRATION.md` — generated step-by-step guide for integrating the output files into an existing Maven project with Lombok, including dependency configuration, annotation processor ordering (`lombok-mapstruct-binding`), and file placement instructions (all paths use `--java-package`).

### 3.2 Non-Functional Requirements
- **Performance**: Efficient text processing.
- **Maintainability**: Clean, modular Python code (separation of Parser, Mapper, and Generator).
- **Robustness**: Must handle complex nested and repeated fields (dozens of fields deep) without crashing or losing context.
- **Dependencies**: Use `uv` for project and dependency management.

## 4. Technical Architecture

### 4.1 Tech Stack
- **Language**: Python 3.10+
- **Project Management**: `uv` (init, add, run).
- **Parsing**:
    - **AST Pipeline**: Each language (Proto and C++) is parsed through a three-stage pipeline: **Tokenizer** (single-pass character scanner producing typed tokens) → **Recursive Descent Parser** (consumes tokens, produces language-specific AST nodes) → **Transformer** (converts AST nodes into the shared `Message`/`Field` models). This approach cleanly separates lexical analysis, syntactic structure, and semantic transformation.
- **Templating**: `Jinja2` for generating Java source code.

### 4.2 Module Design
- `main.py`: Entry point, CLI argument parsing.
- `parser/`:
    - `proto_parser.py`: Entry point for proto parsing (tokenize → parse AST → transform).
    - `proto_ast.py`, `proto_tokenizer.py`, `proto_ast_parser.py`, `proto_transform.py`: AST pipeline for `.proto` files.
    - `cpp_parser.py`: Entry point for C++ header parsing (tokenize → parse AST → transform).
    - `cpp_ast.py`, `cpp_tokenizer.py`, `cpp_ast_parser.py`, `cpp_transform.py`: AST pipeline for C++ headers.
- `matcher.py`:
    - Normalizes names.
    - Recursively matches fields.
    - Validates 100% coverage of proto fields.
- `rep_message_handler.py`:
    - Detects Rep\* messages and strips `msgHeader` fields before matching.
    - Builds synthetic `WebServiceReplyHeader` DTO definition with renamed fields.
    - Injects `WebServiceReplyHeader` field mappings into Rep\* message matches.
- `generator/`:
    - `java_dto_generator.py`: Renders DTOs.
    - `java_mapper_generator.py`: Renders Mappers with recursive logic.
    - `java_mapstruct_generator.py`: Renders MapStruct mapper interfaces, naming strategy, SPI registration, and Maven integration guide.

### 4.3 Data Structures

**Shared model** (output of both parsers after transformation):
```python
@dataclass
class Field:
    original_name: str
    normalized_name: str
    type_name: str
    is_repeated: bool = False
    is_nested: bool = False
    nested_type: Optional['Message'] = None  # Reference to the definition if nested

@dataclass
class Message:
    original_name: str
    normalized_name: str
    fields: List[Field]
    source_file: str
```

**C++ AST nodes** (intermediate representation before transformation):
```python
@dataclass
class CppFieldDecl:
    type_name: str
    field_name: str
    is_vector: bool = False      # std::vector<T> → repeated
    is_char_array: bool = False  # char field[N] → string (not repeated)
    is_array: bool = False       # Type field[N] (non-char) → repeated

@dataclass
class CppAnonymousStructField:
    field_name: str              # Used to derive synthetic struct name
    fields: List[CppFieldDecl]

@dataclass
class CppTypeAlias:
    alias_name: str              # The new name
    existing_type: str           # The original type being aliased
```

## 5. Development Workflow
1.  Initialize project with `uv init`.
2.  Add dependencies (`jinja2`).
3.  **Test-Driven Development (TDD)**: Write tests before implementation for all components.
    - Create test cases for nested/repeated fields.
    - Create test cases for strict C++ matching.
4.  Implement Parsers (TDD approach).
5.  Implement Matcher & Validation logic (TDD approach).
6.  Implement Jinja2 Templates (TDD approach).
7.  Integration Testing.
