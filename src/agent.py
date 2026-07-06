"""
agent.py
Orchestrates: spec -> codegen -> compile_check (retry loop) -> human review.
This is intentionally a plain loop, not a framework, while the project is
young — add structure only once this stops being enough.
"""
from spec_schema import ProjectSpec, ComponentSpec
from hardware_lookup import get_board_meta, load_board_registry
from codegen import generate_code
from compile_check import compile_arduino_sketch, check_python_syntax

MAX_RETRIES = 3


def run(spec: ProjectSpec) -> str | None:
    known_boards = set(load_board_registry().keys())
    problems = spec.validate(known_boards)
    if problems:
        print("Spec is invalid:")
        for p in problems:
            print(f"  - {p}")
        return None

    board_meta = get_board_meta(spec.board)
    compile_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n--- Generation attempt {attempt} ---")
        code = generate_code(spec, compile_error=compile_error)

        if board_meta["toolchain"] == "arduino-cli":
            success, output = compile_arduino_sketch(code, board_meta["fqbn"])
        else:
            success, output = check_python_syntax(code)

        if success:
            print("Compile check passed.")
            print("\n" + "=" * 60)
            print("REVIEW BEFORE FLASHING — check pin wiring and power levels")
            print("against the hardware reference doc before uploading.")
            print("=" * 60 + "\n")
            print(code)
            return code
        else:
            print(f"Compile check failed:\n{output}")
            compile_error = output

    print(f"\nGave up after {MAX_RETRIES} attempts. Last error:\n{compile_error}")
    return None


if __name__ == "__main__":
    # Example spec — replace with real CLI input parsing later
    example_spec = ProjectSpec(
        board="arduino_uno",
        goal="Blink an LED when a PIR motion sensor detects movement",
        components=[
            ComponentSpec(name="PIR motion sensor", connection="digital", notes="output HIGH on motion"),
            ComponentSpec(name="LED", connection="digital"),
        ],
    )
    run(example_spec)
