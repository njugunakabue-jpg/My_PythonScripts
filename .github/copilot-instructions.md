# Copilot / AI Contributor Instructions

These notes aim to get an AI coding agent productive quickly in this repository.

- **Big picture**: this repository is a single-app Tkinter-based tool implemented in `Golf_Calculator_copilot_v12.py`. The UI classes are `PlayerRow` (per-player widgets/state) and `BigBoySkinsApp` (application glue, UI, import/export, and main logic).

- **Core data flow**:
  - UI widgets -> `collect_data()` produces `pars` and `player` dicts (used to build a `pandas.DataFrame`).
  - Business logic lives in `_compute_skins_and_payouts(pars, players_df)` which returns skins, payouts, and hole-level results.
  - `export_to_excel()` formats workbook with `openpyxl` (sheet layout, colors, `Export Summary` sheet) and `import_from_excel()` attempts to re-create UI state from that sheet layout.

- **Important constants & conventions**:
  - `HOLES = 18` is assumed throughout. Many offsets rely on this.
  - Column/grid mapping in the UI and export uses an offset pattern: Name=col0, HCP=col1, Included=col2, holes start at `col = 3 + i if i < 9 else 4 + i`.
  - Excel export uses `col_off = 1` (start at column B). Par row and Stroke Index rows are written immediately below headers.
  - `MAX_PLAYERS`, `MAX_HOLE_SCORE` are enforced in UI code — preserve these checks if you change player logic.

- **Excel import/export compatibility** (CRITICAL when changing either side):
  - `import_from_excel()` searches the sheet for a header cell containing `name` or `player` in the first 50 rows × 10 columns. It expects hole columns to start at `header_col + 3`.
  - Optional rows supported: a `Par` row (label `Par`) and a `Stroke Index` row (labels `Stroke Index`, `stroke_index`, or `si`) immediately after the header.
  - The `Export Summary` sheet (if present) is parsed for keys: case-insensitive matches like `per-skin`, `total purse`, `carryover`, `use net`, `split ties`, `course`, `date`. Keep these names or update parsing logic together.
  - If you modify export column indices, update `import_from_excel()` to match. Tests should verify round-trip (export -> import) behavior.

- **Dependencies seen in code**: `pandas`, `openpyxl`, `tkcalendar`, plus standard `tkinter`/`ttk`. Keep dependency list in sync if you add libs (no `requirements.txt` present currently).

- **Packaging & resource handling**:
  - `get_app_icon_path()` checks for PyInstaller (`sys.frozen` and `sys._MEIPASS`). If adding resources, follow this pattern so the app works both run-from-source and when frozen.

- **UI / threading / event patterns**:
  - The app frequently uses `try/except` and `messagebox` for user-facing errors instead of propagating exceptions — follow this UX pattern when modifying UI code.
  - Mousewheel binding uses `bind_all('<MouseWheel>', ...)` on the player canvas. Beware side-effects if adding other global bindings.

- **Suggested targets for tests** (no tests currently present):
  - Unit tests for `_compute_skins_and_payouts` (pure logic, many edge cases around carryover/split/bonuses).
  - Round-trip test for `export_to_excel` -> `import_from_excel` using an in-memory workbook (openpyxl) to ensure format compatibility.

- **Files to inspect for context**:
  - `Golf_Calculator_copilot_v12.py` — main application and logic.
  - `README.md` — short project description.

- **When submitting changes**:
  - Preserve Excel layout assumptions or update both import and export together.
  - When changing UI grid indices (columns), adjust `PlayerRow` grid placement, `export_to_excel` column mapping, and `import_from_excel` parsing logic.
  - Keep `HOLES = 18` in mind — any change to hole count is repository-wide.

If anything important is missing (CI, preferred packaging, tests, or alternate Excel templates you use), tell me and I will update this guidance.
