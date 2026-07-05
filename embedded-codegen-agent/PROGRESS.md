# Progress log

Append a new entry every session. Don't delete old entries — this is the
history of decisions, not just current state. If you (or a Claude session)
need to know "why did we do it this way," it should be answerable here.

---

## 2026-07-05 — Session 1: project kickoff
- Defined the goal: agent that generates Arduino/RPi code from a structured
  spec, grounded in real hardware reference data, with a compile-check loop
  and mandatory human review before flashing.
- Decided on architecture: spec -> hardware_lookup -> codegen -> compile_check
  (loop on error) -> human review -> flash. Human review step is a hard
  safety boundary, not optional.
- Scaffolded repo structure, CLAUDE.md, and stub source files.
- Next session: implement hardware_lookup.py, seed 2-3 real board reference
  docs, wire up codegen.py to an actual LLM API call.
