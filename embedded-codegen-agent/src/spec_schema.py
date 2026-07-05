"""
spec_schema.py
Defines and validates the structured input spec the agent takes.
This is the contract between "what the user asks for" and everything
downstream — keep it strict so codegen.py always gets clean input.
"""
from dataclasses import dataclass, field


@dataclass
class ComponentSpec:
    name: str            # e.g. "DHT22", "PIR motion sensor", "SG90 servo"
    connection: str      # e.g. "digital", "analog", "i2c", "pwm"
    notes: str = ""       # anything spec-specific: "active low", "needs pull-up"


@dataclass
class ProjectSpec:
    board: str                          # must match a key in config/boards.yaml
    goal: str                           # plain-language description of what it should do
    components: list[ComponentSpec] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)  # e.g. "battery powered", "low power mode"

    def validate(self, known_boards: set[str]) -> list[str]:
        """Returns a list of problems; empty list means the spec is valid."""
        problems = []
        if self.board not in known_boards:
            problems.append(
                f"Unknown board '{self.board}'. Known boards: {sorted(known_boards)}"
            )
        if not self.goal.strip():
            problems.append("goal must not be empty")
        if not self.components:
            problems.append("at least one component is required")
        return problems
