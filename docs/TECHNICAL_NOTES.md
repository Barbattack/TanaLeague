# 🔧 Technical Notes - TanaLeague

**Note tecniche di implementazione per sviluppatori**

Questo documento contiene dettagli tecnici implementativi per la manutenzione e l'estensione del sistema TanaLeague. Per guide utente, vedere [IMPORT_GUIDE.md](IMPORT_GUIDE.md) e [SETUP.md](SETUP.md).

---

## 📋 Indice

### Import TCG
1. [Pokemon TCG](#-pokemon-tcg)
2. [One Piece TCG](#️-one-piece-tcg)
3. [Riftbound TCG](#-riftbound-tcg)

### Backend
4. [Google Sheets - Dettagli Implementativi](#️-google-sheets---dettagli-implementativi)
5. [Sistema Cache (cache.py)](#️-sistema-cache-cachepy)
6. [Stats Builder (stats_builder.py)](#-stats-builder-stats_builderpy)
7. [Admin Panel (auth.py)](#-admin-panel-authpy)
8. [Configurazione (config.py)](#-configurazione-configpy)

### Frontend
9. [Seasonal Standings - Worst-N Drop Logic](#-seasonal-standings---worst-n-drop-logic)
10. [Frontend - Chart.js Implementation](#-frontend---chartjs-implementation)

### Schema e Flusso
11. [Google Sheets - Schema Completo](#-google-sheets---schema-completo)
12. [Webapp - Flusso Dati](#-webapp---flusso-dati)

### Appendici
13. [Debugging Tips](#-debugging-tips)
14. [Riferimenti Codice](#-riferimenti-codice)

---

## 🎴 Pokemon TCG

### Formato Input: TDF/XML

File `.tdf` sono XML con struttura:
```xml
<tournament>
  <players>
    <player id="123" name="Rossi, Mario" />
  </players>
  <rounds>
    <round number="1">
      <pairing player1="123" player2="456" result="W" />
    </round>
  </rounds>
</tournament>
```

### Sistema Punti con Pareggi

**Match Points nel PDF:**
```python
win_points = W * 3 + T * 1 + L * 0
```

**IMPORTANTE:** Il campo `Points_Victory` in Results è diverso:
```python
# Nel foglio Results, colonna 7 (Pts_Victory)
points_victory = W  # NON win_points/3!
```

Questo è intenzionale per compatibilità storica con il sistema Pokémon.

### BYE Handling

```python
if result == "BYE":
    # Conta come vittoria automatica
    match_w += 1
    win_points += 3
```

### Multi-Round Aggregation

Lo script processa tutti i round e aggrega:
```python
for round in rounds:
    for match in round.pairings:
        player_stats[player_id]['W'] += 1 if win else 0
        player_stats[player_id]['T'] += 1 if tie else 0
        player_stats[player_id]['L'] += 1 if loss else 0
```

---

## 🏴‍☠️ One Piece TCG

### Formato Input: CSV

```csv
Ranking,Name,Points,OMW,Player ID,Deck
1,Rossi Mario,9,65.5,OP123,Roronoa Zoro
```

**IMPORTANTE:** Non ha tracking W/T/L nel CSV. Le colonne 10-12 in Results rimangono vuote.

### Sistema Punti Semplificato

```python
# One Piece non ha pareggi
points_victory = points / 3  # Punti dal CSV diviso 3
points_ranking = n_participants - (rank - 1)
points_total = points_victory + points_ranking
```

### OMW% dal CSV

A differenza di Pokemon (calcolato da match), One Piece legge OMW% direttamente dal CSV.

---

## 🎮 Riftbound TCG

### Formato Input: CSV Multi-Round

Riftbound usa **file CSV multipli**, uno per ogni round del torneo, esportati dal software di gestione tornei.

**Naming convention:**
```
RFB_2025_11_17_R1.csv   ← Round 1
RFB_2025_11_17_R2.csv   ← Round 2
RFB_2025_11_17_R3.csv   ← Round 3
```

**Utilizzo:**
```bash
# Import multi-round (RACCOMANDATO)
python import_riftbound.py --csv R1.csv,R2.csv,R3.csv --season RFB01

# Test mode
python import_riftbound.py --csv R1.csv,R2.csv,R3.csv --season RFB01 --test
```

### Struttura CSV (22 colonne)

**Tutte le colonne:**
```
Col 0:  Table Number
Col 1:  Feature Match
Col 2:  Ghost Match
Col 3:  Match Deck Checked
Col 4:  Player 1 User ID        ← CRITICO: Membership Number
Col 5:  Player 1 First Name     ← CRITICO
Col 6:  Player 1 Last Name      ← CRITICO
Col 7:  Player 1 Email
Col 8:  Player 2 User ID        ← CRITICO: Membership Number
Col 9:  Player 2 First Name     ← CRITICO
Col 10: Player 2 Last Name      ← CRITICO
Col 11: Player 2 Email
Col 12: Match Status
Col 13: Match Result            ← CRITICO: Formato "Nome Cognome: 2-0-0"
Col 14: Player 1 Round Record
Col 15: Player 2 Round Record
Col 16: Player 1 Event Record   ← CRITICO: W-L-D totale torneo
Col 17: Player 2 Event Record   ← CRITICO: W-L-D totale torneo
Col 18: Past Interactions
Col 19: Judge at table
Col 20: Registration
Col 21: Match Status (duplicato)
```

**IMPORTANTE:**
- L'User ID (colonne 4 e 8) è usato come Membership Number
- Il validatore richiede **almeno 22 colonne** per ogni riga

### Multi-Round Aggregation

Lo script legge tutti i CSV in sequenza. **L'ultimo round contiene l'Event Record finale** di ogni giocatore:

```python
def parse_csv_rounds(csv_files, season_id, tournament_date):
    players_data = {}  # user_id -> {name, event_record, rounds_played}

    for csv_idx, csv_path in enumerate(csv_files, 1):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header

            for row in reader:
                p1_id = row[4].strip()
                p1_event_record = row[16].strip()  # W-L-D finale

                # Sovrascrive con ogni round - ultimo avrà record finale
                players_data[p1_id] = {
                    'name': f"{row[5]} {row[6]}".strip(),
                    'event_record': p1_event_record,
                    'rounds_played': csv_idx
                }
```

### Match Extraction (Riftbound_Matches)

Oltre ai risultati, estrae i singoli match H2H con vincitore:

```python
# Parse vincitore dal Match Result (formato: "Nome Cognome: 2-0-0")
winner_membership = ""
if match_result and ":" in match_result:
    winner_name = match_result.split(":")[0].strip()
    # Match con Player 1 o Player 2
    if winner_name.lower() == p1_name.lower():
        winner_membership = p1_id
    elif winner_name.lower() == p2_name.lower():
        winner_membership = p2_id

matches_data.append([
    tournament_id, p1_id, p1_name, p2_id, p2_name,
    winner_membership, round_num, table_number, match_result
])
```

**Output:** Salva nel foglio `Riftbound_Matches` per statistiche H2H future.

### Event Record Parsing

```python
def parse_wld_record(record_str: str) -> tuple:
    """
    Parse W-L-D record string.
    Input: "2-1-0" or "3-0-1"
    Output: (wins, losses, draws)
    """
    match = re.match(r'(\d+)-(\d+)-(\d+)', record_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0
```

**ATTENZIONE:** Il formato è W-L-D (Wins-Losses-Draws), non W-D-L!

### Sistema Punti

```python
# Match points (Swiss system) - usato per ranking
win_points = w * 3 + d * 1 + l * 0

# TanaLeague points (UGUALE a Pokemon e One Piece!)
points_victory = w  # Numero di vittorie (NON win_points!)
points_ranking = n_participants - (rank - 1)
points_total = points_victory + points_ranking
```

**IMPORTANTE:** `points_victory` per TUTTI i TCG è il numero di vittorie (W), NON win_points. Il sistema punti TanaLeague è uniforme tra Pokemon, One Piece e Riftbound.

### Ranking Calculation

Il ranking finale è calcolato ordinando per punti Swiss:

```python
# Ordina per punti (poi per wins se pari punti)
results_data.sort(key=lambda x: (x['points'], x['w']), reverse=True)

# Assegna rank
for rank, player in enumerate(results_data, 1):
    player['rank'] = rank
```

### OMW (Opponent Match Win%)

**NOTA:** I CSV Riftbound NON contengono OMW. La colonna OMW in Results è impostata a 0:
```python
formatted_results.append([
    ...
    0,  # OMW (non disponibile nei CSV, lasciamo 0)
    ...
])
```

### Colonne Results Sheet

```
Col 11 (row[10]): W (vittorie match)
Col 12 (row[11]): T (pareggi/ties - nel CSV sono "D" draws)
Col 13 (row[12]): L (sconfitte match)
```

### Troubleshooting Specifico

#### "Nessun giocatore trovato nei CSV"
- **Causa:** Formato CSV non corretto o file vuoto
- **Check:** Verifica che il CSV abbia almeno 18 colonne
- **Check:** Verifica che le colonne 4 e 8 contengano User ID

#### File CSV con encoding errato
- **Sintomo:** Caratteri strani nei nomi
- **Soluzione:** Lo script usa `encoding='utf-8'`. Se necessario, converti il CSV

#### Match Result non parsato
- **Sintomo:** `winner_membership` vuoto
- **Causa:** Nome vincitore nel Match Result non corrisponde esattamente ai nomi giocatori
- **Soluzione:** Lo script ha fallback che cerca parti del nome (cognome/nome)

---

## 🗄️ Google Sheets - Dettagli Implementativi

### Batch Operations per API Quota

**IMPORTANTE:** Google Sheets API ha limiti di quota. Usa sempre batch operations:

```python
# ❌ SBAGLIATO - 100 API calls
for row in rows:
    worksheet.append_row(row)

# ✅ CORRETTO - 1 API call
worksheet.append_rows(rows)
```

**Limiti:**
- 300 requests per 60 secondi per progetto
- 60 requests per 60 secondi per utente

### Update vs Append

```python
# Append (nuovo torneo)
ws_results.append_rows(formatted_results)

# Update (ricalcolo stats)
ws_players.batch_update([
    {'range': f'A{row_num}:K{row_num}', 'values': [[...]]},
    ...
])
```

### Column Indices (0-based vs 1-based)

**ATTENZIONE:** gspread usa 1-based, ma list slicing usa 0-based:

```python
# Leggere colonna 3 (Membership)
row = ws.get_all_values()[row_index]
membership = row[2]  # 0-based: colonna 3 = index 2

# Aggiornare colonna 3
ws.update_cell(row_num, 3, value)  # 1-based: colonna 3 = col 3
```

### Results Sheet - Column Mapping

```
Col 1 (row[0]):  Result_ID
Col 2 (row[1]):  Tournament_ID
Col 3 (row[2]):  Membership
Col 4 (row[3]):  Rank
Col 5 (row[4]):  Win_Points
Col 6 (row[5]):  OMW
Col 7 (row[6]):  Pts_Victory
Col 8 (row[7]):  Pts_Ranking
Col 9 (row[8]):  Pts_Total
Col 10 (row[9]): Name
Col 11 (row[10]): W   ← Match tracking
Col 12 (row[11]): T   ← Match tracking
Col 13 (row[12]): L   ← Match tracking
```

### Players Sheet - Column Mapping

```
Col 1 (row[0]):  Membership
Col 2 (row[1]):  Name
Col 3 (row[2]):  TCG
Col 4 (row[3]):  First_Seen
Col 5 (row[4]):  Last_Seen
Col 6 (row[5]):  Total_Tournaments
Col 7 (row[6]):  Tournament_Wins
Col 8 (row[7]):  Match_W
Col 9 (row[8]):  Match_T
Col 10 (row[9]): Match_L
Col 11 (row[10]): Total_Points
```

**IMPORTANTE per fix player stats:**
Quando leggi dati da Players per mostrare in `/players`, usa gli indici corretti:
```python
# ✅ CORRETTO
p.tournaments = row[5]  # Col 6: Total_Tournaments
p.wins = row[6]         # Col 7: Tournament_Wins
p.points = row[10]      # Col 11: Total_Points
```

---

## 🏆 Seasonal Standings - Worst-N Drop Logic

### Configurazione per TCG

```python
# One Piece & Riftbound: drop 2 worst tournaments dopo 8+ tornei
if total_tournaments >= 8:
    max_to_count = total_tournaments - 2
else:
    max_to_count = total_tournaments

# Pokemon: stesso sistema
```

### ARCHIVED Seasons Exemption

**IMPORTANTE:** Le stagioni con status ARCHIVED NON applicano lo scarto:

```python
# Leggi status da Config sheet
season_status = config_row[4].strip().upper()

if season_status == "ARCHIVED":
    max_to_count = total_tournaments  # NO DROP
    print("⚠️  Scarto: NESSUNO (stagione ARCHIVED - archivio dati)")
else:
    # Applica logica normale
    if total_tournaments >= 8:
        max_to_count = total_tournaments - 2
```

**Razionale:** Le stagioni ARCHIVED servono solo come archivio storico, non come competizione attiva. Applicare lo scarto sarebbe fuorviante.

---

## 🎨 Frontend - Chart.js Implementation

### Version

**Chart.js 4.4.0** (da CDN)

### Doughnut Chart - Match Record

```javascript
new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Vittorie', 'Pareggi', 'Sconfitte'],
        datasets: [{
            data: [wins, ties, losses],
            backgroundColor: ['#22c55e', '#fbbf24', '#ef4444']
        }]
    },
    options: {
        plugins: {
            legend: { position: 'bottom' }
        }
    }
});
```

### Bar Chart - Ranking Distribution

```javascript
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['1° Posto', '2° Posto', '3° Posto', 'Top 8', 'Altro'],
        datasets: [{
            data: [count_1st, count_2nd, count_3rd, count_top8, count_other],
            backgroundColor: ['#fbbf24', '#e5e7eb', '#cd7f32', '#3b82f6', '#94a3b8']
        }]
    },
    options: {
        scales: {
            y: { beginAtZero: true, ticks: { stepSize: 1 } }
        }
    }
});
```

### Radar Chart - Performance Overview

**5 metriche normalizzate 0-100:**

```python
# Backend calculation
win_rate = (tournament_wins / tournaments_played) * 100
top8_rate = (top8_count / tournaments_played) * 100
victory_rate = (tournament_wins / tournaments_played) * 100  # 1st place only
avg_performance = min(100, (avg_points / 25) * 100)  # 25 points = 100%

# Consistency: based on std deviation
if len(points) > 1:
    std_dev = statistics.stdev(points)
    consistency = max(0, (1 - std_dev / 10) * 100)  # max std_dev = 10 → 0%
else:
    consistency = 100  # Solo 1 torneo = massima consistenza
```

```javascript
new Chart(ctx, {
    type: 'radar',
    data: {
        labels: ['Win Rate', 'Top8 Rate', 'Victory Rate', 'Avg Perf', 'Consistency'],
        datasets: [{
            label: 'Performance',
            data: [win_rate, top8_rate, victory_rate, avg_perf, consistency],
            backgroundColor: 'rgba(102, 126, 234, 0.2)',
            borderColor: 'rgb(102, 126, 234)'
        }]
    },
    options: {
        scales: {
            r: { min: 0, max: 100, ticks: { stepSize: 20 } }
        }
    }
});
```

### Tooltip Best Practices

```javascript
// ✅ Tooltip interattivi su icone info
<span class="info-icon" title="Percentuale di tornei vinti">ℹ️</span>

// ✅ Formattazione valori
title="Win Rate: 15.4%"  // Con unità di misura
title="Media: 15.8 punti" // Numeri con 1 decimale
```

---

## 🔍 Debugging Tips

### Check Column Indices

Quando i dati non corrispondono:
```python
# Stampa header e prima riga
print("Header:", ws.row_values(1))
print("Row 2:", ws.row_values(2))
print("Indices:", {i: val for i, val in enumerate(ws.row_values(2))})
```

### Test Regex

```python
import re
test_cases = [
    "1",
    "Cogliati, Pietro",
    "(2metalupo)",
    "12 4-0-0 62.5% 100% 62.5%"
]
for line in test_cases:
    print(f"Testing: [{line}]")
    # Test your patterns here
```

### Dry Run Mode

Aggiungi sempre modalità test:
```python
if test_mode:
    print("⚠️  TEST MODE - Nessuna scrittura")
    # Show what would be written
    for row in data:
        print(row)
else:
    # Actual write
    worksheet.append_rows(data)
```

---

## 📚 Riferimenti Codice

### parse_csv_rounds() - Riftbound

File: `tanaleague2/import_riftbound.py`

Funzione chiave da consultare per:
- Parsing CSV multi-round
- Aggregazione Event Record
- Estrazione match H2H con vincitori
- Calcolo ranking da punti Swiss

### update_players_stats() - Tutti i TCG

Presente in tutti e 3 gli import scripts.

**IMPORTANTE:** Ricalcola SEMPRE da zero da Results sheet:
```python
# NON incrementare stats esistenti
# MA ricalcolare tutto da Results
for result in all_results:
    if result.membership == player_membership:
        # Accumula
```

Questo evita inconsistenze da import parziali o errori.

---

## ⚙️ Sistema Cache (cache.py)

### Architettura

Il sistema cache usa un pattern **file-based + in-memory**:

```
Google Sheets API → cache.py → cache_data.json → Flask app
                      ↓
                 In-memory cache
```

### Classe SheetCache

```python
class SheetCache:
    def __init__(self):
        self.cache_data = None      # Dati in memoria
        self.last_update = None     # Timestamp ultimo refresh
        self.load_from_file()       # Carica da file all'avvio
```

### TTL (Time To Live)

```python
CACHE_REFRESH_MINUTES = 5  # Da config.py

def needs_refresh(self):
    if not self.cache_data or not self.last_update:
        return True
    age = datetime.now() - self.last_update
    return age > timedelta(minutes=CACHE_REFRESH_MINUTES)
```

### Dati Cachati

La cache contiene:
```python
cache_data = {
    'schema_version': 2,
    'seasons': [...],                    # Da Config sheet
    'standings_by_season': {...},        # Da Seasonal_Standings_PROV/FINAL
    'tournaments_by_season': {...},      # Da Tournaments sheet
    # Legacy aliases
    'standings': {...},
    'tournaments': {...}
}
```

### Logica PROV vs FINAL

```python
# Stagioni ACTIVE → legge da Seasonal_Standings_PROV
# Stagioni CLOSED → legge da Seasonal_Standings_FINAL
# Fallback: se sheet vuoto, prova l'altro
```

### Refresh Manuale

```python
# Da webapp
GET /api/refresh  # Forza refresh cache classifiche
```

---

## 📊 Stats Builder (stats_builder.py)

### Overview

Calcola statistiche avanzate per la pagina `/stats/<scope>`. Supporta:
- **Scope singolo**: `OP12`, `PKM01`, `RFB01`
- **All-time TCG**: `ALL-OP`, `ALL-PKM`, `ALL-RFB`

### Struttura Output

```python
build_stats(['OP12']) → {
    'OP12': {
        'spotlights': {...},      # Record individuali
        'spot_narrative': [...],  # Cards narrative
        'pulse': {...},           # KPI e serie temporali
        'tales': {...},           # Pattern sociali
        'hof': {...}              # Hall of Fame
    }
}
```

### Spotlights (Record Individuali)

| Spotlight | Metrica | Requisito |
|-----------|---------|-----------|
| **Dominatore** | MVP score (media × partecipazione) | min 3 eventi |
| **Cecchino** | Media punti per torneo | min 3 eventi |
| **Costante/Imprevedibile** | Deviazione standard punti | min 3 eventi |
| **Fenice** | Trend miglioramento recente | min 3 eventi |
| **Big Match Player** | Media punti in eventi Q3 (grandi) | min 3 eventi |
| **Finalista** | % punti da Top 8 | min 3 eventi |

### Spot Narrative (Cards)

8 narrative cards calcolate automaticamente:
1. **Rising Star** - Giocatore in crescita
2. **Rookie to Watch** - Nuovo promettente (≤3 eventi)
3. **Ironman** - Più presenze
4. **Climber** - Maggior rimonta
5. **Closer** - Capitalizza in Top 8
6. **Big Stage** - Rende nei grandi eventi
7. **New Faces** - Nuovi giocatori (30g)
8. **Attendance Pulse** - Trend presenze

### Pulse (KPI)

```python
kpi = {
    'events_total': 15,           # Tornei totali
    'unique_players': 45,         # Giocatori unici
    'entries_total': 230,         # Partecipazioni totali
    'avg_participants': 15.3,     # Media partecipanti
    'top8_rate': 34.8,            # % in Top 8
    'avg_omw': 52.3,              # Media OMW%
    'compleanno_lega': {...},     # Giorni di attività
    'record_presenze': {...}      # Torneo più affollato
}
```

### Tales (Pattern Sociali)

```python
tales = {
    'companions': [...],      # Coppie che giocano insieme
    'podium_rivals': [...],   # Coppie in podio insieme
    'top8_mixture': [...],    # Diversità avversari in Top 8
    'sfortuna_nera': {...},   # Chi finisce 9° più spesso
    'torneo_competitivo': {...},
    'ultimo_arrivato': {...}
}
```

### Hall of Fame

```python
hof = {
    'highest_single_score': {...},  # Punteggio singolo più alto
    'biggest_crowd': {...},         # Torneo più partecipato
    'most_balanced': {...},         # Torneo più equilibrato (stdev)
    'most_dominated': {...},        # Torneo più dominato (gap)
    'fastest_riser': {...},         # Maggior crescita
    'underdog_hero': {...},         # Vittorie da underdog
    'scalata_epica': {...},         # Scalata ranking
    'piu_vittorie': {...},          # Record vittorie
    'piu_punti': {...}              # Record punti lifetime
}
```

### Cache Stats

```python
# File: stats_cache.py
MAX_AGE = 900  # 15 minuti

GET /api/stats/refresh/<scope>  # Forza refresh stats
```

---

## 🔐 Admin Panel (auth.py)

### Autenticazione

Sistema session-based con Flask:

```python
# Login
session['admin_logged_in'] = True
session['admin_username'] = username
session['login_time'] = datetime.now().isoformat()
session.permanent = True  # Usa PERMANENT_SESSION_LIFETIME
```

### Password Hash

**NON** salvare password in chiaro! Usa werkzeug:

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Generare hash (una volta)
hash = generate_password_hash("mia_password_sicura")
# Output: "pbkdf2:sha256:600000$..."

# Verificare (al login)
check_password_hash(ADMIN_PASSWORD_HASH, password_inserita)
```

### Decorator @admin_required

```python
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Solo se loggato
    return render_template('admin/dashboard.html')
```

### Session Timeout

```python
SESSION_TIMEOUT = 30  # minuti (da config.py)

# Verifica automatica ad ogni richiesta
if datetime.now() - login_time > timedelta(minutes=SESSION_TIMEOUT):
    logout_user()
    return False
```

### Routes Admin

| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/admin/login` | GET/POST | Form login |
| `/admin/logout` | GET | Logout |
| `/admin` | GET | Dashboard (protetta) |
| `/admin/import/onepiece` | POST | Import One Piece |
| `/admin/import/pokemon` | POST | Import Pokemon |
| `/admin/import/riftbound` | POST | Import Riftbound |

---

## 🔧 Configurazione (config.py)

### Variabili Richieste

```python
# Google Sheets
SHEET_ID = "abc123..."              # ID del Google Sheet
CREDENTIALS_FILE = "service_account_credentials.json"

# Cache
CACHE_REFRESH_MINUTES = 5           # TTL cache in minuti
CACHE_FILE = "cache_data.json"      # File cache locale

# Flask
SECRET_KEY = "chiave-segreta-32-char"
DEBUG = False                       # True solo in sviluppo

# Admin
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "pbkdf2:sha256:600000$..."
SESSION_TIMEOUT = 30                # Minuti
```

### Generare Valori Sicuri

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# ADMIN_PASSWORD_HASH
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('mia_password'))"
```

### File .gitignore

```
config.py
service_account_credentials.json
cache_data.json
*.pyc
__pycache__/
```

---

## 📋 Google Sheets - Schema Completo

### Config Sheet

| Colonna | Nome | Descrizione |
|---------|------|-------------|
| A | Season_ID | ID stagione (es. OP12, PKM01) |
| B | TCG | Codice TCG (OP, PKM, RFB) |
| C | Name | Nome visualizzato |
| D | Season_Num | Numero stagione |
| E | Status | ACTIVE / CLOSED / ARCHIVED |
| F-K | Settings | Configurazioni varie |
| L | Next_Tournament | Data prossimo torneo |

### Tournaments Sheet

| Colonna | Nome | Descrizione |
|---------|------|-------------|
| A | Tournament_ID | ID univoco (es. OP12_2025-11-17) |
| B | Season_ID | Riferimento stagione |
| C | Date | Data torneo (YYYY-MM-DD) |
| D | Participants | Numero partecipanti |
| E | Rounds | Numero round |
| F | Format | Formato (Swiss, etc.) |
| G | Location | Luogo |
| H | Winner | Nome vincitore |

### Seasonal_Standings_PROV / _FINAL

| Colonna | Nome | Descrizione |
|---------|------|-------------|
| A | Season_ID | ID stagione |
| B | Membership | ID giocatore |
| C | Name | Nome giocatore |
| D | Points | Punti totali stagione |
| E | Tournaments_Played | Tornei giocati |
| F | Tournaments_Counted | Tornei contati (dopo scarto) |
| G | Total_Wins | Vittorie tornei |
| H | Match_Wins | Vittorie match |
| I | Best_Rank | Miglior piazzamento |
| J | Top8_Count | Volte in Top 8 |
| K | Position | Posizione in classifica |

### Riftbound_Matches (per H2H futuro)

| Colonna | Nome | Descrizione |
|---------|------|-------------|
| A | Tournament_ID | ID torneo |
| B | Player1_ID | Membership giocatore 1 |
| C | Player1_Name | Nome giocatore 1 |
| D | Player2_ID | Membership giocatore 2 |
| E | Player2_Name | Nome giocatore 2 |
| F | Winner_ID | Membership vincitore |
| G | Round | Numero round |
| H | Table | Numero tavolo |
| I | Result | Risultato testuale |

**NOTA:** Questo foglio viene popolato durante import ma NON è ancora utilizzato dalla webapp per visualizzare statistiche H2H.

---

## 🌐 Webapp - Flusso Dati

### Request Flow

```
Browser → Flask Route → cache.get_data() → Template Jinja2 → HTML
                              ↓
                      (se cache scaduta)
                              ↓
                      Google Sheets API
```

### Routes Principali

| Route | Template | Dati |
|-------|----------|------|
| `/` | landing.html | standings top 3, stats highlights |
| `/classifiche` | classifiche_page.html | lista stagioni per TCG |
| `/classifica/<season>` | classifica.html | standings completi |
| `/players` | players.html | lista giocatori |
| `/player/<membership>` | player.html | profilo + charts + achievement |
| `/stats/<scope>` | stats.html | spotlights, pulse, tales, hof |
| `/achievements` | achievements.html | catalogo 40 achievement |

### Jinja2 Filters Custom

```python
@app.template_filter('format_player_name')
def format_player_name(name, tcg, membership=''):
    # OP: Nome completo
    # PKM: "Nome I."
    # RFB: Membership (nickname)
```

---

## 🛡️ Import Validator (import_validator.py)

### Overview

Sistema di validazione pre-import che garantisce:
- **Nessuna scrittura** su Google Sheets se ci sono errori
- **Report dettagliato** con riga/linea esatta degli errori
- **Conferma utente** per warning non bloccanti
- **Supporto reimport** sicuro con cancellazione atomica (batch)

### Filosofia: "Validate Everything, Write Nothing Until Safe"

```
┌─────────────────────────────────────────────────────────────┐
│  FASE 1-4: VALIDAZIONE (può fallire, nessun danno)          │
│  ─────────────────────────────────────────────────────────  │
│  1. File esiste e leggibile?                                │
│  2. Formato corretto (XML/CSV valido)?                      │
│  3. Struttura attesa (tag/colonne)?                         │
│  4. Dati sensati (tipi, range)?                             │
│  5. Google Sheets raggiungibile? Sheet esistono?            │
│  6. Torneo già importato? (no duplicati)                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ TUTTO OK?
              ┌───────────┴───────────┐
              │ NO                    │ SÌ
              ▼                       ▼
    ┌─────────────────┐    ┌─────────────────────────────────┐
    │ ❌ STOP         │    │  FASE 5: IMPORT                 │
    │ Report errori   │    │  (batch write, tutto insieme)   │
    │ Sheet INTATTO   │    └─────────────────────────────────┘
    └─────────────────┘
```

### Classe ImportValidator

```python
from import_validator import ImportValidator

validator = ImportValidator()

# Aggiungere errori/warning
validator.add_error("Messaggio errore", line=15, detail="Dettaglio")
validator.add_warning("Messaggio warning", line=20)

# Verifiche
if not validator.is_valid():    # Errori critici?
    print(validator.report())   # Stampa report formattato
    sys.exit(1)

if validator.has_warnings():    # Warning presenti?
    if not validator.ask_confirmation():  # Chiedi conferma
        sys.exit(0)
```

### Funzioni di Validazione Disponibili

| Funzione | TCG | Descrizione |
|----------|-----|-------------|
| `validate_pokemon_tdf()` | PKM | Valida file TDF/XML Pokemon |
| `validate_onepiece_csv()` | OP | Valida CSV Bandai One Piece |
| `validate_riftbound_csv()` | RFB | Valida CSV multi-round Riftbound |
| `validate_google_sheets()` | Tutti | Verifica connessione e worksheet |
| `validate_season()` | Tutti | Verifica season in Config |
| `check_tournament_exists()` | Tutti | Check duplicati |
| `batch_delete_tournament()` | Tutti | Cancellazione atomica per reimport |

### Flag --reimport

Tutti gli script di import supportano il flag `--reimport` per sovrascrivere tornei esistenti:

```bash
# Import normale (blocca se esiste)
python import_pokemon.py --tdf torneo.tdf --season PKM01

# Reimport (cancella e reimporta)
python import_pokemon.py --tdf torneo.tdf --season PKM01 --reimport
```

**Flusso --reimport:**
1. Validazione completa (come sempre)
2. Trova dati esistenti del torneo
3. Chiede conferma esplicita all'utente
4. Cancella atomicamente (batch delete):
   - Righe Results
   - Riga Tournaments
   - Righe Matches (se presenti)
5. Importa nuovi dati
6. Ricalcola Players (automatico, già implementato)

**Garanzie di sicurezza:**
- Cancellazione atomica (all-or-nothing) via Google Sheets API batchUpdate
- Se cancellazione fallisce, nessun dato viene toccato
- Players ricalcolati da zero leggendo tutti i Results

### Check Specifici per TCG

**Pokemon TDF:**
- File XML valido
- Tag obbligatori: `<name>`, `<id>`, `<startdate>`, `<players>`, `<standings>`
- Formato data: MM/DD/YYYY
- Ogni player ha userid, firstname, lastname
- Match outcomes validi (1, 2, 3, 5)

**One Piece CSV:**
- CSV parsabile
- Colonne: Ranking, User Name, Membership Number, Win Points, Record
- Ranking numerico e sequenziale
- Membership non vuoto

**Riftbound CSV (22 colonne):**
- Tutti i file esistono
- Almeno 22 colonne per riga
- User ID (col 4, 8) non vuoti
- Event Record formato W-L-D

### Output Esempio (Errore)

```
🚀 IMPORT TORNEO POKEMON: Challenge_2025_11_25.tdf
📊 Stagione: PKM01

🔍 VALIDAZIONE IN CORSO...

   📄 Validazione file TDF...

================================================================
  ERRORI RILEVATI (2)
================================================================
  1. Riga 12: Tag <startdate> formato errato
     Trovato: "24-09-2025" - Atteso: MM/DD/YYYY (es. "09/24/2025")

  2. Riga 45: Player userid="5234880" senza <lastname>

================================================================

❌ IMPORT ANNULLATO - Correggi gli errori e riprova
📋 Nessuna modifica effettuata al Google Sheet
```

---

**Fine Technical Notes**

Ultimo aggiornamento: 22 Novembre 2025
