"""Root-level pytest gate: collect only orch's suite.

Without this file `detect_test_command` finds nothing at the repo root and an
orch task targeting this repo fails with `no_test_command`. The ignore list
keeps accidental `pytest` runs from wandering into the nested sibling repos.
"""

collect_ignore = ["soul-commander", "RecallInfinity", ".playwright-mcp"]
