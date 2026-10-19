# CLAUDE.md

StudyFlash Local: a Streamlit flashcard/vocabulary study app with SQLite
storage. No backend, no auth, no built-in AI.

- Architecture, data model, deck loading, session-state keys: `docs/ARCHITECTURE.md`
- Testing, conventions, how-to recipes, known tech debt: `docs/MAINTENANCE.md`
- End-user guide (Dutch): `README.md`

## Commands

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
```

## Essentials

- `app.py` is a top-to-bottom Streamlit script (reruns on every interaction).
  Only the screen picked in the `screen` radio executes. `vocabulary.py` is
  pure logic (no Streamlit); `vocabulary_ui.py` is the Woordjes screen.
- UI text is Dutch; code and comments are English. Tests locate widgets by
  Dutch label or key — change both together.
- Decks are identified by **name**, cards by string **id**; all progress
  tables key on `(user, deck, card_id)`. Don't rename decks or regenerate ids.
- Persist deck edits by mutating `st.session_state.data` then
  `save_shared_deck(deck)`. The DB `shared_decks` table overrides
  `shared_decks.json` for decks with the same name.
- Schema changes go in `init_db()` with `CREATE TABLE IF NOT EXISTS` /
  `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`; never drop user data.
- New modules imported by the app must be added to the file-copy lists in the
  `AppTest` tests in `test_vocabulary.py`.
- Never commit `studyflash_local.db`; `backup_before_*/` and `work/` are local scratch.
- Keep `CHATGPT_PROMPT.txt` in sync with the JSON accepted by `load_package`.
