# 🔧 RIFTBOUND - Documentazione Tecnica Completa

**Data:** 17 Novembre 2025
**Autore:** Claude (sessione con tutti i context)

---

## 📖 INDICE

1. [Architettura](#architettura)
2. [Formato PDF Input](#formato-pdf-input)
3. [Logica Parsing](#logica-parsing)
4. [Calcolo Punti](#calcolo-punti)
5. [Integrazione Google Sheet](#integrazione-google-sheet)
6. [Codice Completo](#codice-completo)
7. [Troubleshooting](#troubleshooting)

---

## 🏗️ ARCHITETTURA

### Flow completo

```
┌──────────────┐
│   PDF File   │  RFB_YYYY_MM_DD.pdf
└──────┬───────┘
       │
       ↓
┌──────────────────────┐
│  parse_pdf()         │  Estrazione dati
│  - Strategy 1: Tables│  (pdfplumber)
│  - Strategy 2: Words │
└──────┬───────────────┘
       │
       ↓ {tournament, results, players}
       │
┌──────────────────────┐
│ import_to_sheet()    │  Scrittura Google Sheet
│ - Tournaments        │
│ - Results (W/T/L)    │
│ - Players (lifetime) │
└──────────────────────┘
       │
       ↓
┌──────────────────────┐
│  Google Sheet        │
│  - Config            │
│  - Players           │
│  - Results           │
│  - Tournaments       │
└──────────────────────┘
```

### File coinvolti

```
tanaleague2/
├── import_riftbound.py      # Script principale (445 righe)
├── RFB_2025_11_10.pdf        # PDF test (16 giocatori)
├── config.py                 # Config (SHEET_ID, credentials)
└── requirements.txt          # Dipendenze (pdfplumber, gspread)
```

---

## 📄 FORMATO PDF INPUT

### Struttura visuale

```
┌─────────────────────────────────────────────────────────────┐
│ Standings - Release Event - Lunedì 10 Novembre             │
│ Round 4            Page 1/1            Rank 1 - 16         │
│                                                             │
│ Rank  Player              Points  W-L-D   OMW    GW   OGW  │
│ 1                                                           │
│ Cogliati, Pietro                                            │
│ (2metalupo)                                                 │
│ 12 4-0-0 62.5% 100% 62.5%                                  │
│                                                             │
│ 2                                                           │
│ Viganò, Federico                                            │
│ (Squicco)                                                   │
│ 9 3-1-0 64.5% 75% 64.5%                                    │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

### Pattern per ogni giocatore

```
Riga 1:  [RANK]              → Es: "1"
Riga 2:  [COGNOME, NOME]     → Es: "Cogliati, Pietro"
Riga 3:  ([NICKNAME])        → Es: "(2metalupo)"
Riga 4:  [STATS]             → Es: "12 4-0-0 62.5% 100% 62.5%"
```

**IMPORTANTE:** Il NICKNAME è il **Membership Number** nel sistema!

### Regex patterns

```python
# Rank (numero da 1 a 99)
r'^(\d{1,2})\b'

# Nickname tra parentesi
r'\(([^)]+)\)'

# Stats completi
r'(\d+)\s+(\d+)-(\d+)-(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%'
#  ^points  ^W   ^L   ^D     ^OMW      ^GW       ^OGW
```

---

## 🧠 LOGICA PARSING

### Problema: extract_text() non funziona

**Comportamento:**
```python
text = page.extract_text()
# Ritorna solo 1034 caratteri invece del contenuto completo
# Non contiene i rank (righe con solo numero)
```

**Causa:** Font/layout PDF incompatibili con estrazione testo base.

### Soluzione: Strategia ibrida

#### STRATEGIA 1: Estrazione tabelle (tentativo)

```python
tables = page.extract_tables()
if tables:
    # Elabora tabelle strutturate
    # PRO: Molto affidabile quando funziona
    # CONTRO: Non sempre riconosce le tabelle in tutti i PDF
```

#### STRATEGIA 2: Analisi coordinate (MAIN)

**Concetto chiave:** Usa coordinate fisiche delle parole nel PDF.

```python
# 1. Estrai tutte le parole con coordinate
words = page.extract_words()
# Ogni word è un dict: {text, x0, x1, top, bottom, ...}

# 2. Raggruppa per coordinata Y (stessa riga orizzontale)
lines_dict = {}
for word in words:
    y = round(word['top'])  # Arrotonda per gestire lievi differenze
    if y not in lines_dict:
        lines_dict[y] = []
    lines_dict[y].append(word)

# 3. Ordina righe dall'alto in basso
sorted_lines = sorted(lines_dict.items())  # Sort by Y coordinate

# 4. Per ogni riga, ordina parole da sinistra a destra
for y, words_in_line in sorted_lines:
    words_in_line.sort(key=lambda w: w['x0'])  # Sort by X coordinate
    line_text = ' '.join([w['text'] for w in words_in_line])
```

### State Machine per parsing

**Stati:**
- `current_rank` = None | int
- `current_name` = None | str
- `current_nickname` = None | str

**Transizioni:**

```python
# Stato IDLE → RANK_FOUND
if line_text matches r'^(\d{1,2})\b':
    current_rank = matched_number
    # Controlla se nickname è sulla stessa riga
    if '(nickname)' in rest_of_line:
        current_nickname = extract_nickname()
        current_name = text_before_nickname()
    else:
        current_name = rest_of_line (se presente)

# Stato RANK_FOUND → NICKNAME_FOUND
if current_rank and not current_nickname:
    if '(nickname)' in line_text:
        current_nickname = extract_nickname()
        if not current_name:
            current_name = text_before_nickname()
    elif line_text and not current_name:
        current_name = line_text  # Nome su riga separata

# Stato COMPLETE (rank + name + nickname) → STATS_FOUND
if current_rank and current_name and current_nickname:
    if line_text matches STATS_PATTERN:
        # Estrai tutti i dati
        points, w, l, d, omw, gw, ogw = parse_stats(line_text)

        # Salva player
        results_data.append({...})

        # Reset stato → IDLE
        current_rank = None
        current_name = None
        current_nickname = None
```

**Vantaggi di questo approccio:**
- ✅ Non dipende da `extract_text()`
- ✅ Robusto contro variazioni di layout
- ✅ Gestisce multilinea automaticamente
- ✅ Funziona anche con font problematici

---

## 💯 CALCOLO PUNTI

### Sistema Riftbound (con pareggi)

**Match points (come Pokémon):**
```python
win_points = w * 3 + d * 1 + l * 0
# Esempio: 3 vittorie, 1 pareggio = 3*3 + 1*1 = 10 punti match
```

### Formula TanaLeague

**Punti per la classifica stagionale:**

```python
# 1. Punti da vittorie
points_victory = win_points / 3
# Esempio: 10 punti match / 3 = 3.33

# 2. Punti da posizionamento
points_ranking = n_participants - (rank - 1)
# Esempio: 16 partecipanti, rank 1 → 16 - 0 = 16

# 3. Totale
points_total = points_victory + points_ranking
# Esempio: 3.33 + 16 = 19.33
```

**Perché questa formula?**
- Premia sia le vittorie che la posizione finale
- Bilanciata per tornei di diverse dimensioni
- Consistente con One Piece e Pokémon

---

## 🗄️ INTEGRAZIONE GOOGLE SHEET

### Fogli coinvolti

#### 1. Config
**Aggiungi stagione RFB:**

```python
# Nel foglio Config, riga nuova:
Season_ID    = "RFB01"
TCG          = "RFB"  # ← IMPORTANTE: identifica il gioco
Season_Name  = "Riftbound Season 1"
Entry_Fee    = 5
Pack_Cost    = 6
X0_Ratio     = 0.4
X1_Ratio     = 0.3
Rounding     = 0.5
Status       = "ACTIVE"
Next_Tournament = "2025-11-20"
```

#### 2. Tournaments
**Scrittura:**

```python
tournament_data = [
    tournament_id,        # "RFB01_2025-11-10"
    season_id,            # "RFB01"
    tournament_date,      # "2025-11-10"
    n_participants,       # 16
    n_rounds,             # 4
    pdf_filename,         # "RFB_2025_11_10.pdf"
    import_datetime,      # "2025-11-17 14:30:00"
    winner_name           # "Cogliati, Pietro"
]

ws_tournaments.append_row(tournament_data)
```

#### 3. Results
**Struttura colonne (FONDAMENTALE!):**

```
Col 1:  Result_ID         → "RFB01_2025-11-10_2metalupo"
Col 2:  Tournament_ID     → "RFB01_2025-11-10"
Col 3:  Membership        → "2metalupo"
Col 4:  Rank              → 1
Col 5:  Win_Points        → 12 (W*3 + D*1)
Col 6:  OMW               → 62.5
Col 7:  Pts_Victory       → 4.0 (12/3)
Col 8:  Pts_Ranking       → 16 (16 - 0)
Col 9:  Pts_Total         → 20.0 (4.0 + 16)
Col 10: Name              → "Cogliati, Pietro"
Col 11: W                 → 4  ← TRACKING W/T/L
Col 12: T (Ties/Draws)    → 0  ← TRACKING W/T/L
Col 13: L                 → 0  ← TRACKING W/T/L
```

**IMPORTANTE:** Colonne 11-13 per tracking W/T/L (come Pokémon).

**Scrittura:**

```python
for player in results_data:
    row = [
        f"{tournament_id}_{player['membership']}",  # Result_ID
        tournament_id,
        player['membership'],  # nickname
        player['rank'],
        player['win_points'],  # W*3 + D*1
        round(player['omw'], 2),
        round(points_victory, 2),
        round(points_ranking, 2),
        round(points_total, 2),
        player['name'],
        player['w'],   # Col 11
        player['d'],   # Col 12 (T = Ties)
        player['l']    # Col 13
    ]
    formatted_results.append(row)

ws_results.append_rows(formatted_results)
```

#### 4. Players
**Lifetime stats per TCG:**

```python
# Struttura
Membership       → "2metalupo"
Name             → "Cogliati, Pietro"
TCG              → "RFB"  ← Filtra per gioco
First_Seen       → "2025-11-10"
Last_Seen        → "2025-11-10"
Total_Tournaments → 1
Tournament_Wins   → 1 (conta rank=1)
Match_W          → 4
Match_T          → 0
Match_L          → 0
Total_Points     → 20.0
```

**Logica update:**

```python
# 1. Leggi tutti Results per questo TCG
all_results = ws_results.get_all_values()
for row in all_results[3:]:  # Skip header
    membership = row[2]
    tournament_id = row[1]

    # Filtra per TCG
    season_id = tournament_id.split('_')[0]  # "RFB01"
    tcg = extract_tcg_code(season_id)         # "RFB"

    if tcg != "RFB":
        continue

    # Accumula stats
    lifetime_stats[membership]['total_tournaments'] += 1
    if rank == 1:
        lifetime_stats[membership]['tournament_wins'] += 1
    lifetime_stats[membership]['match_w'] += w
    lifetime_stats[membership]['match_t'] += d  # draws
    lifetime_stats[membership]['match_l'] += l
    lifetime_stats[membership]['total_points'] += points_total

# 2. Aggiorna o inserisci in Players
for membership, stats in lifetime_stats.items():
    key = (membership, "RFB")
    if key in existing_players:
        # Update existing row
        ws_players.batch_update([...])
    else:
        # Insert new player
        ws_players.append_row([...])
```

---

## 💻 CODICE COMPLETO

### Funzione parse_pdf (estratto chiave)

```python
def parse_pdf(pdf_path: str, season_id: str, tournament_date: str) -> Dict:
    """Estrae dati torneo dal PDF"""

    results_data = []
    players = {}

    with pdfplumber.open(pdf_path) as pdf:
        # STRATEGIA 1: Tabelle
        for page in pdf.pages:
            tables = page.extract_tables()
            # ... elabora tabelle se presenti

        # STRATEGIA 2: Coordinate (MAIN)
        all_words = []
        for page in pdf.pages:
            words = page.extract_words()
            all_words.extend(words)

        # Raggruppa per Y
        lines_dict = {}
        for word in all_words:
            y = round(word['top'])
            if y not in lines_dict:
                lines_dict[y] = []
            lines_dict[y].append(word)

        # Ordina righe
        sorted_lines = sorted(lines_dict.items())

        # State machine
        current_rank = None
        current_name = None
        current_nickname = None

        for y, words_in_line in sorted_lines:
            words_in_line.sort(key=lambda w: w['x0'])
            line_text = ' '.join([w['text'] for w in words_in_line])

            # Cerca rank
            rank_match = re.match(r'^(\d{1,2})\b', line_text)
            if rank_match and 1 <= int(rank_match.group(1)) <= 99:
                current_rank = int(rank_match.group(1))
                rest_of_line = line_text[len(rank_match.group(0)):].strip()

                # Nickname sulla stessa riga?
                nick_match = re.search(r'\(([^)]+)\)', rest_of_line)
                if nick_match:
                    current_nickname = nick_match.group(1)
                    name_part = rest_of_line[:nick_match.start()].strip()
                    if name_part:
                        current_name = name_part
                else:
                    if rest_of_line:
                        current_name = rest_of_line
                continue

            # Cerca nickname se manca
            if current_rank and not current_nickname:
                nick_match = re.search(r'\(([^)]+)\)', line_text)
                if nick_match:
                    current_nickname = nick_match.group(1)
                    # ...
                    continue
                if line_text and not current_name:
                    current_name = line_text
                    continue

            # Cerca stats se abbiamo tutto
            if current_rank and current_name and current_nickname:
                stats_match = re.search(
                    r'(\d+)\s+(\d+)-(\d+)-(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%',
                    line_text
                )
                if stats_match:
                    points = int(stats_match.group(1))
                    w = int(stats_match.group(2))
                    l = int(stats_match.group(3))
                    d = int(stats_match.group(4))
                    omw = float(stats_match.group(5))
                    gw = float(stats_match.group(6))
                    ogw = float(stats_match.group(7))

                    win_points = w * 3 + d * 1

                    players[current_nickname] = current_name

                    results_data.append({
                        'rank': current_rank,
                        'name': current_name,
                        'membership': current_nickname,
                        'points': points,
                        'w': w,
                        'l': l,
                        'd': d,
                        'win_points': win_points,
                        'omw': omw,
                        'gw': gw,
                        'ogw': ogw
                    })

                    # Reset
                    current_rank = None
                    current_name = None
                    current_nickname = None

    if not results_data:
        raise ValueError("❌ Nessun giocatore trovato!")

    # Calcola tournament metadata
    n_participants = len(results_data)
    n_rounds = results_data[0]['w'] + results_data[0]['l'] + results_data[0]['d']
    winner_name = results_data[0]['name']

    # Formatta per Google Sheet
    formatted_results = []
    for r in results_data:
        points_victory = r['win_points'] / 3
        points_ranking = n_participants - (r['rank'] - 1)
        points_total = points_victory + points_ranking

        formatted_results.append([
            f"{tournament_id}_{r['membership']}",  # Result_ID
            tournament_id,
            r['membership'],
            r['rank'],
            r['win_points'],
            round(r['omw'], 2),
            round(points_victory, 2),
            round(points_ranking, 2),
            round(points_total, 2),
            r['name'],
            r['w'],
            r['d'],  # T (ties)
            r['l']
        ])

    tournament_data = [
        tournament_id,
        season_id,
        tournament_date,
        n_participants,
        n_rounds,
        pdf_path.split('/')[-1],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        winner_name
    ]

    return {
        'tournament': tournament_data,
        'results': formatted_results,
        'players': players
    }
```

### Utilizzo

```bash
# Test (no write)
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01 --test

# Import reale
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01
```

---

## 🐛 TROUBLESHOOTING

### "Could get FontBBox from font descriptor"
**Tipo:** Warning
**Gravità:** Bassa (non blocca esecuzione)
**Causa:** Font PDF con metadati incompleti
**Soluzione:** Ignora - è normale

### "Trovati 0 ranks, X nicknames"
**Tipo:** Error
**Causa:** `extract_text()` non funziona
**Soluzione:** Usa strategia 2 con `extract_words()`
**Debug:** Aggiungi print delle prime righe estratte

### "Nessun giocatore trovato"
**Tipo:** Error - Critico
**Causa:** Parsing fallito completamente
**Debug checklist:**
1. Quante parole trova `extract_words()`? (dovrebbe essere 200+)
2. Quante righe dopo raggruppamento Y? (dovrebbe essere 50+)
3. Stampa le prime 20 righe ricostruite - vedi i rank?
4. Controlla pattern regex - funziona su testo di test?

**Esempio debug:**

```python
print(f"  📝 Trovate {len(all_words)} parole")
print(f"  📏 Raggruppate in {len(sorted_lines)} righe")

# Mostra prime righe
for i, (y, words) in enumerate(sorted_lines[:20]):
    words.sort(key=lambda w: w['x0'])
    text = ' '.join([w['text'] for w in words])
    print(f"  Riga {i:2d} (y={y}): [{text}]")
```

### Match W/L/D invertiti
**Sintomo:** Record 4-0-0 salvato come L=4 invece di W=4
**Causa:** Ordine capture groups nel regex
**Fix:** Verifica ordine nel pattern:
```python
# CORRETTO
r'(\d+)-(\d+)-(\d+)'  # W-L-D
w = match.group(1)
l = match.group(2)
d = match.group(3)
```

---

## ✅ CHECKLIST FUNZIONAMENTO

**Il sistema funziona se:**

- [ ] `extract_words()` trova 200+ parole
- [ ] Raggruppa in 50+ righe
- [ ] Trova tutti i 16 rank (1-16)
- [ ] Trova tutti i 16 nickname
- [ ] Associa correttamente rank-nome-nickname-stats
- [ ] Test mode mostra "16 giocatori trovati"
- [ ] Tutti i giocatori hanno W/L/D corretti
- [ ] Points_total calcolato correttamente

**Output perfetto:**
```
✓ Rank 1: Cogliati, Pietro (2metalupo) - 4-0-0
✓ Rank 2: Viganò, Federico (Squicco) - 3-1-0
...
✓ Rank 16: Ghezzi, Davide (ArtiKron) - 0-4-0

✅ Parsing completato: 16 giocatori trovati!
```

---

## 🚀 DEPLOY SU PYTHONANYWHERE

1. Upload `import_riftbound.py` e PDF via Files tab
2. Console: `cd ~/tanaleague2`
3. Test: `python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01 --test`
4. Se OK → Import reale senza `--test`

---

**Fine documentazione tecnica Riftbound**

Ultimo aggiornamento: 17 Novembre 2025
