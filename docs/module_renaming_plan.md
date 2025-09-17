# Module Renaming Plan (Design)

Goal: Gradually rename top-level directories `Models/`, `Tools/`, and `Toolsets/` to PEP 8 compliant snake_case: `models/`, `tools/`, `toolsets/` without breaking existing imports or tests. Maintain backward compatibility for at least one minor release cycle.

## Rationale
- Consistency with Python packaging conventions (PEP 8).
- Easier auto-completion and expectation for new contributors.
- Avoid mixed-case directory names causing issues on case-insensitive filesystems.

## Scope (Phase Breakdown)
1. Preparation (current)
   - Add this plan doc.
   - Inventory public import surfaces used by code/tests: e.g. `from Models.provider_config import ...`, `from Tools.search_tool import ...`, `from Toolsets.common_agent_toolset import ...`.
2. Introduce shim packages
   - Create new packages `models/`, `tools/`, `toolsets/`.
   - Move (git mv) one directory at a time (`Models` -> `models`).
   - Inside old directory name path, leave an `__init__.py` with deprecation warnings re-exporting symbols (or better: keep stub package that imports from new path).
   - Update internal imports to new lowercase paths.
3. Deprecation window
   - On import of legacy module (e.g. `Models.provider_config`) emit `DeprecationWarning` advising to switch to `models.provider_config`.
   - Document in README migration section.
4. Removal
   - After at least one release (or timebox), remove legacy shim packages.

## Compatibility Strategy
- Use runtime import redirection in legacy `__init__.py`:
  ```python
  import warnings
  from models.provider_config import *  # noqa
  warnings.warn("Import 'Models' is deprecated; use 'models' instead.", DeprecationWarning, stacklevel=2)
  ```
- Avoid wildcard re-export if performance or namespace pollution becomes a concern; list selected symbols explicitly.

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Partial rename breaks tests | High | Rename one directory per PR; run full suite |
| External scripts rely on old case | Medium | Provide deprecation period + clear warning |
| Circular imports after move | Low | Perform grep to update all internal references atomically |
| Case-insensitive FS conflicts | Low | Use `git mv Models _Models_tmp && git mv _Models_tmp models` if needed |

## Tooling / Validation
- Add a CI check to forbid new imports starting with capitalized `Models`, `Tools`, `Toolsets` after migration period.
- Optionally add a script `scripts/check_imports.py` scanning for forbidden patterns.

## Step-by-Step Execution (Detailed)
1. Create `models/` directory and move `Models/*.py`.
2. Add legacy `Models/__init__.py` shim (only `__init__.py` remains in old dir).
3. Update all imports (`grep -R "from Models" -n`).
4. Run tests, fix any breakages.
5. Repeat for `Tools/` -> `tools/` (special care: tests import from `Tools.search_tool`).
6. Repeat for `Toolsets/` -> `toolsets/`.
7. Add deprecation section to README.
8. After adoption period, remove uppercase directories entirely.

## Deprecation Messaging
- Emit `DeprecationWarning` (not `UserWarning`) so users can opt-in visibility with `-W default`.
- README snippet:
  > The directories `Models/`, `Tools/`, and `Toolsets/` have been renamed to `models/`, `tools/`, and `toolsets/`. Update imports accordingly. Legacy imports will be removed in a future release.

## Acceptance Criteria
- Tests pass after each phase.
- No direct `from Models.` style imports remain internally post-phase.
- Deprecation warning fires exactly once per import location.

## Out of Scope
- Renaming CLI package or other existing snake_case modules.
- Refactoring internal APIs of modules being moved.

## Future Enhancements
- Auto-generate tool index documentation from `tools/` contents.
- Add type-check enforcement once migration complete.

---
Prepared: 2025-09-17