
import streamlit as st
import streamlit.components.v1 as components
import json, csv, io, sqlite3, math, hashlib, random
from datetime import datetime, date, timedelta
from pathlib import Path

DB = "studyflash_local.db"
DEFAULT_USER = "dochter"
BUNDLED_PACKAGE = Path(__file__).with_name("shared_decks.json")

st.set_page_config(page_title="StudyFlash Local", page_icon="📚", layout="wide")

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS progress(
        user TEXT NOT NULL, deck TEXT NOT NULL, card_id TEXT NOT NULL,
        due TEXT NOT NULL, interval REAL NOT NULL DEFAULT 0,
        ease REAL NOT NULL DEFAULT 2.5, reps INTEGER NOT NULL DEFAULT 0,
        lapses INTEGER NOT NULL DEFAULT 0, last_quality INTEGER,
        PRIMARY KEY(user, deck, card_id))""")
    columns = [row[1] for row in c.execute("PRAGMA table_info(progress)")]
    if "user" not in columns:
        c.execute("ALTER TABLE progress RENAME TO progress_legacy")
        c.execute("""CREATE TABLE progress(
            user TEXT NOT NULL, deck TEXT NOT NULL, card_id TEXT NOT NULL,
            due TEXT NOT NULL, interval REAL NOT NULL DEFAULT 0,
            ease REAL NOT NULL DEFAULT 2.5, reps INTEGER NOT NULL DEFAULT 0,
            lapses INTEGER NOT NULL DEFAULT 0, last_quality INTEGER,
            PRIMARY KEY(user, deck, card_id))""")
        c.execute("""INSERT INTO progress
            (user, deck, card_id, due, interval, ease, reps, lapses)
            SELECT ?, deck, card_id, due, interval, ease, reps, lapses
            FROM progress_legacy""", (DEFAULT_USER,))
        c.execute("DROP TABLE progress_legacy")
    columns = [row[1] for row in c.execute("PRAGMA table_info(progress)")]
    if "last_quality" not in columns:
        c.execute("ALTER TABLE progress ADD COLUMN last_quality INTEGER")
    c.execute("""CREATE TABLE IF NOT EXISTS shared_decks(
        name TEXT PRIMARY KEY,
        deck_json TEXT NOT NULL,
        updated_at TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS stamp_progress(
        user TEXT NOT NULL, deck TEXT NOT NULL, card_id TEXT NOT NULL,
        correct INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(user, deck, card_id))""")
    c.commit()
    return c

CONN = init_db()

def ensure_progress(user, deck, cards):
    for card in cards:
        cid = str(card["id"])
        CONN.execute("""INSERT OR IGNORE INTO progress
            (user, deck, card_id, due, interval, ease, reps, lapses, last_quality)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (user, deck, cid, date.today().isoformat(), 0, 2.5, 0, 0, None))
    CONN.commit()

def get_progress(user, deck, cid):
    return CONN.execute("SELECT * FROM progress WHERE user=? AND deck=? AND card_id=?",
                         (user,deck,cid)).fetchone()

def review(user, deck, card, quality):
    # Lightweight SM-2-style scheduler:
    # quality: 0=again, 1=hard, 2=good, 3=easy
    p = get_progress(user, deck, str(card["id"]))
    ease = float(p["ease"]); interval = float(p["interval"])
    reps = int(p["reps"]); lapses = int(p["lapses"])
    if quality == 0:
        reps = 0
        lapses += 1
        interval = 0
        ease = max(1.3, ease - 0.20)
        due = date.today()
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 3
        else:
            mult = {1: 1.2, 2: ease, 3: ease + 0.3}[quality]
            interval = max(1, round(interval * mult))
        reps += 1
        if quality == 1:
            ease = max(1.3, ease - 0.15)
        elif quality == 3:
            ease += 0.10
        due = date.today() if quality == 1 else date.today() + timedelta(days=interval)
    CONN.execute("""UPDATE progress SET due=?, interval=?, ease=?, reps=?, lapses=?, last_quality=?
                    WHERE user=? AND deck=? AND card_id=?""",
                 (due.isoformat(), interval, ease, reps, lapses, quality,
                  user, deck, str(card["id"])))
    CONN.commit()

def ensure_stamp_progress(user, deck, cards):
    for card in cards:
        CONN.execute("""INSERT OR IGNORE INTO stamp_progress(user, deck, card_id, correct)
                        VALUES(?,?,?,0)""", (user, deck, str(card["id"])))
    CONN.commit()

