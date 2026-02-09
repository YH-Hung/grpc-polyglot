from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from protoc_adapter.parser.proto_parser import parse_proto_file
from protoc_adapter.parser.cpp_parser import parse_cpp_header
from protoc_adapter.matcher import match_messages, MatchError
from protoc_adapter.generator.java_dto_generator import generate_dtos
from protoc_adapter.generator.java_mapper_generator import generate_mappers
from protoc_adapter.models import Message


def _find_files(working_path: str, extensions: List[str]) -> List[str]:
    """Recursively find files with given extensions under working_path."""
    results = []
    for ext in extensions:
        results.extend(str(p) for p in Path(working_path).rglob(f"*{ext}"))
    return sorted(results)


def run(working_path: str, java_package: str) -> None:
    """Main pipeline: parse, match, generate."""
    # 1. Find input files
    proto_files = _find_files(working_path, [".proto"])
    cpp_files = _find_files(working_path, [".h", ".hpp"])

    if not proto_files:
        print(f"No .proto files found under {working_path}")
        sys.exit(1)
    if not cpp_files:
        print(f"No C++ header files found under {working_path}")
        sys.exit(1)

    print(f"Found {len(proto_files)} proto file(s) and {len(cpp_files)} C++ header file(s)")

    # 2. Parse all files
    all_proto_messages: List[Message] = []
    proto_messages_by_file: Dict[str, List[Message]] = defaultdict(list)

    for pf in proto_files:
        messages = parse_proto_file(pf)
        all_proto_messages.extend(messages)
        proto_messages_by_file[pf] = messages
        print(f"  Parsed {pf}: {len(messages)} message(s)")

    all_cpp_messages: List[Message] = []
    for cf in cpp_files:
        messages = parse_cpp_header(cf)
        all_cpp_messages.extend(messages)
        print(f"  Parsed {cf}: {len(messages)} struct(s)")

    # 3. Match
    try:
        all_matches = match_messages(all_proto_messages, all_cpp_messages)
    except MatchError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    if not all_matches:
        print("No matching proto/C++ message pairs found.")
        sys.exit(0)

    print(f"Matched {len(all_matches)} message pair(s)")

    # 4. Generate DTOs
    dto_files = generate_dtos(all_matches, java_package, working_path)
    for f in dto_files:
        print(f"  Generated DTO: {f}")

    # 5. Generate Mappers (grouped by proto file)
    # Build matches_by_proto: map proto file -> its matches
    matched_proto_names = {m.proto_message.original_name: m for m in all_matches}
    matches_by_proto: Dict[str, List] = {}
    for proto_file, messages in proto_messages_by_file.items():
        file_matches = []
        for msg in messages:
            if msg.original_name in matched_proto_names:
                file_matches.append(matched_proto_names[msg.original_name])
        if file_matches:
            matches_by_proto[proto_file] = file_matches

    mapper_files = generate_mappers(matches_by_proto, java_package, working_path)
    for f in mapper_files:
        print(f"  Generated Mapper: {f}")

    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Protobuf to Java Adapter Tool",
    )
    parser.add_argument(
        "--working-path",
        required=True,
        help="Path to scan for .proto and C++ header files",
    )
    parser.add_argument(
        "--java-package",
        required=True,
        help="Java package name for generated code",
    )

    args = parser.parse_args()
    run(args.working_path, args.java_package)
