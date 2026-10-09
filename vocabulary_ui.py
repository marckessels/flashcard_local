import json
import random
import streamlit as st
from vocabulary import parse_pairs, make_deck, matches


def render(data, deck, user, conn, save_deck):
    st.subheader('Woordjes')
    with st.expander('Woordenlijst importeren of plakken'):
        name = st.text_input('Naam woordenlijst', key='v_name')
        a, b = st.columns(2)
        source = a.text_input('Taal voorkant', 'NL', key='v_source')
        target = b.text_input('Taal achterkant', 'EN', key='v_target')
        upload = st.file_uploader('Woordenlijst CSV / JSON', type=['csv', 'json'], key='v_file')
        text = st.text_area('Of plak woordparen', placeholder='huis = house\nfiets = bicycle | bike', key='v_paste')
        st.caption('Twee kolommen: nl,en (of source,target). Zonder kopregel kan ook. Plakken: tab, ; of =. Alternatieven: |.')
        if st.button('Woordenlijst toevoegen', key='v_import'):
            try:
                if any(d['name'] == name.strip() for d in data['decks']):
                    raise ValueError('Deze decknaam bestaat al. Kies een nieuwe naam.')
                content = upload.getvalue().decode('utf-8-sig') if upload else text
                kind = 'json' if upload and upload.name.lower().endswith('.json') else 'paste'
                created = make_deck(name, parse_pairs(content, kind), source, target)
                save_deck(created)
                data['decks'].append(created)
                st.session_state.pending_deck = created['name']
                st.rerun()
            except (ValueError, UnicodeError) as error:
                st.error(str(error))
    current = next(d for d in data['decks'] if d['name'] == deck)
    if current.get('kind') != 'vocabulary':
        st.info('Importeer een woordenlijst hierboven, of maak van dit deck een woordenlijst.')
        with st.form('v_convert'):
            source = st.text_input('Bron­taal', 'NL')
            target = st.text_input('Doeltaal', 'EN')
            if st.form_submit_button('Gebruik dit deck als woordenlijst'):
                if source.strip() and target.strip():
                    current.update(kind='vocabulary', source_language=source.strip(), target_language=target.strip())
                    save_deck(current)
                    st.rerun()
                st.error('Vul beide talen in.')
        return
    st.caption('Woorden toevoegen, wijzigen en verwijderen kan via het tabblad Kaarten. Gebruik | voor alternatieven aan beide kanten.')
    exercise(current, user, deck, conn)


@st.fragment
def exercise(current, user, deck, conn):
    cards = current['cards']
    languages = (current.get('source_language', 'NL'), current.get('target_language', 'EN'))
    direction = st.radio('Oefenrichting', [0, 1], format_func=lambda n: f'{languages[n]} → {languages[1-n]}', horizontal=True, key='v_direction')
    mode = st.radio('Oefenvorm', ['Flashcards', 'Antwoord typen'], horizontal=True, key='v_mode')
    accents = st.checkbox('Accenten negeren bij antwoordcontrole', key='v_accents')
    st.caption('Hoofdletters, extra spaties, afsluitende .!? en typografische apostroffen worden genegeerd. Spelling, lidwoorden en accenten tellen mee; accenten kun je hierboven uitschakelen.')
    conn.execute('''CREATE TABLE IF NOT EXISTS vocabulary_progress(
        user TEXT, deck TEXT, card_id TEXT, direction INTEGER, attempts INTEGER DEFAULT 0,
        correct INTEGER DEFAULT 0, PRIMARY KEY(user,deck,card_id,direction))''')
    conn.commit()
    marker = (user, deck, direction, mode, accents, json.dumps(cards, ensure_ascii=False))
    if st.session_state.get('v_marker') != marker:
        queue = [c['id'] for c in cards]
        random.shuffle(queue)
        st.session_state.update(v_marker=marker, v_queue=queue, v_feedback=None, v_reveal=False, v_empty=False, v_turn=0)
    queue = st.session_state.v_queue
    if not queue:
        st.success('Oefenronde afgerond.')
        st.button('Nieuwe woordenronde', on_click=restart)
    else:
        card = next(c for c in cards if c['id'] == queue[0])
        front, back = ('front', 'back') if direction == 0 else ('back', 'front')
        st.caption(f'Nog {len(queue)} woorden in deze ronde')
        st.subheader(card[front].split('|')[0].strip())
        feedback = st.session_state.v_feedback
        if mode == 'Antwoord typen' and feedback is None:
            answer_key = f'v_input_{st.session_state.v_turn}'
            with st.form(f'v_answer_{st.session_state.v_turn}'):
                st.text_input('Jouw vertaling', key=answer_key)
                st.form_submit_button('Controleer antwoord', on_click=check_answer,
                                      args=(answer_key, card[back], accents, conn, user, deck, card['id'], direction))
            if st.session_state.get('v_empty'):
                st.warning('Typ eerst een antwoord.')
        elif mode == 'Flashcards':
            if not st.session_state.v_reveal:
                st.button('Draai woordkaart om', on_click=reveal)
            else:
                st.info(card[back])
                for label, correct in [('Juist onthouden', True), ('Nog oefenen', False)]:
                    st.button(label, on_click=grade_flashcard,
                              args=(conn, user, deck, card['id'], direction, correct))
        if feedback is not None:
            correct, answer = feedback
            if correct:
                st.success(f'Goed! Jouw antwoord: {answer}')
            else:
                st.error(f'Nog oefenen. Jouw antwoord: {answer}')
            st.info('Toegestane antwoorden: ' + card[back])
            st.button('Volgend woord', on_click=advance, args=(queue, correct))
    rows = conn.execute('SELECT direction, SUM(attempts), SUM(correct) FROM vocabulary_progress WHERE user=? AND deck=? GROUP BY direction', (user, deck)).fetchall()
    for row in rows:
        st.caption(f'{languages[row[0]]} → {languages[1-row[0]]}: {row[2]} goed van {row[1]} pogingen (alle oefenrondes).')
    st.caption('Woordjes oefent alle woorden; fouten komen opnieuw terug. Deze voortgang staat los van de spaced-repetitionplanning in Leren.')


def record(conn, user, deck, cid, direction, correct):
    conn.execute('''INSERT INTO vocabulary_progress(user,deck,card_id,direction,attempts,correct)
        VALUES(?,?,?,?,1,?) ON CONFLICT(user,deck,card_id,direction) DO UPDATE SET
        attempts=attempts+1, correct=vocabulary_progress.correct+excluded.correct''', (user,deck,str(cid),direction,int(correct)))
    conn.commit()


def advance(queue, correct):
    cid = queue.pop(0)
    if not correct:
        queue.append(cid)
    st.session_state.update(v_feedback=None, v_reveal=False, v_empty=False, v_turn=st.session_state.v_turn+1)




def check_answer(key, expected, accents, conn, user, deck, cid, direction):
    answer = st.session_state.get(key, '')
    st.session_state.v_empty = not answer.strip()
    if answer.strip() and st.session_state.v_feedback is None:
        correct = matches(answer, expected, accents)
        record(conn, user, deck, cid, direction, correct)
        st.session_state.v_feedback = (correct, answer)


def reveal():
    st.session_state.v_reveal = True


def restart():
    st.session_state.v_marker = None


def grade_flashcard(conn, user, deck, cid, direction, correct):
    record(conn, user, deck, cid, direction, correct)
    advance(st.session_state.v_queue, correct)