def remaining_stamp_ids(user, deck):
    return [row["card_id"] for row in CONN.execute(
        "SELECT card_id FROM stamp_progress WHERE user=? AND deck=? AND correct=0",
        (user, deck))]

def mark_stamp(user, deck, card_id, correct):
    CONN.execute("UPDATE stamp_progress SET correct=? WHERE user=? AND deck=? AND card_id=?",
                 (1 if correct else 0, user, deck, str(card_id)))
    CONN.commit()

def reset_stamp(user, deck):
    CONN.execute("UPDATE stamp_progress SET correct=0 WHERE user=? AND deck=?", (user, deck))
    CONN.commit()

def enable_keyboard_shortcuts():
    components.html("""
    <script>
    const host = window.parent;
    if (host.__studyflashKeyHandler) {
      host.removeEventListener('keydown', host.__studyflashKeyHandler);
    }
    host.__studyflashKeyHandler = (event) => {
      const active = host.document.activeElement;
      const tag = active && active.tagName ? active.tagName.toLowerCase() : '';
      if (['input', 'textarea', 'select'].includes(tag) || (active && active.isContentEditable)) return;

      const labels = {
        'Space': ['Toon antwoord', 'Toon modelantwoord'],
        'KeyZ': ['Again'],
        'KeyX': ['Hard'],
        'KeyC': ['Good'],
        'KeyV': ['Easy']
      };
      const wanted = labels[event.code];
      if (!wanted) return;
      const button = [...host.document.querySelectorAll('button')].find((candidate) => {
        const text = candidate.innerText.trim();
        return wanted.includes(text) && candidate.offsetParent !== null && !candidate.disabled;
      });
      if (button) {
        event.preventDefault();
        button.click();
      }
    };
    host.addEventListener('keydown', host.__studyflashKeyHandler);
    </script>
    """, height=1)

def load_package(upload):
    raw = upload.getvalue()
    name = upload.name.lower()
    if name.endswith(".json"):
        data = json.loads(raw.decode("utf-8"))
    elif name.endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        data = {"decks":[{"name":"Imported CSV","cards":[
            {"id":str(i+1),"front":r.get("front",""),"back":r.get("back",""),
             "tags":[x.strip() for x in r.get("tags","").split("|") if x.strip()]}
            for i,r in enumerate(rows)
        ]}]}
    else:
        raise ValueError("Gebruik JSON of CSV.")
    if "decks" not in data:
        raise ValueError("JSON moet een 'decks' array bevatten.")
    return data

