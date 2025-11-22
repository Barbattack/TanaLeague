# 🏆 TanaLeague

**Sistema di gestione classifiche e statistiche per leghe competitive di Trading Card Games (TCG)**

Web app Flask completa per tracciare tornei, classifiche, statistiche avanzate, profili giocatori e achievement per **One Piece TCG**, **Pokémon TCG** e **Riftbound TCG**.

🌐 **Live:** [latanadellepulci.pythonanywhere.com](https://latanadellepulci.pythonanywhere.com)

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)

---

## 📋 Indice

- [Caratteristiche](#-caratteristiche)
- [TCG Supportati](#-tcg-supportati)
- [Novità v2.0](#-novità-v20)
- [Quick Start](#-quick-start)
- [Architettura](#-architettura)
- [Import Tornei](#-import-tornei)
- [Achievement System](#-achievement-system-new)
- [Deploy](#-deploy-su-pythonanywhere)
- [Documentazione](#-documentazione)
- [Struttura Progetto](#-struttura-progetto)

---

## ✨ Caratteristiche

### Funzionalità Principali
- **📊 Classifiche Stagionali** - Rankings con scarto dinamico (migliori N-2 tornei)
- **🏅 Achievement System** - 40+ achievement sbloccabili automaticamente
- **📈 Statistiche Avanzate** - MVP, Sharpshooter, Metronome, Phoenix, Big Stage, Closer
- **👤 Profili Giocatori** - Storico completo, win rate, trend, 3 grafici avanzati (doughnut, bar, radar), achievement
- **📉 Analytics** - Pulse (KPI), Tales (narrative), Hall of Fame
- **🔄 Import Automatico** - Da CSV (One Piece), TDF/XML (Pokémon), CSV Multi-Round (Riftbound)
- **⚡ Cache Intelligente** - Aggiornamento automatico ogni 5 minuti
- **🎮 Multi-TCG** - Gestione separata per 3 giochi diversi

---

## 🎮 TCG Supportati

### 🏴‍☠️ One Piece TCG
- **Status**: ✅ Completo
- **Import**: CSV da Limitlesstcg
- **Sistema Punti**: W=3, L=0 (no pareggi)
- **Display Nomi**: Nome completo (default)
- **Features**: Classifiche, stats, achievement, profili

### ⚡ Pokémon TCG
- **Status**: ✅ Completo
- **Import**: TDF/XML da Play! Pokémon Tournament
- **Sistema Punti**: W=3, D=1, L=0 (con pareggi)
- **Display Nomi**: "Nome I." (es. "Pietro C.")
- **Features**: Classifiche, stats, achievement, match tracking H2H

### 🌌 Riftbound TCG
- **Status**: ✅ Completo (UPDATED!)
- **Import**: CSV Multi-Round (uno per round, aggregati automaticamente)
- **Sistema Punti**: W=3, D=1, L=0 (con pareggi)
- **Display Nomi**: First Name + Last Name
- **Features**: Classifiche, stats avanzate (W-L-D tracking), achievement, multi-round support

---

## 🆕 Novità v2.0

### Achievement System 🏅
- **40+ achievement** organizzati in 7 categorie
- **Auto-unlock** durante import tornei
- **Profili giocatore** con achievement sbloccati
- **Pagina dedicata** `/achievements` con progress tracking
- Categorie: Glory, Giant Slayer, Consistency, Legacy, Wildcards, Seasonal, Heartbreak

### Riftbound Support 🌌
- **Import CSV Multi-Round** con aggregazione automatica (R1.csv,R2.csv,R3.csv)
- **Stats avanzate** con W-L-D tracking dettagliato (come Pokémon!)
- **Seasonal standings** automatici
- **Achievement unlock** integrato
- User ID come Membership Number

### Pokémon Enhancements ⚡
- **Seasonal standings** automatici (come Riftbound/OP)
- **Achievement unlock** integrato
- Display personalizzato "Nome I."

### UI/UX Improvements 🎨
- **Grafici Avanzati Profilo Giocatore** 📊
  - Match Record (doughnut): W-T-L lifetime con percentuali
  - Ranking Distribution (bar): Frequenza in ogni fascia (1°, 2°, 3°, Top8, oltre)
  - Performance Radar (pentagon): 5 metriche normalizzate (Win Rate, Top8 Rate, Victory Rate, Avg Perf, Consistency)
  - 9 tooltip informativi per user-friendly UX
- **Nuova pagina Classifiche** (`/classifiche`) con lista tutte le stagioni
- **Menu rinnovato** con Home, Classifiche, Achievement, Stats
- **Pulsanti PKM/RFB attivi** sulla homepage
- **Stagioni ARCHIVED nascoste** da dropdown e liste
- **Custom name display** per TCG (OP: full, PKM: Nome I., RFB: nickname)
- **Lista giocatori corretta** con punti medi e stats accurate

---

## 🆕 Recent Updates (Nov 2024)

### 📊 Advanced Player Charts (Latest)
- **3 grafici interattivi** nella scheda giocatore:
  - **Doughnut Chart**: Match Record lifetime (W-T-L con percentuali)
  - **Bar Chart**: Distribuzione ranking (🥇 1°, 🥈 2°, 🥉 3°, Top8, oltre)
  - **Radar Chart**: Performance overview su 5 metriche (Win Rate, Top8 Rate, Victory Rate, Avg Perf, Consistency)
- **9 tooltip informativi** con spiegazioni dettagliate per ogni metrica
- **Formule ottimizzate**: Avg Performance normalizzato a 25pt, Consistency basato su std dev
- **Responsive design** con Chart.js 4.4.0

### 🔧 Bug Fixes & Improvements
- **Fixed**: Player list stats now show correct data (tournaments, wins, avg points)
- **Fixed**: Tournament record in player history shows actual W-T-L instead of wrong ranking
- **Fixed**: ARCHIVED seasons skip worst-2-tournament drop (data archive only)
- **Refactor**: Import scripts renamed for consistency (`import_pokemon.py`, `import_onepiece.py`, `import_riftbound.py`)
- **Docs**: Comprehensive Pokemon points system clarification in IMPORT_GUIDE

---

## 🚀 Quick Start

### Prerequisiti
```bash
- Python 3.8+
- Google Cloud Project con Sheets API abilitato
- Service Account credentials JSON
- PythonAnywhere account (per deploy)
```

### Installazione Locale

```bash
# 1. Clone repository
git clone <repository-url>
cd TanaLeague

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Configura credenziali
# - Scarica service_account_credentials.json da Google Cloud
# - Metti in tanaleague2/

# 4. Configura SHEET_ID
# - Modifica SHEET_ID in tanaleague2/config.py
# - Oppure in ogni import script

# 5. Setup Achievement System (UNA VOLTA!)
cd tanaleague2
python setup_achievements.py
# Questo crea i fogli Achievement_Definitions e Player_Achievements

# 6. Run app locale
python app.py
```

Webapp disponibile su `http://localhost:5000`

---

## 🏗️ Architettura

```
┌─────────────────┐
│  Google Sheets  │  ← Database (Config, Results, Players, Tournaments, Achievements)
└────────┬────────┘
         │ (gspread API)
         ↓
┌─────────────────┐
│   Flask App     │  ← Backend Python (app.py + cache.py + achievements.py)
│   + Cache       │  ← Cache file-based (5 min TTL)
└────────┬────────┘
         │ (Jinja2)
         ↓
┌─────────────────┐
│  HTML Templates │  ← Frontend Bootstrap 5 + Font Awesome
│   + Bootstrap   │
└─────────────────┘
```

### Google Sheets Structure

| Sheet | Descrizione |
|-------|-------------|
| **Config** | Configurazione stagioni (ID, nome, status, settings) |
| **Tournaments** | Lista tornei (ID, data, partecipanti, vincitore) |
| **Results** | Risultati individuali (giocatore, rank, punti, W-L-D) |
| **Players** | Anagrafica giocatori (membership, nome, TCG, stats lifetime) |
| **Seasonal_Standings_PROV** | Classifiche provvisorie (stagioni ACTIVE) |
| **Seasonal_Standings_FINAL** | Classifiche finali (stagioni CLOSED) |
| **Achievement_Definitions** | Definizioni 40 achievement (NEW!) |
| **Player_Achievements** | Achievement sbloccati (membership, ach_id, date) (NEW!) |
| **Pokemon_Matches** | Match H2H Pokemon (opzionale) |
| **Vouchers** | Buoni negozio (solo One Piece) |

---

## 📥 Import Tornei

### One Piece TCG (CSV)

```bash
cd tanaleague2
python import_onepiece.py --csv path/to/tournament.csv --season OP12
```

**Formato CSV richiesto**: Export da Limitlesstcg
- Columns: Ranking, User Name, Membership Number, Win Points, OMW %, Record, etc.

### Pokémon TCG (TDF/XML)

```bash
cd tanaleague2
python import_pokemon.py --tdf path/to/tournament.tdf --season PKM-FS25
```

**Formato TDF richiesto**: Export da Play! Pokémon Tournament software

### Riftbound TCG (CSV Multi-Round)

**Import Singolo Round:**
```bash
cd tanaleague2
python import_riftbound.py --csv RFB_2025_11_17_R1.csv --season RFB01
```

**Import Multi-Round (RACCOMANDATO):**
```bash
cd tanaleague2
python import_riftbound.py --csv RFB_2025_11_17_R1.csv,RFB_2025_11_17_R2.csv,RFB_2025_11_17_R3.csv --season RFB01
```

**Formato CSV richiesto**: Export CSV dal software gestione tornei (uno per round)
- Deve contenere: Player User ID, First/Last Name, Event Record (W-L-D)
- Multi-round fornisce stats dettagliate W-L-D come Pokémon!

### Test Mode (Dry Run)

Tutti gli import supportano `--test` per verificare senza scrivere:

```bash
python import_onepiece.py --csv file.csv --season OP12 --test
python import_pokemon.py --tdf file.tdf --season PKM-FS25 --test
python import_riftbound.py --csv file.csv --season RFB01 --test
# Multi-round test
python import_riftbound.py --csv R1.csv,R2.csv,R3.csv --season RFB01 --test
```

---

## 🏅 Achievement System (NEW!)

### Setup (Una volta sola)

```bash
cd tanaleague2
python setup_achievements.py
```

Questo crea e popola:
- `Achievement_Definitions` (40 achievement predefiniti)
- `Player_Achievements` (vuoto, si popola automaticamente)

### Categorie Achievement (40 totali)

| Categoria | Count | Esempi |
|-----------|-------|--------|
| 🏆 **Glory** | 7 | First Blood, King of the Hill, Perfect Storm, Undefeated Season |
| ⚔️ **Giant Slayer** | 6 | Dragonslayer, Kingslayer, Gatekeeper, Upset Artist |
| 📈 **Consistency** | 8 | Hot Streak, Unstoppable Force, Season Warrior, Iron Wall |
| 🌍 **Legacy** | 8 | Debutto, Veteran, Gladiator, Hall of Famer, Triple Crown |
| 🎪 **Wildcards** | 4 | The Answer (42 pt), Lucky Seven, Triple Threat |
| ⏰ **Seasonal** | 3 | Opening Act, Grand Finale, Season Sweep |
| 💔 **Heartbreak** | 5 | Rookie Struggles, Forever Second, Storm Cloud |

### Auto-Unlock

Gli achievement si sbloccano **automaticamente** quando importi tornei:

```bash
python import_onepiece.py --csv file.csv --season OP12
# Output:
# ...
# 🎮 Check achievement...
# 🏆 0000012345: 🎬 First Blood
# 🏆 0000012345: 📅 Regular
# ✅ 2 achievement sbloccati!
```

### Visualizzazione

- **Profilo Giocatore** (`/player/<membership>`): Achievement sbloccati con emoji, descrizione, data
- **Pagina Achievement** (`/achievements`): Tutti i 40 achievement con % unlock

---

## 🚀 Deploy su PythonAnywhere

### 1. Upload Files

```bash
# Via git (consigliato)
git clone <repository-url>

# Oppure upload manuale:
# - Upload file Python via Files tab
# - Upload templates/ via Files tab
# - Upload service_account_credentials.json
```

### 2. Configura Web App

**Web tab → Add new web app:**
- Python version: 3.8+
- Framework: Flask
- WSGI file: `/home/yourusername/TanaLeague/tanaleague2/wsgi.py`

**Crea wsgi.py:**
```python
import sys
sys.path.insert(0, '/home/yourusername/TanaLeague/tanaleague2')

from app import app as application
```

### 3. Installa Dipendenze

```bash
pip install --user gspread google-auth pandas pdfplumber flask
```

### 4. Setup Achievement

```bash
cd ~/TanaLeague/tanaleague2
python setup_achievements.py
```

### 5. Reload

**Web tab → Reload button**

---

## 📚 Documentazione

| Documento | Descrizione |
|-----------|-------------|
| **[docs/SETUP.md](docs/SETUP.md)** | Guida installazione e configurazione completa |
| **[docs/IMPORT_GUIDE.md](docs/IMPORT_GUIDE.md)** | Come importare tornei da CSV/PDF/TDF |
| **[docs/ACHIEVEMENT_SYSTEM.md](docs/ACHIEVEMENT_SYSTEM.md)** | Sistema achievement in dettaglio |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Risoluzione problemi comuni |

---

## 📁 Struttura Progetto

```
TanaLeague/
├── README.md                       # Questo file
├── requirements.txt                # Dipendenze Python
│
├── tanaleague2/                    # Codice principale
│   ├── app.py                      # Flask app + routes
│   ├── cache.py                    # Cache manager Google Sheets
│   ├── config.py                   # Configurazione
│   ├── achievements.py             # Sistema achievement (NEW!)
│   ├── setup_achievements.py       # Script setup sheets (NEW!)
│   │
│   ├── import_onepiece.py        # Import One Piece (CSV)
│   ├── import_riftbound.py         # Import Riftbound (CSV Multi-Round) (UPDATED!)
│   ├── import_pokemon.py        # Import Pokémon (TDF)
│   │
│   ├── stats_builder.py            # Builder statistiche
│   ├── stats_cache.py              # Cache file stats
│   │
│   ├── templates/                  # Template HTML
│   │   ├── base.html               # Layout base + menu
│   │   ├── landing.html            # Homepage
│   │   ├── classifiche_page.html   # Lista classifiche (NEW!)
│   │   ├── classifica.html         # Classifica singola stagione
│   │   ├── player.html             # Profilo giocatore + achievement (UPDATED!)
│   │   ├── players.html            # Lista giocatori
│   │   ├── achievements.html       # Pagina achievement (NEW!)
│   │   ├── stats.html              # Stats avanzate
│   │   ├── pulse.html              # Pulse (KPI)
│   │   ├── tales.html              # Tales (narrative)
│   │   ├── hall.html               # Hall of Fame
│   │   └── error.html              # Error page
│   │
│   └── static/                     # Assets
│       ├── style.css
│       └── logo.png
│
└── docs/                           # Documentazione (NEW!)
    ├── SETUP.md
    ├── IMPORT_GUIDE.md
    ├── ACHIEVEMENT_SYSTEM.md
    └── TROUBLESHOOTING.md
```

---

## 🔧 Manutenzione

### Backup Google Sheets

Il sistema crea backup automatici in `Backup_Log` sheet ogni import.

**Backup manuale:**
1. Google Sheets → File → Make a copy
2. Salva con data: `TanaLeague_Backup_2024-11-17`

### Cache Refresh

Cache si aggiorna automaticamente ogni 5 minuti.

**Refresh manuale:**
- Visita `/api/refresh` (classifiche)
- Visita `/api/stats/refresh/<scope>` (stats)

### Aggiungere Achievement

1. Apri `Achievement_Definitions` sheet
2. Aggiungi riga con: `achievement_id`, `name`, `description`, `category`, `rarity`, `emoji`, `points`, `requirement_type`, `requirement_value`
3. Modifica `achievements.py` per logica unlock (se `requirement_type=special`)

### Nuova Stagione

1. Apri `Config` sheet
2. Aggiungi riga: `season_id` (es. OP13), `tcg`, `name`, `season_num`, `status=ACTIVE`
3. Imposta vecchia stagione a `status=CLOSED`
4. (Opzionale) Vecchie stagioni → `status=ARCHIVED` per nasconderle

---

## 🛡️ Sicurezza

- **Service Account**: Credenziali Google in file separato (non in git!)
- **SHEET_ID**: Hardcoded negli script (cambia per deploy)
- **API Limits**: Google Sheets ha rate limits (100 req/100sec)
- **Cache**: Riduce chiamate API con cache 5 min
- **No SQL Injection**: Google Sheets non vulnerabile

---

## 📊 Statistiche Progetto

- **Linee di codice**: ~10,000+
- **File Python**: 12
- **Template HTML**: 16
- **Achievement**: 40
- **TCG Supportati**: 3
- **Stagioni Gestite**: 15+
- **Giocatori Attivi**: 50+
- **Tornei Totali**: 100+

---

## 🙏 Credits

- **Flask**: Web framework
- **Google Sheets API**: Database backend
- **Bootstrap 5**: Frontend framework
- **Font Awesome**: Icone
- **pandas**: Data manipulation
- **gspread**: Google Sheets Python client

---

## 📜 License

Progetto privato - Tutti i diritti riservati © 2024 La Tana delle Pulci

---

## 🤝 Supporto

**La Tana delle Pulci**
Viale Adamello 1, Lecco
Instagram: [@latanadellepulci](https://www.instagram.com/latanadellepulci/)

Per bug o feature request: Apri issue su GitHub

---

**Made with ❤️ for the TCG community**

*Last updated: November 2024 (v2.0 - Achievement System Release)*
