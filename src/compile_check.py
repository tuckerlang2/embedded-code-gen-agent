"""
compile_check.py
Runs a headless compile of generated code, no hardware required. This is
the cheap automated verification step that catches syntax/type errors
before a human ever needs to look at the code.
"""
import subprocess
import tempfile
from pathlib import Path


def compile_arduino_sketch(code: str, fqbn: str) -> tuple[bool, str]:
    """
    Writes `code` to a temp sketch folder and compiles it with arduino-cli.
    Returns (success, output). Requires arduino-cli installed and on PATH,
    with the relevant board core already installed
    (`arduino-cli core install arduino:avr` etc.)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        sketch_dir = Path(tmpdir) / "sketch"
        sketch_dir.mkdir()
        # arduino-cli requires the .ino file to match its parent folder name
        sketch_file = sketch_dir / "sketch.ino"
        sketch_file.write_text(code, encoding="utf-8")

        result = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", fqbn, str(sketch_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output


def check_python_syntax(code: str) -> tuple[bool, str]:
    """For Raspberry Pi projects: a basic syntax check, no hardware needed."""
    try:
        compile(code, "<generated>", "exec")
        return True, "OK"
    except SyntaxError as e:
        return False, str(e)