def save_package(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

def save_shared_deck(deck_data):
    CONN.execute("""INSERT INTO shared_decks(name, deck_json, updated_at)
                    VALUES(?,?,?)
                    ON CONFLICT(name) DO UPDATE SET
                    deck_json=excluded.deck_json, updated_at=excluded.updated_at""",
                 (deck_data["name"], json.dumps(deck_data, ensure_ascii=False),
                  datetime.now().isoformat()))
    CONN.commit()

def save_shared_package(data):
    for deck_data in data.get("decks", []):
        save_shared_deck(deck_data)

def cards_for(deck):
    for d in st.session_state.data["decks"]:
        if d["name"] == deck:
            return d.get("cards", [])
    return []

def current_deck():
    names = [d["name"] for d in st.session_state.data["decks"]]
    if not names:
        return None
    if st.session_state.get("deck") not in names:
        st.session_state.deck = names[0]
    return st.session_state.deck

def default_package():
    if BUNDLED_PACKAGE.exists():
        data = json.loads(BUNDLED_PACKAGE.read_text(encoding="utf-8"))
    else:
        data = {
        "schema_version": 1,
        "source": {"generated_by":"ChatGPT","created":datetime.now().isoformat()},
        "decks": [{
            "name":"Demo",
            "description":"Voorbeelddeck",
            "cards":[
                {"id":"demo-1","front":"Wat is spaced repetition?","back":"Een leermethode waarbij je informatie op oplopende intervallen herhaalt.","tags":["leren"]},
                {"id":"demo-2","front":"Wat doet de hippocampus?","back":"Hij speelt een belangrijke rol bij het vormen en consolideren van nieuwe herinneringen.","tags":["biologie"]}
            ],
            "summary":"Dit is een demo. Importeer een door ChatGPT gemaakt JSON-pakket om je eigen cursus te gebruiken."
        }]
        }
    decks_by_name = {d["name"]: d for d in data.get("decks", [])}
    for row in CONN.execute("SELECT deck_json FROM shared_decks"):
        stored_deck = json.loads(row["deck_json"])
        decks_by_name[stored_deck["name"]] = stored_deck
    data["decks"] = list(decks_by_name.values())
    return data

if "data" not in st.session_state:
    st.session_state.data = default_package()

st.title("📚 StudyFlash Local")
st.caption("Lokale Streamlit-leerapp geïnspireerd op Studyflash — zonder ingebouwde AI.")
st.info("AI-generatie gebeurt bewust buiten deze app: upload je lesmateriaal in ChatGPT, laat ChatGPT een StudyFlash JSON-pakket maken en importeer dat hier.")

with st.sidebar:
    st.header("📦 Cursus")
    user = st.text_input("Gebruiker", value=st.session_state.get("user", DEFAULT_USER)).strip()
    user = user or DEFAULT_USER
    st.session_state.user = user
    st.caption(f"Voortgang wordt bijgehouden voor: {user}")
    up = st.file_uploader("Importeer ChatGPT-pakket", type=["json","csv"])
    if up:
        upload_key = f"{up.name}:{hashlib.sha256(up.getvalue()).hexdigest()}"
        if st.session_state.get("last_imported_upload") != upload_key:
            try:
                imported_data = load_package(up)
                save_shared_package(imported_data)
                st.session_state.data = imported_data
                names = [d["name"] for d in imported_data["decks"]]
                st.session_state.deck = names[0] if names else None
                st.session_state.last_imported_upload = upload_key
                st.success("Pakket geïmporteerd.")
            except Exception as e:
                st.error(f"Import mislukt: {e}")
    deck = current_deck()
    if deck:
        st.session_state.deck = st.selectbox("Deck", [d["name"] for d in st.session_state.data["decks"]],
                                             index=[d["name"] for d in st.session_state.data["decks"]].index(deck))
    st.divider()
    st.download_button("⬇️ Exporteer voortgang/pakket",
                       save_package(st.session_state.data),
                       file_name="studyflash_package.json",
                       mime="application/json")

deck = current_deck()
if not deck:
    st.warning("Geen deck gevonden.")
    st.stop()
cards = cards_for(deck)
ensure_progress(user, deck, cards)

tabs = st.tabs(["🏠 Overzicht","🧠 Leren","📝 Stampen","📖 Samenvatting","✏️ Kaarten","📊 Voortgang"])

with tabs[0]:
    d = next(x for x in st.session_state.data["decks"] if x["name"] == deck)
    rows = [get_progress(user,deck,str(c["id"])) for c in cards]
    due = sum(r["due"] <= date.today().isoformat() for r in rows)
    mastered = sum(r["reps"] >= 4 and r["interval"] >= 14 for r in rows)
    a,b,c = st.columns(3)
    a.metric("Kaarten", len(cards))
    b.metric("Vandaag te herhalen", due)
    c.metric("Beheerst", mastered)
    st.subheader(d.get("description",""))
    st.markdown(d.get("summary","Geen samenvatting beschikbaar."))
    st.caption("Plan: eerst kaarten met due=today; daarna nieuwe kaarten. Het schema gebruikt een eenvoudige SM-2-achtige herhalingslogica.")

with tabs[1]:
    st.subheader("Flashcards")

    # Quick-add card while studying
    with st.expander("➕ Kaart toevoegen tijdens het leren"):
        quick_front = st.text_input("Vraag / voorkant", key="quick_front")
        quick_back = st.text_area("Antwoord / achterkant", key="quick_back")
        quick_tags = st.text_input("Tags (komma's)", key="quick_tags")
        if st.button("Toevoegen en verder leren", type="primary", key="quick_add"):
            if not quick_front.strip() or not quick_back.strip():
                st.error("Vul zowel de vraag als het antwoord in.")
            else:
                ids = {str(c["id"]) for c in cards}
                n = 1
                cid = f"user-{n}"
                while cid in ids:
                    n += 1
                    cid = f"user-{n}"
                new_card = {
                    "id": cid,
                    "front": quick_front.strip(),
                    "back": quick_back.strip(),
                    "tags": [x.strip() for x in quick_tags.split(",") if x.strip()],
                    "source": "user"
                }
                cards.append(new_card)
                ensure_progress(user, deck, [new_card])
                save_shared_deck(next(d for d in st.session_state.data["decks"] if d["name"] == deck))
                st.success("Kaart toegevoegd en ingepland.")
                st.rerun()
    rows = [get_progress(user,deck,str(c["id"])) for c in cards]
    learn_marker = f"{user}:{deck}"
    if st.session_state.get("learn_marker") != learn_marker:
        due_ids = [str(c["id"]) for c,r in zip(cards,rows)
                   if r["due"] <= date.today().isoformat()]
        random.shuffle(due_ids)
        st.session_state.learn_queue = due_ids
        st.session_state.learn_marker = learn_marker
        st.session_state.show_answer = False
    valid_ids = {str(c["id"]) for c in cards}
    queue = [cid for cid in st.session_state.get("learn_queue", []) if cid in valid_ids]
    st.session_state.learn_queue = queue
    if not queue:
        st.success("🎉 Leerronde klaar: alle woorden zijn met Good of Easy afgerond.")
        if st.button("Nieuwe leerronde met alle woorden"):
            new_queue = [str(c["id"]) for c in cards]
            random.shuffle(new_queue)
            st.session_state.learn_queue = new_queue
            st.session_state.show_answer = False
            st.rerun()
    else:
        card_by_id = {str(c["id"]): c for c in cards}
        card = card_by_id[queue[0]]
        st.caption(f"Nog {len(set(queue))} actieve woorden")
        st.markdown(f"### {card['front']}")
        if st.session_state.show_answer:
            st.markdown("---")
            st.markdown(card["back"])
            st.caption("Toetsen: Z = Again · X = Hard · C = Good · V = Easy")
            cols = st.columns(4)
            labels = [("Again",0),("Hard",1),("Good",2),("Easy",3)]
            for col,(lab,q) in zip(cols,labels):
                if col.button(lab, use_container_width=True):
                    review(user, deck, card, q)
                    queue.pop(0)
                    if q <= 1:
                        difficult_ids = [str(c["id"]) for c in cards
                                         if (p := get_progress(user, deck, str(c["id"])))
                                         and p["due"] <= date.today().isoformat()
                                         and p["last_quality"] in (None, 0, 1)]
                        if 0 < len(difficult_ids) <= 4:
                            good_ids = [str(c["id"]) for c in cards
                                        if (p := get_progress(user, deck, str(c["id"])))
                                        and p["last_quality"] in (2, 3)
                                        and str(c["id"]) not in queue]
                            if good_ids:
                                queue.insert(0, random.choice(good_ids))
                        queue.append(str(card["id"]))
                    st.session_state.learn_queue = queue
                    st.session_state.show_answer = False
                    st.rerun()
        else:
            st.caption("Druk op de spatiebalk om het antwoord te tonen.")
            if st.button("Toon antwoord", type="primary", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()

    enable_keyboard_shortcuts()

with tabs[2]:
    st.subheader("Stampen")
    ensure_stamp_progress(user, deck, cards)
    stamp_marker = f"{user}:{deck}"
    if st.session_state.get("stamp_marker") != stamp_marker:
        stamp_queue = remaining_stamp_ids(user, deck)
        random.shuffle(stamp_queue)
        st.session_state.stamp_queue = stamp_queue
        st.session_state.stamp_marker = stamp_marker
        st.session_state.stamp_reveal = False
    valid_stamp_ids = {str(c["id"]) for c in cards}
    remaining_ids = set(remaining_stamp_ids(user, deck)) & valid_stamp_ids
    stamp_queue = [cid for cid in st.session_state.get("stamp_queue", []) if cid in remaining_ids]
    for cid in remaining_ids:
        if cid not in stamp_queue:
            stamp_queue.append(cid)
    st.session_state.stamp_queue = stamp_queue
    if not stamp_queue:
        st.success(f"🎉 Stampen klaar: alle {len(cards)} kaarten zijn juist beantwoord.")
        if st.button("Opnieuw stampen"):
            reset_stamp(user, deck)
            st.session_state.stamp_marker = None
            st.rerun()
    else:
        card_by_id = {str(c["id"]): c for c in cards}
        q = card_by_id[stamp_queue[0]]
        st.write(f"Nog {len(remaining_ids)} van {len(cards)} kaarten te gaan")
        st.markdown(f"### {q['front']}")
        if not st.session_state.get("stamp_reveal",False):
            st.caption("Druk op de spatiebalk om het antwoord te tonen.")
            if st.button("Toon modelantwoord", type="primary"):
                st.session_state.stamp_reveal = True
                st.rerun()
        else:
            st.info(q["back"])
            x,y = st.columns(2)
            if x.button("✓ Juist"):
                mark_stamp(user, deck, q["id"], True)
                stamp_queue.pop(0)
                st.session_state.stamp_queue = stamp_queue
                st.session_state.stamp_reveal = False
                st.rerun()
            if y.button("✗ Fout"):
                mark_stamp(user, deck, q["id"], False)
                stamp_queue.append(stamp_queue.pop(0))
                st.session_state.stamp_queue = stamp_queue
                st.session_state.stamp_reveal = False
                st.rerun()

with tabs[3]:
    d = next(x for x in st.session_state.data["decks"] if x["name"] == deck)
    st.subheader("Samenvatting")
    st.markdown(d.get("summary","Geen samenvatting."))
    if d.get("key_points"):
        st.subheader("Kernpunten")
        for p in d["key_points"]:
            st.markdown(f"- {p}")

with tabs[4]:
    st.subheader("Kaarten beheren")

    st.markdown("#### Kaartenoverzicht")
    st.dataframe(
        [{"Voorkant": card.get("front", ""), "Achterkant": card.get("back", "")}
         for card in cards],
        use_container_width=True,
        hide_index=True,
        height=min(38 + 35 * max(len(cards), 1), 700)
    )

    # User-created cards
    with st.expander("➕ Nieuwe kaart maken"):
        new_front = st.text_input("Voorkant / vraag", key="new_front")
        new_back = st.text_area("Achterkant / antwoord", key="new_back")
        new_tags = st.text_input("Tags (komma's)", key="new_tags")
        if st.button("Kaart toevoegen", type="primary"):
            if not new_front.strip() or not new_back.strip():
                st.error("Vul zowel de voorkant als de achterkant in.")
            else:
                ids = {str(c["id"]) for c in cards}
                n = 1
                cid = f"user-{n}"
                while cid in ids:
                    n += 1
                    cid = f"user-{n}"
                cards.append({
                    "id": cid,
                    "front": new_front.strip(),
                    "back": new_back.strip(),
                    "tags": [x.strip() for x in new_tags.split(",") if x.strip()],
                    "source": "user"
                })
                ensure_progress(user, deck, [cards[-1]])
                save_shared_deck(next(d for d in st.session_state.data["decks"] if d["name"] == deck))
                st.success("Kaart toegevoegd.")
                st.rerun()

    # Edit/delete existing cards
    with st.expander("✏️ Kaarten bewerken of verwijderen"):
        for idx,card in enumerate(cards):
            with st.expander(f"{idx+1}. {card['front']}"):
                f = st.text_input("Voorkant", card["front"], key=f"f{deck}{idx}")
                b = st.text_area("Achterkant", card["back"], key=f"b{deck}{idx}")
                tags = st.text_input("Tags (komma's)", ", ".join(card.get("tags",[])), key=f"t{deck}{idx}")
                c1, c2 = st.columns(2)
                if c1.button("Opslaan", key=f"s{deck}{idx}"):
                    card["front"], card["back"] = f,b
                    card["tags"] = [x.strip() for x in tags.split(",") if x.strip()]
                    save_shared_deck(next(d for d in st.session_state.data["decks"] if d["name"] == deck))
                    st.success("Opgeslagen.")
                if c2.button("🗑️ Verwijderen", key=f"d{deck}{idx}"):
                    cid = str(card["id"])
                    cards.pop(idx)
                    CONN.execute("DELETE FROM progress WHERE user=? AND deck=? AND card_id=?", (user, deck, cid))
                    CONN.execute("DELETE FROM stamp_progress WHERE deck=? AND card_id=?", (deck, cid))
                    CONN.commit()
                    save_shared_deck(next(d for d in st.session_state.data["decks"] if d["name"] == deck))
                    st.rerun()

with tabs[5]:
    st.subheader("Voortgang")
    rows = [get_progress(user,deck,str(c["id"])) for c in cards]
    if rows:
        mastered = sum(r["reps"] >= 4 and r["interval"] >= 14 for r in rows)
        learning = sum(r["reps"] > 0 and not (r["reps"] >= 4 and r["interval"] >= 14) for r in rows)
        new = sum(r["reps"] == 0 for r in rows)
        a,b,c = st.columns(3)
        a.metric("Nieuw",new); b.metric("In training",learning); c.metric("Beheerst",mastered)
        st.dataframe([{
            "kaart": c["front"][:70],
            "herhalingen": r["reps"],
            "interval_dagen": round(r["interval"],1),
            "ease": round(r["ease"],2),
            "volgende": r["due"]
        } for c,r in zip(cards,rows)], use_container_width=True, hide_index=True)

st.divider()
st.caption("StudyFlash Local is een onafhankelijke hobby-/prototype-app en niet verbonden aan Studyflash GmbH.")
