"""Recursive descent parser for C++ header files.

Consumes a token stream from cpp_tokenizer and produces C++ AST nodes.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .cpp_ast import (
    CppAnonymousStructField,
    CppFieldDecl,
    CppHeader,
    CppStruct,
    CppTypeAlias,
)
from .cpp_tokenizer import CppToken, CppTokenType

_ACCESS_SPECIFIERS = {"public", "private", "protected"}
_VECTOR_TYPES = {"vector", "list"}


class CppParseError(Exception):
    def __init__(self, message: str, token: CppToken | None = None):
        if token:
            super().__init__(f"Line {token.line}:{token.col}: {message}")
        else:
            super().__init__(message)


class CppParser:
    """Recursive descent parser for C++ header files."""

    def __init__(self, tokens: List[CppToken]):
        self._tokens = tokens
        self._pos = 0

    # -- public API --

    def parse(self) -> CppHeader:
        """Parse the full token stream into a CppHeader AST."""
        type_aliases: List[CppTypeAlias] = []
        structs: List[CppStruct] = []

        while not self._at_end():
            tt = self._peek().type

            if tt == CppTokenType.TYPEDEF:
                result = self._parse_typedef()
                if isinstance(result, CppTypeAlias):
                    type_aliases.append(result)
                elif isinstance(result, CppStruct):
                    structs.append(result)
            elif tt == CppTokenType.STRUCT:
                struct = self._parse_top_level_struct()
                if struct is not None:
                    structs.append(struct)
            else:
                self._advance()

        return CppHeader(type_aliases=type_aliases, structs=structs)

    # -- typedef parsing --

    def _parse_typedef(self) -> CppTypeAlias | CppStruct | None:
        """Parse a typedef declaration.

        Handles four forms:
        1. typedef struct Name { ... };    -> CppStruct (named)
        2. typedef struct { ... } Name;    -> CppStruct (anonymous typedef)
        3. typedef struct A B;             -> CppTypeAlias (struct alias)
        4. typedef Type Name;              -> CppTypeAlias (simple alias)
        """
        self._expect(CppTokenType.TYPEDEF)

        if self._peek().type == CppTokenType.STRUCT:
            self._advance()  # consume STRUCT

            if self._peek().type == CppTokenType.LBRACE:
                # Form 2: typedef struct { ... } Name;
                self._advance()  # consume LBRACE
                fields, nested = self._parse_struct_body()
                self._expect(CppTokenType.RBRACE)
                typedef_name = self._expect(CppTokenType.IDENT).value
                self._expect(CppTokenType.SEMICOLON)
                return CppStruct(
                    name=None,
                    is_anonymous_typedef=True,
                    typedef_name=typedef_name,
                    fields=fields,
                    nested_structs=nested,
                )

            if self._peek().type == CppTokenType.IDENT:
                name = self._advance().value

                if self._peek().type == CppTokenType.LBRACE:
                    # Form 1: typedef struct Name { ... };
                    self._advance()  # consume LBRACE
                    fields, nested = self._parse_struct_body()
                    self._expect(CppTokenType.RBRACE)
                    self._expect(CppTokenType.SEMICOLON)
                    return CppStruct(
                        name=name,
                        fields=fields,
                        nested_structs=nested,
                    )

                if self._peek().type == CppTokenType.IDENT:
                    # Form 3: typedef struct A B;
                    alias_name = self._advance().value
                    self._expect(CppTokenType.SEMICOLON)
                    return CppTypeAlias(
                        new_name=alias_name,
                        existing_type=name,
                        is_struct_alias=True,
                    )

                # Unknown pattern, skip to semicolon
                self._skip_to_semicolon()
                return None

            # Unknown pattern after typedef struct
            self._skip_to_semicolon()
            return None

        # Form 4: typedef Type Name;
        type_name = self._parse_simple_type_ref()
        if self._peek().type == CppTokenType.IDENT:
            alias_name = self._advance().value
            self._expect(CppTokenType.SEMICOLON)
            return CppTypeAlias(new_name=alias_name, existing_type=type_name)

        self._skip_to_semicolon()
        return None

    # -- struct parsing --

    def _parse_top_level_struct(self) -> CppStruct | None:
        """Parse a top-level struct definition: struct Name { ... };"""
        self._expect(CppTokenType.STRUCT)

        if self._peek().type != CppTokenType.IDENT:
            # Anonymous struct at top level without typedef — skip
            self._skip_to_matching_brace()
            self._consume_if(CppTokenType.SEMICOLON)
            return None

        name = self._advance().value

        if self._peek().type != CppTokenType.LBRACE:
            # Forward declaration: struct Foo; — skip
            self._skip_to_semicolon()
            return None

        self._advance()  # consume LBRACE
        fields, nested = self._parse_struct_body()
        self._expect(CppTokenType.RBRACE)
        self._expect(CppTokenType.SEMICOLON)

        return CppStruct(name=name, fields=fields, nested_structs=nested)

    def _parse_struct_body(
        self,
    ) -> Tuple[
        List[Union[CppFieldDecl, CppAnonymousStructField]],
        List[CppStruct],
    ]:
        """Parse the contents between { and } of a struct."""
        fields: List[Union[CppFieldDecl, CppAnonymousStructField]] = []
        nested_structs: List[CppStruct] = []

        while not self._at_end() and self._peek().type != CppTokenType.RBRACE:
            tt = self._peek().type

            # Handle struct keyword inside body
            if tt == CppTokenType.STRUCT:
                next_tt = self._peek_at(1).type
                if next_tt == CppTokenType.LBRACE:
                    # Anonymous nested struct: struct { ... } fieldName;
                    fields.append(self._parse_anonymous_struct_field())
                elif next_tt == CppTokenType.IDENT:
                    # Named nested struct: struct Name { ... };
                    nested_structs.append(self._parse_named_nested_struct())
                else:
                    self._advance()
                continue

            # Skip typedef inside struct body
            if tt == CppTokenType.TYPEDEF:
                self._skip_to_semicolon()
                continue

            # Skip access specifiers: public: / private: / protected:
            if tt == CppTokenType.IDENT and self._peek().value in _ACCESS_SPECIFIERS:
                if self._peek_at(1).type == CppTokenType.COLON:
                    self._advance()  # IDENT
                    self._advance()  # COLON
                    continue

            # Try to parse a field declaration
            field = self._try_parse_field_decl()
            if field is not None:
                fields.append(field)
            else:
                self._advance()

        return fields, nested_structs

    def _parse_anonymous_struct_field(self) -> CppAnonymousStructField:
        """Parse: struct { <fields> } fieldName;"""
        self._expect(CppTokenType.STRUCT)
        self._expect(CppTokenType.LBRACE)
        inner_fields, _ = self._parse_struct_body()
        self._expect(CppTokenType.RBRACE)
        field_name = self._expect(CppTokenType.IDENT).value
        self._expect(CppTokenType.SEMICOLON)
        return CppAnonymousStructField(field_name=field_name, fields=inner_fields)

    def _parse_named_nested_struct(self) -> CppStruct:
        """Parse: struct Name { ... }; inside a parent struct body."""
        self._expect(CppTokenType.STRUCT)
        name = self._expect(CppTokenType.IDENT).value

        if self._peek().type != CppTokenType.LBRACE:
            # Forward declaration inside struct — skip
            self._skip_to_semicolon()
            return CppStruct(name=name)

        self._advance()  # consume LBRACE
        fields, nested = self._parse_struct_body()
        self._expect(CppTokenType.RBRACE)
        self._expect(CppTokenType.SEMICOLON)
        return CppStruct(name=name, fields=fields, nested_structs=nested)

    # -- field declaration parsing --

    def _try_parse_field_decl(self) -> CppFieldDecl | None:
        """Try to parse a field declaration. Returns None if not a valid field."""
        saved = self._pos

        # Case: char field (CHAR keyword token)
        if self._peek().type == CppTokenType.CHAR:
            self._advance()  # consume CHAR
            if self._peek().type != CppTokenType.IDENT:
                self._pos = saved
                return None
            field_name = self._advance().value

            if self._peek().type == CppTokenType.LBRACKET:
                # char name[SIZE]; -> string field
                self._advance()  # [
                self._consume_if(CppTokenType.NUMBER)  # optional size
                self._expect(CppTokenType.RBRACKET)  # ]
                self._expect(CppTokenType.SEMICOLON)
                return CppFieldDecl(
                    type_name="char",
                    field_name=field_name,
                    is_char_array=True,
                )
            elif self._peek().type == CppTokenType.SEMICOLON:
                self._advance()
                return CppFieldDecl(type_name="char", field_name=field_name)

            self._pos = saved
            return None

        # Parse type specifier (possibly std::qualified, possibly vector<T>)
        type_result = self._try_parse_type_spec()
        if type_result is None:
            return None

        type_name, is_vector, inner_type = type_result

        if is_vector:
            # vector<T> fieldName;
            if self._peek().type != CppTokenType.IDENT:
                self._pos = saved
                return None
            field_name = self._advance().value
            self._expect(CppTokenType.SEMICOLON)
            return CppFieldDecl(
                type_name=inner_type,
                field_name=field_name,
                is_vector=True,
            )

        # Simple or array field: Type name[SIZE]; or Type name;
        if self._peek().type != CppTokenType.IDENT:
            self._pos = saved
            return None
        field_name = self._advance().value

        if self._peek().type == CppTokenType.LBRACKET:
            # Type name[SIZE];
            self._advance()  # [
            self._consume_if(CppTokenType.NUMBER)  # optional size
            self._expect(CppTokenType.RBRACKET)  # ]
            self._expect(CppTokenType.SEMICOLON)
            return CppFieldDecl(
                type_name=type_name,
                field_name=field_name,
                is_array=True,
            )

        if self._peek().type == CppTokenType.SEMICOLON:
            self._advance()
            return CppFieldDecl(type_name=type_name, field_name=field_name)

        # Not a recognizable field pattern
        self._pos = saved
        return None

    def _try_parse_type_spec(
        self,
    ) -> Tuple[str, bool, str] | None:
        """Parse a type specifier.

        Returns (type_name, is_vector, inner_type) or None.
        For vector/list types: is_vector=True, inner_type is the element type.
        For simple types: is_vector=False, inner_type is empty string.
        Handles std:: prefix by stripping it.
        """
        if self._peek().type != CppTokenType.IDENT:
            return None

        # Check for std:: prefix
        has_std = False
        if (
            self._peek().value == "std"
            and self._peek_at(1).type == CppTokenType.COLONCOLON
        ):
            has_std = True
            self._advance()  # std
            self._advance()  # ::

        if self._peek().type != CppTokenType.IDENT:
            return None

        type_name = self._advance().value

        # Check for vector/list template
        if type_name in _VECTOR_TYPES and self._peek().type == CppTokenType.LANGLE:
            self._advance()  # <
            inner = self._parse_inner_type()
            self._expect(CppTokenType.RANGLE)  # >
            return (type_name, True, inner)

        return (type_name, False, "")

    def _parse_inner_type(self) -> str:
        """Parse the type inside angle brackets, stripping std:: prefix."""
        if (
            self._peek().type == CppTokenType.IDENT
            and self._peek().value == "std"
            and self._peek_at(1).type == CppTokenType.COLONCOLON
        ):
            self._advance()  # std
            self._advance()  # ::
        return self._expect(CppTokenType.IDENT).value

    def _parse_simple_type_ref(self) -> str:
        """Parse a possibly namespace-qualified type name: [std::]IDENT."""
        if (
            self._peek().type == CppTokenType.IDENT
            and self._peek().value == "std"
            and self._peek_at(1).type == CppTokenType.COLONCOLON
        ):
            self._advance()  # std
            self._advance()  # ::
            return self._expect(CppTokenType.IDENT).value

        if self._peek().type == CppTokenType.CHAR:
            return self._advance().value

        return self._expect(CppTokenType.IDENT).value

    # -- skip / recovery helpers --

    def _skip_to_semicolon(self) -> None:
        """Skip tokens until (and including) the next semicolon."""
        while not self._at_end():
            tok = self._advance()
            if tok.type == CppTokenType.SEMICOLON:
                return

    def _skip_to_matching_brace(self) -> None:
        """Skip tokens including a matched { ... } block."""
        if self._peek().type != CppTokenType.LBRACE:
            return
        self._advance()  # {
        depth = 1
        while not self._at_end() and depth > 0:
            tok = self._advance()
            if tok.type == CppTokenType.LBRACE:
                depth += 1
            elif tok.type == CppTokenType.RBRACE:
                depth -= 1

    # -- token helpers --

    def _peek(self) -> CppToken:
        return self._tokens[self._pos]

    def _peek_at(self, offset: int) -> CppToken:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]  # EOF

    def _advance(self) -> CppToken:
        tok = self._tokens[self._pos]
        if tok.type != CppTokenType.EOF:
            self._pos += 1
        return tok

    def _expect(self, expected: CppTokenType) -> CppToken:
        tok = self._peek()
        if tok.type != expected:
            raise CppParseError(
                f"Expected {expected.name}, got {tok.type.name} ({tok.value!r})",
                tok,
            )
        return self._advance()

    def _consume_if(self, expected: CppTokenType) -> CppToken | None:
        if self._peek().type == expected:
            return self._advance()
        return None

    def _at_end(self) -> bool:
        return self._tokens[self._pos].type == CppTokenType.EOF
