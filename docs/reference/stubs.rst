Runtime Stand-ins and Determinism
=================================

The repository ships deterministic examples and tests that do not require a real
pyCycle/OpenMDAO installation for basic scaffolding checks.

Why this exists
---------------

- Local development stays lightweight.
- CI remains deterministic for docs, packaging, and example smoke checks.
- Tool payload contracts can be validated without heavy runtime assets.

What is intentionally simplified
--------------------------------

- Example scripts use lightweight stand-in problem objects.
- Example outputs focus on stable JSON shape and key fields.
- Full-fidelity thermodynamic behavior requires real OpenMDAO/pyCycle installs
  and should be validated in integration environments.
