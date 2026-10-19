# StudyFlash Local — Architecture

Developer reference for the codebase. The end-user guide is `README.md` (Dutch).
UI text is Dutch; code, comments and these docs are English.

## Overview

A single-process Streamlit app for studying flashcards and vocabulary lists,
with all state in a local SQLite file. There is no backend, no auth and no
built-in AI: content is generated in ChatGPT with `CHATGPT_PROMPT.txt` and
imported as JSON/CSV.

| File | Role |
|---|---|
| `app.py` | Entry point. Page setup, DB schema/migrations, SM-2 scheduler, package import/export, deck loading, sidebar, and the screens Overzicht, Leren, Stampen, Samenvatting, Kaarten, Voortgang. Top-to-bottom Streamlit script, no `main()`. |
| `vocabulary.py` | Pure logic, no Streamlit: answer normalisation/matching, word-pair parsing (CSV/TSV/`;`/`=`/JSON), vocabulary deck construction, bundled example CSV loader. Unit-testable. |
| `vocabulary_ui.py` | The Woordjes screen: `render()` (import + convert deck) and the `@st.fragment` `exercise()` with its callbacks. Owns tables `vocabulary_progress` and `vocabulary_rounds`. |
| `test_vocabulary.py` | `unittest` suite: pure-function tests plus Streamlit `AppTest` end-to-end flows. |
| `shared_decks.json` | Bundled base package (currently one Latin deck). Seed only — see "Deck loading". |
| `engels_nederlands_woordjes.csv` | Bundled English→Dutch example list (`Engels,Nederlands,Foto`), loaded as a vocabulary deck. |
| `examples_nl_en.csv/.json` | Sample files for the vocabulary importer. Not loaded by the app. |
| `CHATGPT_PROMPT.txt` | Prompt that tells ChatGPT to emit the package JSON schema. Keep it in sync with `load_package`. |
| `.streamlit/config.toml` | Minimal toolbar. |
| `start_studyflash.bat` | Windows launcher; expects `.venv` next to `app.py`. |
| `studyflash_local.db` | Runtime SQLite DB (gitignored). Always created next to `app.py`. |

Gitignored local folders `backup_before_*/` and `work/` are scratch/backup
copies, not part of the app.

## Streamlit execution model (read this first)

Every interaction reruns `app.py` top to bottom. Consequences used throughout:

- **Per-session state** lives in `st.session_state`. Two keys are initialised
  once per browser session and then reused:
  - `db_connection` → the SQLite connection, exposed as module global `CONN`.
    (One connection per browser session, not `st.cache_resource`.)
  - `data` → the in-memory package `{"decks": [...]}` built by `default_package()`.
- **Only the selected screen runs.** The `screen` radio selects one branch;
  other screens execute no code and no DB queries. Tests assert this.
- **Edits are in-place.** Card edits mutate the dicts inside
  `st.session_state.data`, then call `save_shared_deck(deck)` to persist the
  *whole deck* to the DB, then `st.rerun()`.
- **Fragment.** `vocabulary_ui.exercise` is an `@st.fragment`, so answering a
  word reruns only the exercise, not the whole page. Its buttons use
  `on_click` callbacks (state changes happen before the rerun), which is why the
  answer field can be cleared and the next word shown in one step.

## Data model

### Package / deck JSON

```json
{
  "schema_version": 1,
  "source": {"generated_by": "ChatGPT", "created": "...", "title": "..."},
  "decks": [{
    "name": "Unique deck name",          // identity key everywhere
    "description": "...", "summary": "markdown", "key_points": ["..."],
    "kind": "vocabulary",                // optional; enables Woordjes exercise
    "source_language": "NL", "target_language": "EN",   // vocabulary only
    "cards": [{"id": "unique-in-deck", "front": "...", "back": "...",
               "tags": ["..."], "source": "user"}]
  }]
}
```

- **Deck identity is the `name`.** All progress tables key on deck name.
  Renaming a deck orphans its progress; there is no rename feature.
- **Card identity is `id`**, unique within a deck, always stored as a string.
  IDs are generated as `user-<uuid hex>` (manual/imported without id),
  `vocab-<uuid hex>` (vocabulary import) or
  `example-en-nl-<sha256[:24]>` (bundled example; stable so progress survives
  restarts).
- **Alternatives**: in vocabulary decks, `front`/`back` may hold several
  accepted answers separated by `|` (`bicycle | bike`). The prompt shows only
  the first alternative.

### SQLite tables

All created in `init_db()` (`app.py`) except the two vocabulary tables, which
`vocabulary_ui.exercise()` creates lazily with `CREATE TABLE IF NOT EXISTS`.

| Table | Key | Purpose |
|---|---|---|
| `shared_decks` | `name` | Full deck JSON (`deck_json`) + `updated_at`. Source of truth for every deck that was imported or edited. Shared across users. |
| `progress` | `(user, deck, card_id)` | SM-2 state for **Leren**: `due` (ISO date), `interval` (days), `ease`, `reps`, `lapses`, `last_quality` (0–3). |
| `stamp_progress` | `(user, deck, card_id)` | **Stampen**: `correct` 0/1. Round is finished when all are 1. |
| `vocabulary_progress` | `(user, deck, card_id, direction)` | **Woordjes** cumulative `attempts` / `correct` per direction (0 = front→back, 1 = back→front). |
| `vocabulary_rounds` | `(user, deck, direction, mode)` | Saved Woordjes round as JSON: `queue`, `turn`, `last_answer`, `last_cid`, `known`. Enables "Verdergaan met vorige sessie". |

