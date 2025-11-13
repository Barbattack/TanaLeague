# TanaLeague

**Sistema di gestione classifiche e statistiche per leghe competitive di Trading Card Games (TCG)**

Web app Flask per tracciare tornei, classifiche, statistiche avanzate e profili giocatori per One Piece TCG e Pokémon TCG.

🌐 **Live:** [latanadellepulci.pythonanywhere.com](https://latanadellepulci.pythonanywhere.com)

---

## 📋 Indice

- [Caratteristiche](#-caratteristiche)
- [Architettura](#-architettura)
- [Setup](#-setup)
- [Configurazione](#-configurazione)
- [Import Tornei](#-import-tornei)
- [Deploy su PythonAnywhere](#-deploy-su-pythonanywhere)
- [Manutenzione](#-manutenzione)
- [Sicurezza](#-sicurezza)
- [Struttura Progetto](#-struttura-progetto)

---

## ✨ Caratteristiche

### Funzionalità Principali
- **Classifiche stagionali** - Rankings giocatori per stagione (OP01, OP12, PKM-FS25, ecc.)
- **Statistiche avanzate** - MVP, Sharpshooter, Metronome, Phoenix, Big Stage, Closer
- **Profili giocatori** - Storico completo, win rate, trend, grafici
- **Analytics** - Pulse (KPI), Tales (narrative), Hall of Fame
- **Import automatico** - Da CSV (One Piece) e TDF/XML (Pokémon)
- **Cache intelligente** - Aggiornamento automatico ogni 5 minuti

### TCG Supportati
- 🏴‍☠️ **One Piece TCG** - Sistema punti semplice (W=3, L=0)
- ⚡ **Pokémon TCG** - Sistema punti con pareggi (W=3, T=1, L=0) + match tracking H2H

---

## 🏗️ Architettura

```
┌─────────────────┐
│  Google Sheets  │  ← Database (Config, Results, Players, Tournaments)
└────────┬────────┘
         │ (gspread API)
         ↓
┌─────────────────┐
│   Flask App     │  ← Backend Python
│   + Cache       │  ← Cache locale (refresh ogni 5 min)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Jinja2 HTML    │  ← Frontend (templates + CSS)
└─────────────────┘
```

**Stack Tecnologico:**
- **Backend:** Python 3.10+, Flask 3.0.0
- **Database:** Google Sheets (via gspread 5.12.0)
- **Auth:** Google Service Account
- **Cache:** JSON file-based
- **Frontend:** HTML5, CSS3, Jinja2, Chart.js
- **Hosting:** PythonAnywhere (free tier)

**Perché Google Sheets come database?**
- ✅ Facile da editare manualmente
- ✅ Visualizzazione dati immediata
- ✅ Formule Excel/Sheets native
- ✅ No costi database
- ⚠️ Limite: ~1000 righe consigliato per performance

---

## 🚀 Setup

### Prerequisiti
- Python 3.10+
- Account Google Cloud (per service account)
- Google Sheet configurato

### 1. Clone Repository
```bash
git clone https://github.com/Barbattack/TanaLeague.git
cd TanaLeague/tanaleague2
```

### 2. Installa Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Configura Credenziali

**IMPORTANTE:** Non usare mai credenziali reali su GitHub!

#### Crea Service Account Google:
1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea progetto (o usa esistente)
3. Abilita Google Sheets API
4. IAM & Admin → Service Accounts → Create
5. Scarica JSON key → salvalo come `secrets/service_account.json`
6. Condividi il Google Sheet con l'email del service account (con ruolo Editor)

#### Crea config.py:
```bash
cp config.example.py config.py
```

Modifica `config.py`:
```python
SHEET_ID = "TUO_GOOGLE_SHEET_ID"  # Dall'URL del foglio
CREDENTIALS_FILE = "secrets/service_account.json"
ADMIN_USER = "tuo_username"
ADMIN_PASS = "password_sicura"  # Cambia!
SECRET_KEY = "genera_chiave_casuale"  # python -c "import secrets; print(secrets.token_hex(32))"
DEBUG = True  # False in produzione
```

### 4. Struttura Google Sheet

Il tuo Google Sheet deve avere questi fogli (worksheets):

**Config** - Configurazione stagioni
```
Season_ID | TCG | Season_Name              | Start_Date | Status | Next_Tournament
OP12      | OP  | One Piece Serie 12       | 2024-01-01 | ACTIVE | 2024-12-15
PKM-FS25  | PKM | Pokemon Fiamme Spettrali | 2025-11-01 | ACTIVE | 2025-11-20
```

**Players** - Anagrafica giocatori
```
Membership | Name       | Join_Date  | ...
PLCI001   | Mario Rossi | 2024-01-01 | ...
```

**Results** - Risultati tornei
```
Season_ID | Tournament_ID  | Membership | Rank | Points | OMW% | ...
OP12      | OP12_2024-11-01| PLCI001   | 1    | 12.0   | 66.7 | ...
```

**Tournaments** - Metadata tornei
```
Season_ID | Tournament_ID  | Date       | Winner  | Participants
OP12      | OP12_2024-11-01| 2024-11-01 | PLCI001 | 24
```

**Seasonal_Standings_PROV** / **FINAL** - Classifiche calcolate (auto-generate)

### 5. Run Locale
```bash
python app.py
```

Vai su: http://localhost:5000

---

## ⚙️ Configurazione

### Cache Settings
```python
CACHE_REFRESH_MINUTES = 5  # Minuti tra refresh automatici
CACHE_FILE = "cache_data.json"  # File cache locale
```

La cache:
- Si aggiorna automaticamente ogni 5 minuti
- Riduce chiamate API a Google Sheets
- Può essere invalidata manualmente via `/api/refresh`

### Refresh Manuale Cache
```bash
# Cache classifiche
curl https://tuodominio.com/api/refresh

# Cache stats (per una stagione)
curl https://tuodominio.com/api/stats/refresh/OP12
```

---

## 📥 Import Tornei

### One Piece TCG (CSV)

Usa lo script `import_tournament.py`:

```bash
python import_tournament.py --csv torneo_novembre.csv --season OP12
```

**Formato CSV richiesto:**
```csv
Membership,Name,Rank,Points,OMW%,Record
PLCI001,Mario Rossi,1,12.0,66.7,4-0
PLCI002,Luigi Verdi,2,9.0,55.5,3-1
```

### Pokémon TCG (TDF/XML)

Usa lo script `parse_pokemon_tdf.py`:

```bash
# Test (dry-run)
python parse_pokemon_tdf.py --tdf torneo.tdf --season PKM-FS25 --test

# Import reale
python parse_pokemon_tdf.py --tdf torneo.tdf --season PKM-FS25
```

**Differenze Pokémon:**
- Sistema punti con pareggi (W=3, T=1, L=0)
- Tracking match-by-match (H2H disponibile)
- OMW% calcolato da match reali
- File .TDF esportato da Pokémon Tournament Manager

**Nomenclatura stagioni Pokémon:**
```
PKM-FS25  = Fiamme Spettrali 2025
PKM-SR25  = Scarlatto Rombo 2025
PKM-XX##  = [Codice Espansione][Anno]
```

📖 Vedi: `GUIDA_POKEMON_IMPORT.txt` per dettagli completi

---

## 🌐 Deploy su PythonAnywhere

### Setup Iniziale

1. **Crea account** su [PythonAnywhere](https://www.pythonanywhere.com)

2. **Upload files:**
```bash
# Comprimi il progetto (escludi file sensibili!)
zip -r tanaleague.zip tanaleague2/ -x "*.pyc" "*__pycache__*" "*.json" "secrets/*"

# Upload su PythonAnywhere via Files tab
```

3. **Installa dipendenze:**
```bash
pip3 install --user Flask gspread google-auth pandas
```

4. **Configura WSGI:**

Web tab → WSGI configuration file → Incolla:
```python
import sys

path = '/home/TUOUSERNAME/tanaleague2'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
```

5. **Upload credenziali:**
- Crea cartella: `/home/TUOUSERNAME/tanaleague2/secrets/`
- Upload `service_account.json` nella cartella secrets
- Upload anche copia come `service_account_credentials.json` nella root

6. **Crea config.py:**
```bash
cp config.example.py config.py
# Modifica config.py con i tuoi valori
```

7. **Reload webapp:**

Web tab → pulsante verde "Reload"

📖 Vedi: `SETUP_PYTHONANYWHERE.txt` per guida dettagliata

---

## 🛠️ Manutenzione

### Aggiornare il Codice

**Su GitHub (development):**
```bash
git pull origin main
# Modifica i file
git add .
git commit -m "Descrizione modifiche"
git push origin main
```

**Su PythonAnywhere (production):**
1. Scarica i file modificati da GitHub
2. Upload su PythonAnywhere (Files tab)
3. Oppure usa git direttamente:
```bash
cd ~/tanaleague2
git pull origin main
```
4. Reload webapp (Web tab)

### Backup

**Backup Google Sheet:**
- File → Scarica → Excel (.xlsx)
- Frequenza consigliata: settimanale

**Backup File Locali:**
```bash
# Su PythonAnywhere console
cd ~
tar -czf backup_$(date +%Y%m%d).tar.gz tanaleague2/
```

### Monitoring

**Check salute app:**
```bash
curl https://latanadellepulci.pythonanywhere.com/ping
# Risposta: "pong" = OK
```

**Log errors:**
- PythonAnywhere: Web tab → Error log
- Controlla se ci sono errori di connessione a Google Sheets

---

## 🔒 Sicurezza

### ⚠️ FILE DA NON COMMITTARE MAI

Il `.gitignore` protegge automaticamente questi file:

```
secrets/                      # Credenziali Google
service_account*.json         # Tutte le chiavi
config.py                     # Password e API keys
cache_data.json               # Dati cache (possono contenere info sensibili)
__pycache__/                  # File Python compilati
```

### 🔐 Best Practices

1. **Credenziali Google:**
   - Usa SEMPRE service account (mai OAuth user)
   - Ruota chiavi ogni 6-12 mesi
   - Se compromesse, disabilita immediatamente e crea nuovo service account

2. **Password Admin:**
   - Usa password forte (min 16 caratteri)
   - Cambia password di default in `config.py`
   - Considera di implementare autenticazione 2FA

3. **Google Sheet:**
   - Condividi SOLO con service account email
   - NON rendere pubblico il foglio
   - Usa permessi "Editor" (non "Owner") per service account

4. **PythonAnywhere:**
   - DEBUG = False in produzione
   - Proteggi account con password forte
   - Abilita 2FA se disponibile

### 🚨 In Caso di Compromissione

Se le credenziali vengono esposte:

1. **Immediato:** Disabilita service account su Google Cloud Console
2. Crea nuovo service account
3. Scarica nuove credenziali
4. Condividi Google Sheet con nuovo service account
5. Upload nuove credenziali su PythonAnywhere
6. Reload webapp
7. Verifica che tutto funzioni
8. Elimina vecchio service account

---

## 📁 Struttura Progetto

```
TanaLeague/
├── README.md                          # Questo file
├── LICENSE                            # CC0 1.0 Universal
├── .gitignore                         # File da ignorare
│
└── tanaleague2/                       # Main app directory
    ├── app.py                         # Flask app principale
    ├── cache.py                       # Cache manager (Google Sheets)
    ├── stats_builder.py               # Statistiche avanzate
    ├── stats_cache.py                 # Cache statistiche
    │
    ├── config.example.py              # Template configurazione
    ├── requirements.txt               # Dipendenze Python
    ├── wsgi_config.py                 # WSGI entry point
    │
    ├── import_tournament.py           # Import One Piece (CSV)
    ├── parse_pokemon_tdf.py           # Import Pokémon (TDF)
    │
    ├── SETUP_PYTHONANYWHERE.txt       # Guida deploy
    ├── GUIDA_POKEMON_IMPORT.txt       # Guida import Pokémon
    │
    ├── templates/                     # Template HTML
    │   ├── base.html                  # Template base
    │   ├── landing.html               # Homepage
    │   ├── classifica.html            # Classifiche
    │   ├── stats.html                 # Statistiche
    │   ├── player.html                # Profilo giocatore
    │   ├── players.html               # Lista giocatori
    │   └── error.html                 # Pagina errore
    │
    ├── static/                        # File statici
    │   ├── style.css                  # CSS principale
    │   └── logo.png                   # Logo
    │
    └── secrets/                       # Credenziali (NON in Git!)
        └── service_account.json       # Credenziali Google (gitignored)
```

### File Principali

| File | Descrizione |
|------|-------------|
| `app.py` | Flask routes, logica principale webapp |
| `cache.py` | Gestione cache e connessione Google Sheets |
| `stats_builder.py` | Calcolo statistiche avanzate (MVP, Sharpshooter, ecc.) |
| `import_tournament.py` | Script import tornei One Piece da CSV |
| `parse_pokemon_tdf.py` | Script import tornei Pokémon da TDF/XML |
| `config.py` | Configurazione (NON committare) |

---

## 🤝 Contribuire

Questo progetto è attualmente privato/personale. Per suggerimenti o bug:
- Apri una Issue su GitHub
- Contatta il maintainer

---

## 📄 Licenza

**CC0 1.0 Universal** - Public Domain

Puoi copiare, modificare, distribuire ed eseguire l'opera, anche per scopi commerciali, senza chiedere il permesso.

---

## 🙏 Credits

**Sviluppato con ❤️ per la community TCG italiana**

- Flask Documentation
- gspread Library
- Google Sheets API
- PythonAnywhere
- Claude Code (per setup e sicurezza)

---

## 📞 Support

Per domande o problemi:
1. Controlla questa documentazione
2. Leggi i file di guida specifici (SETUP_PYTHONANYWHERE.txt, GUIDA_POKEMON_IMPORT.txt)
3. Controlla i log di errore su PythonAnywhere
4. Apri una Issue su GitHub

---

**🚀 Buon divertimento con TanaLeague!**
