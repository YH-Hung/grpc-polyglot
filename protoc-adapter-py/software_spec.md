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
    - **Parsing Strategy**: A brace-counting or stack-based parser is required to correctly identify nested message/struct boundaries and repeated fields. Regex alone is insufficient for nested structures.
2.  **Mapping Logic**:
    - **Class Matching**: A Proto message maps to a CppHeader struct if their Normalized names are identical.
    - **Field Matching**: A Proto field maps to a CppHeader field if their Normalized names are identical.
    - **Data Types**:
        - **Primitives**: Direct mapping (e.g., `int32` -> `int`).
        - **Repeated**: `repeated T` in Proto maps to `List<T>` in Java and corresponding vector/list types in C++.
        - **Nested**: Nested messages or structs must be matched recursively.
    - **Strict Validation**: **EVERY** field in a mapped Proto message must have a corresponding matched field in the C++ Header. If any field (including nested or repeated ones) is unmatched, the tool must raise a fatal error.
3.  **Code Generation**:
    - **Java DTOs**:
        - Generate a Java class for each matched CppHeader struct.
        - **Naming**: Class and Field names must **strictly** match the casing found in the C++ Header (e.g., if C++ has `UsErId`, Java must have `UsErId`).
        - **Lombok**: Use `@Data` and `@Builder` attributes. **Do NOT** use `@NoArgsConstructor` or `@AllArgsConstructor`.
    - **Java Mappers**:
        - Generate a Mapper class for each Proto file group.
        - Implement static mapping methods to convert between Proto objects and Java DTOs.
        - **Complex Types**:
            - Recursively call mapping methods for nested objects.
            - Transform lists for repeated fields.
        - Use the Builder pattern for instantiation.
4.  **CLI Interface**:
    - Command: `python -m protoc_adapter --working-path <PATH> --java-package <PACKAGE>`
5.  **Output Structure**:
    - Generate `dto` and `mapper` directories under the `working-path`.

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
    - **Custom Parser**: Implements state-machine logic to track brace depth `{}` for capturing full struct/message bodies and handling nested definitions.
- **Templating**: `Jinja2` for generating Java source code.

### 4.2 Module Design
- `main.py`: Entry point, CLI argument parsing.
- `parser/`:
    - `proto_parser.py`: Extracts messages/fields using brace counting.
    - `cpp_parser.py`: Extracts structs/fields using brace counting.
- `matcher.py`: 
    - Normalizes names.
    - Recursively matches fields.
    - Validates 100% coverage of proto fields.
- `generator/`:
    - `java_dto_generator.py`: Renders DTOs.
    - `java_mapper_generator.py`: Renders Mappers with recursive logic.

### 4.3 Data Structures
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
