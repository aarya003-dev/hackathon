# Python Review Guidelines

Style and correctness rules the core review agent applies to Python diffs.

## Style

- Avoid bare `except:` clauses; catch the specific exception types.
- Keep functions small and focused; prefer early returns over deep nesting.
- Do not leave debug `print()` calls in committed code.
- Use `is None` / `is not None` for identity checks instead of `== None`.

## Correctness

- Resolve `TODO` and `FIXME` markers before merging.
- Prefer explicit truthiness over `== True` or `== False` comparisons.
- Guard against division by zero and empty collections before iterating.
- Match file handles with a `with` statement so they are always closed.

## Suggestions

Every finding should include a concrete suggestion: the exact replacement code
or the specific fix, not a generic "fix this".
