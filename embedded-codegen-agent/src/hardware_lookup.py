"""
hardware_lookup.py
Loads the real hardware reference doc for a given board so codegen.py can
ground the LLM's output in facts instead of memory. This is the single
highest-leverage file in the project for reliability — do not skip it or
let codegen.py fall back to generating without this context.
"""
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BOARDS_CONFIG = PROJECT_ROOT / "config" / "boards.yaml"


def load_board_registry() -> dict:
    with open(BOARDS_CONFIG) as f:
        return yaml.safe_load(f)["boards"]


def get_reference_text(board_key: str) -> str:
    """Returns the full reference doc text for a board, or raises if missing."""
    registry = load_board_registry()
    if board_key not in registry:
        raise ValueError(f"Unknown board '{board_key}'. Known: {sorted(registry)}")

    ref_path = PROJECT_ROOT / registry[board_key]["reference_doc"]
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference doc missing for '{board_key}': expected at {ref_path}. "
            f"Add it before generating code for this board."
        )
    return ref_path.read_text()


def get_board_meta(board_key: str) -> dict:
    """Returns the boards.yaml entry (fqbn, logic level, toolchain, etc.)."""
    return load_board_registry()[board_key]
