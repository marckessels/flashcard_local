# StudyFlash Local — Maintenance & Extension Guide

Read `docs/ARCHITECTURE.md` first for the data model and execution model.

## Setup and running

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Or double-click `start_studyflash.bat` once `.venv` exists.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
```

- Last verified 19 Oct 2026: 6 tests pass on Python 3.13.1, Streamlit 1.66.0,
  streamlit-hotkeys 0.6.0 (~8 s).
- `AppTest` tests copy `app.py`, `vocabulary.py` and `vocabulary_ui.py` into a
  temp folder, so they run against a fresh DB and **without**
  `shared_decks.json` and the example CSV (unless the test writes its own
  `shared_decks.json`). With no bundled files the app shows only the "Demo"
  deck, which is why `test_app_workflow_and_existing_study` expects 2 decks.
- **If you add a new Python module that the app imports, add it to the copy
  list in every `AppTest` test**, or those tests fail with `ImportError`.
- Tests find widgets by `key` or by Dutch label. Renaming a label or key breaks
  tests; update both together.
- Expected noise: "missing ScriptRunContext", `ResourceWarning: unclosed
  database`, and the `use_container_width` deprecation warning.
- Update `TEST_RESULTS.md` (Dutch) after a meaningful test run.

## Conventions

- UI strings in Dutch; identifiers and comments in English.
- `vocabulary.py` stays free of Streamlit so it can be unit-tested. Put new
  pure logic there (or in another Streamlit-free module), UI in a `*_ui.py`.
- Raise `ValueError` with a Dutch, user-facing message for invalid input; the
  UI shows `str(error)` in `st.error`. Validate fully before saving — imports
  are all-or-nothing.
- Always `str()` card ids before using them in SQL or comparisons.
- After any change to a deck's cards or metadata: mutate the dict in
  `st.session_state.data`, call `save_shared_deck(deck_dict)`, then `st.rerun()`.
- Give each feature its own session-state key prefix and unique widget keys.
- Commit after each DB write (the code calls `CONN.commit()` everywhere).

## Recipes

### Add a new screen
1. Add the label to the `screen` radio list in `app.py`.
2. Add an `if screen == "...":` block. Keep heavy work inside the branch so
   other screens stay fast. For a sizeable screen, create `<name>_ui.py` with a
   `render(...)` function and import it lazily inside the branch (as Woordjes
   does), passing `st.session_state.data`, `deck`, `user`, `CONN`,
   `save_shared_deck`.
3. If it needs SM-2 rows, add the label to the `ensure_progress` condition
   right after the radio.
4. If interactions should not rerun the whole page, wrap the interactive part
   in `@st.fragment` and use `on_click` callbacks.
5. Add the new module to the `AppTest` copy lists and add a test that switches
   to the screen and asserts `not at.exception`.

### Add a table or column
- New table: `CREATE TABLE IF NOT EXISTS` in `init_db()` (preferred), keyed on
  `(user, deck, card_id, …)` to match the rest.
- New column on an existing table: follow the `last_quality` pattern — check
  `PRAGMA table_info(...)`, then `ALTER TABLE ... ADD COLUMN`. Never drop or
  recreate tables with user data without copying rows.
- If the table stores per-card data, also delete its rows in the Kaarten
  delete handler (`app.py`, "Verwijderen" button).
- `init_db()` only runs once per browser session; restart the app (or open a
  new tab) to apply schema changes in development.

### Extend the package JSON schema
1. Add optional fields only; old packages and DB rows must keep loading
   (`schema_version` is 1 and not checked).
2. Validate in `load_package` if the field is required for correctness.
3. Use `d.get("field", default)` where it is read.
4. Update `CHATGPT_PROMPT.txt` so ChatGPT produces it, and the README.

### Add a vocabulary import format
Extend `parse_pairs` in `vocabulary.py` (the delimiter is detected from the
first line: tab, then `;`, then `,`, then `=`). Return cards via the same
dict shape, keep exact-duplicate removal, and add cases to
`test_import_formats` / `test_validation`.

### Change answer-matching rules
Edit `normalize`/`matches` in `vocabulary.py`, update the caption in
`vocabulary_ui.exercise` and the README section, and extend
`test_answer_matching`. The project intentionally avoids fuzzy matching; the
"Toch goed rekenen" override is the escape hatch.

### Tune the scheduler
All logic is in `review()` (`app.py`). "Mastered" is defined twice (Overzicht
and Voortgang) as `reps >= 4 and interval >= 14` — change both or extract a
helper.

### Update the bundled decks
Editing `shared_decks.json` only affects users whose DB has no deck of that
name yet. To push an update to an existing install, re-import the file via the
sidebar (it overwrites by name) — card ids that stay the same keep their
progress.

## Known issues and tech debt

Not bugs that break the app today, but worth knowing before changing nearby code.

- **`use_container_width` is deprecated** (Streamlit announced removal after
  2025-12-31; still works in 1.66). `requirements.txt` has `streamlit>=1.40`
  unpinned, so a future release can break `st.button`/`st.dataframe` calls.
  Fix: replace with `width="stretch"` and consider pinning Streamlit.
- **Dead code**: the `n`/`user-{n}` id loop in both "add card" handlers is
  immediately overwritten by a uuid; `vocabulary_ui.restart()` is unused;
  `v_feedback` is set but never non-`None`.
- **Duplicated "add card" logic** in Leren (quick add) and Kaarten.
- **N+1 queries** in Leren after Again/Hard: `get_progress` per card. Fine for
  hundreds of cards; use `deck_progress` if decks get large.
- **Stampen** shows "Druk op de spatiebalk…" but has no hotkeys.
- **Woordjes renders after the footer** caption because its branch is placed
  after `st.divider()` at the end of `app.py`.
- **Deck rename/delete** is not supported; progress is keyed by deck name.
- **No concurrency control**: two sessions editing the same deck overwrite each
  other (last `save_shared_deck` wins), because each session holds its own
  in-memory copy loaded at session start.
- **Stale `vocabulary_rounds`** rows are never cleaned up; harmless.
- README contains stray lines (`"# flashcard_local"` twice) and a dangling
  bullet near the top.

## Release checklist

1. Run the test suite.
2. Manually click through the changed screen in the browser (tests use
   `AppTest`, not a real browser; mobile layout is untested).
3. Update `README.md` (user-facing, Dutch) and `TEST_RESULTS.md`.
4. Remind users to back up `studyflash_local.db` before updating; never ship
   the DB (it is gitignored).
