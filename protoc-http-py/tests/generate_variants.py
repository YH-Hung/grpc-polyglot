import os
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "out_test"
PROTO_DIR = REPO_ROOT / "proto"

# Ensure package import works
sys.path.insert(0, str(REPO_ROOT))
from protoc_http_py.main import generate, generate_directory_with_shared_utilities  # type: ignore


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    base = p.with_suffix("")
    ext = p.suffix
    i = 1
    while True:
        cand = Path(f"{base}.{i}{ext}")
        if not cand.exists():
            return cand
        i += 1


def find_proto_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".proto"):
                files.append(Path(dp) / fn)
    files.sort(key=lambda p: str(p).lower())
    return files


def rename_current_outputs_to_default():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for vb in sorted(OUT_DIR.glob("*.vb")):
        # Skip files that already have a known variant suffix
        if vb.name.endswith(".default.vb") or vb.name.endswith(".net40hwr.vb"):
            continue
        stem = vb.stem
        target = vb.parent / f"{stem}.default.vb"
        target = unique_path(target)
        vb.rename(target)
        print(f"Renamed: {vb.name} -> {target.name}")


def generate_and_suffix(mode: str, suffix: str):
    protos = find_proto_files(PROTO_DIR / "simple") + find_proto_files(PROTO_DIR / "complex")
    if not protos:
        raise RuntimeError("No .proto files found under proto/")

    # Use new directory-based generation with shared utilities
    out_paths = generate_directory_with_shared_utilities([str(p) for p in protos], str(OUT_DIR), None, compat=mode)

    # Rename all generated files with suffix
    for out_path in out_paths:
        out = Path(out_path)
        stem = out.stem
        target = out.parent / f"{stem}.{suffix}.vb"
        target = unique_path(target)
        out.replace(target)
        print(f"Generated ({mode}): {target.name}")


def main():
    print(f"Repo root: {REPO_ROOT}")
    print(f"Output dir: {OUT_DIR}")
    # Optionally rename any pre-existing VB files to .default.vb to avoid overwrites
    rename_current_outputs_to_default()
    # Generate default (modern HttpClient + async) as .default.vb
    generate_and_suffix(None, "default")
    # Generate variant modes
    generate_and_suffix("net40hwr", "net40hwr")
    # Summary
    print("\nFinal out_test listing:")
    for vb in sorted(OUT_DIR.glob("*.vb")):
        print(f" - {vb.name}")


if __name__ == "__main__":
    main()
