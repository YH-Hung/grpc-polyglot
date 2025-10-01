from pathlib import Path
import os
import sys
import subprocess

# Allow running from repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from protoc_http_py.main import generate


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_generate_default_async(tmp_path: Path):
    proto = REPO_ROOT / "proto" / "simple" / "helloworld.proto"
    out_dir = tmp_path / "out_default"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(generate(str(proto), str(out_dir), None))
    text = read(out_path)

    # HttpClient/async-based client expected
    assert "Imports System.Net.Http" in text
    assert "Imports System.Threading" in text
    assert "Imports System.Threading.Tasks" in text
    assert "Private Async Function PostJsonAsync" in text
    assert "Public Function SayHelloAsync(" in text
    assert "/helloworld/say-hello/v1" in text
    assert "/helloworld/say-hello/v2" in text


def test_generate_net45_async(tmp_path: Path):
    proto = REPO_ROOT / "proto" / "simple" / "helloworld.proto"
    out_dir = tmp_path / "out_net45"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(generate(str(proto), str(out_dir), None, compat="net45"))
    text = read(out_path)

    # HttpClient/async-based client expected
    assert "Imports System.Net.Http" in text
    assert "Imports System.Threading" in text
    assert "Imports System.Threading.Tasks" in text
    assert "Private Async Function PostJsonAsync" in text
    assert "Public Function SayHelloAsync(" in text
    # NameOf is allowed in net45 path
    assert "NameOf(http)" in text
    assert "NameOf(request)" in text




def test_generate_net40hwr_sync(tmp_path: Path):
    proto = REPO_ROOT / "proto" / "simple" / "helloworld.proto"
    out_dir = tmp_path / "out_net40hwr"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(generate(str(proto), str(out_dir), None, compat="net40hwr"))
    text = read(out_path)

    # Synchronous HttpWebRequest-based client expected
    assert "Imports System.Net" in text
    assert "Imports System.IO" in text
    assert "HttpWebRequest" in text
    assert "HttpClient" not in text
    assert "Async Function" not in text
    assert "CancellationToken" not in text
    # Method names are not suffixed with Async in net40hwr mode
    assert "Public Function SayHello(" in text
    assert "/helloworld/say-hello/v1" in text


def test_cli_alias_net40(tmp_path: Path):
    # Verify the CLI alias --net40 maps to net40hwr output
    proto = REPO_ROOT / "proto" / "simple" / "helloworld.proto"
    out_dir = tmp_path / "out_cli_net40"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "protoc_http_py.main",
        "--proto",
        str(proto),
        "--out",
        str(out_dir),
        "--net40",
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"CLI failed: {res.stdout}\n{res.stderr}"

    out_path = out_dir / "helloworld.vb"
    assert out_path.exists()
    text = read(out_path)

    # Expect same as net40hwr (synchronous HttpWebRequest-based)
    assert "Imports System.Net" in text
    assert "Imports System.IO" in text
    assert "HttpWebRequest" in text
    assert "HttpClient" not in text
    assert "Async Function" not in text
    assert "CancellationToken" not in text
    assert "Public Function SayHello(" in text
