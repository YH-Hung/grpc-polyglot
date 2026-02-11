"""AST node definitions for C++ header files."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class CppTypeAlias:
    """typedef <existing_type> <new_name>; or typedef struct <A> <B>;"""

    new_name: str
    existing_type: str
    is_struct_alias: bool = False


@dataclass
class CppFieldDecl:
    """A field declaration inside a struct."""

    type_name: str
    field_name: str
    is_vector: bool = False
    is_char_array: bool = False
    is_array: bool = False


@dataclass
class CppAnonymousStructField:
    """struct { ... } fieldName; — an anonymous nested struct used as a field."""

    field_name: str
    fields: List[Union[CppFieldDecl, CppAnonymousStructField]] = field(
        default_factory=list
    )


@dataclass
class CppStruct:
    """A struct definition (named, typedef-named, or anonymous-typedef)."""

    name: Optional[str] = None
    is_anonymous_typedef: bool = False
    typedef_name: Optional[str] = None
    fields: List[Union[CppFieldDecl, CppAnonymousStructField]] = field(
        default_factory=list
    )
    nested_structs: List[CppStruct] = field(default_factory=list)


@dataclass
class CppHeader:
    """Top-level parsed representation of a C++ header file."""

    type_aliases: List[CppTypeAlias] = field(default_factory=list)
    structs: List[CppStruct] = field(default_factory=list)