`user` is a free-text name from the sidebar (default `"dochter"`). It is a
progress namespace, not an account.

**Migrations** are ad hoc in `init_db()`: inspect `PRAGMA table_info`, then
rename/copy or `ALTER TABLE ADD COLUMN`. Existing examples: adding the `user`
column (legacy rows assigned to `DEFAULT_USER`) and adding `last_quality`.

## Deck loading (`default_package`)

Decks are merged by name, later sources winning:

1. `shared_decks.json` if present, else a hard-coded "Demo" deck.
2. `engels_nederlands_woordjes.csv` via `vocabulary.load_example_csv`.
3. Every row of the `shared_decks` table.

So once a deck has been imported or edited, the DB copy overrides the bundled
file. **Changing `shared_decks.json` has no effect on a deck of the same name
already in the DB.** Deleting a deck is not supported in the UI.

`default_package()` runs once per session and again after a sidebar import.

## Feature flows

### Import (sidebar)
`load_package(upload)` accepts `.json` (package schema) or `.csv`
(`front,back,tags`, tags split by `|`, deck named "Imported CSV"). It validates
non-empty unique deck names, a `cards` list, non-empty `front`/`back`, and
unique card ids (assigns missing ones). Each deck is upserted into
`shared_decks`, overwriting a deck with the same name. A SHA-256 of the upload
(`last_imported_upload`) prevents re-importing on every rerun.

Export downloads `st.session_state.data` as JSON — decks/cards only, no progress.

### Leren (spaced repetition)
- `ensure_progress` inserts default rows (due today) for new cards.
- On entering a `(user, deck)` the queue is the shuffled set of due cards
  (`learn_marker` detects a change).
- `review()` implements a simplified SM-2. Quality 0 Again, 1 Hard, 2 Good,
  3 Easy:
  - Again: reps→0, lapses+1, interval 0, ease −0.20 (min 1.3), due today.
  - Otherwise: interval 1 → 3 → `interval × {1.2, ease, ease+0.3}`;
    Hard ease −0.15, Easy ease +0.10; Hard stays due today.
- Again/Hard re-append the card to the queue. If ≤4 difficult due cards remain,
  a random already-known card is inserted first to space the repeat.
- "Mastered" (Overzicht/Voortgang) = `reps >= 4 and interval >= 14`.
- Optional hotkeys via `streamlit-hotkeys`: Space flip, Z/X/C/V grade. Off by
  default because they swallow keystrokes in text inputs.

### Stampen (drill)
Every card until answered correctly once. `stamp_progress.correct` persists
across sessions; wrong answers go to the back of `stamp_queue`.

### Kaarten (manage)
Read-only table, "new card" expander, and an editor for **one** selected card
(keys `edit_card_<deck>`, `f/b/t/s/d<deck><card_id>`). Deleting removes the
card's rows from `progress`, `stamp_progress` and `vocabulary_progress` for all
users. Saved rounds are not touched; `start_round` drops unknown ids on resume.

### Woordjes (vocabulary)
`render()`:
- Import expander: name (must be new), languages, upload or paste →
  `parse_pairs` → `make_deck` → `save_deck` → select it via `pending_deck`
  (applied at the top of `app.py` before the selectbox is built).
- A non-vocabulary deck can be converted by setting `kind` + languages.

`exercise()` (fragment):
- Context = `(user, deck, direction, mode)`. `v_marker` also includes the
  accents flag and the serialised cards, so any change re-initialises the round.
- If a saved round exists, the user chooses resume or start over.
- Typed answers: `check_answer` → `matches()` → `record()` → `advance()` →
  `save_round()`. Wrong words go to the back of the queue. `v_turn` guards
  against counting a stale submission twice.
- "Toch goed rekenen" (`override_answer`) adds +1 correct to that attempt,
  removes the word from the queue and bumps `v_turn`.
- Flashcards: reveal → self-grade (`grade_flashcard`).
- On resume, cards added since the save (not in `known`) are appended.

Answer matching (`vocabulary.normalize`): NFKC + casefold, typographic
apostrophes/dashes unified, whitespace collapsed, leading/trailing ` .!?`
stripped, accents optionally removed. No fuzzy matching, by design.

### Session-state keys

| Prefix / key | Owner |
|---|---|
| `db_connection`, `data`, `user`, `deck`, `pending_deck`, `screen`, `last_imported_upload` | app shell |
| `learn_queue`, `learn_marker`, `show_answer`, `learning_keys`, `quick_*` | Leren |
| `stamp_queue`, `stamp_marker`, `stamp_reveal` | Stampen |
| `new_*`, `edit_card_*`, `f…/b…/t…/s…/d…` | Kaarten |
| `v_*` | Woordjes (`v_queue`, `v_turn`, `v_context`, `v_marker`, `v_ready`, `v_last_answer`, `v_last_cid`, `v_known`, `v_input`, `v_reveal`, `v_empty`, `v_feedback`, widget keys) |

Use a new unique prefix for new features; widget keys must be unique per page.

## Deployment notes

- Local: `streamlit run app.py`, port 8501.
- On Streamlit Cloud the SQLite file is ephemeral: progress, saved rounds and
  edited/imported decks vanish on redeploy. Only `shared_decks.json` and the
  example CSV survive, because they are in git.
- Backup = copy `studyflash_local.db` (and `shared_decks.json`) while the app
  is stopped.
