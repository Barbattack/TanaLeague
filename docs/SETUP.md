# 🔧 Setup e Installazione TanaLeague

Guida completa per configurare TanaLeague da zero, sia in locale che su PythonAnywhere.

---

## 📋 Indice

- [Prerequisiti](#-prerequisiti)
- [Google Cloud Setup](#-google-cloud-setup)
- [Google Sheets Setup](#-google-sheets-setup)
- [Installazione Locale](#-installazione-locale)
- [Deploy PythonAnywhere](#-deploy-pythonanywhere)
- [Achievement System Setup](#-achievement-system-setup)
- [Configurazione Stagioni](#-configurazione-stagioni)
- [Verifica Setup](#-verifica-setup)

---

## 📌 Prerequisiti

### Software Richiesto

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/) (opzionale, per clonare repo)
- **Editor di testo** - VSCode, Sublime, etc.
- **Browser moderno** - Per Google Cloud Console e Sheets

### Account Necessari

- **Google Cloud Account** - Per Sheets API
- **PythonAnywhere Account** - Per deploy online (opzionale per sviluppo locale)

---

## ☁️ Google Cloud Setup

### 1. Crea Progetto Google Cloud

1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Click su **Select a Project** → **New Project**
3. Nome progetto: `TanaLeague` (o altro nome)
4. Click **Create**

### 2. Abilita Google Sheets API

1. Nel progetto creato, vai su **APIs & Services** → **Library**
2. Cerca **Google Sheets API**
3. Click **Enable**

### 3. Crea Service Account

1. Vai su **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Nome: `tanaleague-service`
4. Role: **Editor** (o **Owner** se hai permessi)
5. Click **Done**

### 4. Genera Credenziali JSON

1. Nella lista **Service Accounts**, click sul service account appena creato
2. Vai su tab **Keys**
3. Click **Add Key** → **Create New Key**
4. Formato: **JSON**
5. Click **Create**
6. Il file JSON viene scaricato automaticamente
7. **IMPORTANTE**: Rinomina il file in `service_account_credentials.json`

**⚠️ SICUREZZA**: Non committare mai questo file su git! Aggiungi a `.gitignore`:

```bash
echo "service_account_credentials.json" >> .gitignore
```

---

## 📊 Google Sheets Setup

### 1. Crea Google Sheet

1. Vai su [Google Sheets](https://sheets.google.com/)
2. Click **Blank** per creare nuovo foglio
3. Rinomina: `TanaLeague_Database`

### 2. Condividi con Service Account

1. Apri il file `service_account_credentials.json` appena scaricato
2. Copia il valore del campo `client_email` (es. `tanaleague-service@project-id.iam.gserviceaccount.com`)
3. Nel Google Sheet, click **Share** in alto a destra
4. Incolla l'email del service account
5. Permessi: **Editor**
6. **DESELEZIONA** "Notify people"
7. Click **Share**

### 3. Copia SHEET_ID

Dalla URL del Google Sheet:
```
https://docs.google.com/spreadsheets/d/1abc123def456ghi789/edit#gid=0
                                      ^^^^^^^^^^^^^^^^^^^^
                                      Questo è il SHEET_ID
```

**Annotalo**: Lo userai nella configurazione.

### 4. Crea Fogli Base

Crea i seguenti fogli (tab) nel Google Sheet:

| Nome Foglio | Descrizione |
|-------------|-------------|
| **Config** | Configurazione stagioni e parametri |
| **Tournaments** | Lista tornei importati |
| **Results** | Risultati individuali giocatori |
| **Players** | Anagrafica giocatori |
| **Seasonal_Standings_PROV** | Classifiche stagioni ACTIVE |
| **Seasonal_Standings_FINAL** | Classifiche stagioni CLOSED |
| **Vouchers** | Buoni negozio (solo One Piece) |
| **Pokemon_Matches** | Match H2H Pokemon (opzionale) |
| **Backup_Log** | Log backup automatici |

**Achievement sheets** (creati automaticamente da `setup_achievements.py`):
- `Achievement_Definitions`
- `Player_Achievements`

### 5. Popola Config Sheet

Nel foglio **Config**, crea header (riga 1-3) e aggiungi stagioni:

**Header (righe 1-3)**:
```
Row 1: [Lasciare vuota - spazio intestazione]
Row 2: season_id | tcg | name | season_num | status | ...
Row 3: [Eventuali descrizioni]
Row 4+: Dati stagioni
```

**Esempio stagioni (da riga 4)**:
```
season_id    tcg   name              season_num  status    entry_fee  pack_cost  drop_logic  drop_threshold
OP12         OP    OP12 - Lecco      12          ACTIVE    5          4          best_n_minus_2  8
OP11         OP    OP11 - Lecco      11          CLOSED    5          4          best_n_minus_2  8
PKM-FS25     PKM   Fall Season 2025  1           ACTIVE    0          0          best_n_minus_2  8
RFB01        RFB   Riftbound S1      1           ACTIVE    0          0          best_n_minus_2  8
```

**Colonne Config**:
- `season_id`: ID univoco (es. OP12, PKM-FS25, RFB01)
- `tcg`: Gioco (OP, PKM, RFB)
- `name`: Nome descrittivo stagione
- `season_num`: Numero stagione progressivo
- `status`: ACTIVE, CLOSED, ARCHIVED
- `entry_fee`: Quota iscrizione (€) - solo per OP
- `pack_cost`: Costo busta (€) - solo per OP
- `drop_logic`: Formula scarto (best_n_minus_2)
- `drop_threshold`: Tornei minimi per scarto (8)

---

## 💻 Installazione Locale

### 1. Clone Repository

```bash
git clone <repository-url>
cd TanaLeague
```

Oppure download ZIP da GitHub e decomprimi.

### 2. Crea Virtual Environment (Consigliato)

```bash
# Su Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Su Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Installa Dipendenze

```bash
pip install -r requirements.txt
```

**Dipendenze principali**:
```
flask==2.3.0
gspread==5.10.0
google-auth==2.22.0
pandas==2.0.3
pdfplumber==0.10.2
```

### 4. Configura Credenziali

Copia il file `service_account_credentials.json` nella cartella `tanaleague2/`:

```bash
cp /path/to/service_account_credentials.json tanaleague2/
```

**Verifica posizione**:
```
TanaLeague/
├── tanaleague2/
│   ├── service_account_credentials.json  ← QUI
│   ├── app.py
│   ├── ...
```

### 5. Configura SHEET_ID

Apri `tanaleague2/config.py` e modifica:

```python
# config.py
SHEET_ID = "1abc123def456ghi789"  # ← Sostituisci con il tuo SHEET_ID
```

Oppure modifica direttamente negli import scripts se non hai `config.py`:

```python
# In import_onepiece.py, import_pokemon.py, import_riftbound.py
SHEET_ID = "1abc123def456ghi789"  # ← Inserisci il tuo
```

### 6. Test Connessione

Test rapido per verificare connessione Google Sheets:

```bash
cd tanaleague2
python3
```

```python
>>> import gspread
>>> from google.oauth2.service_account import Credentials
>>>
>>> SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
>>> creds = Credentials.from_service_account_file('service_account_credentials.json', scopes=SCOPES)
>>> client = gspread.authorize(creds)
>>> sheet = client.open_by_key('1abc123def456ghi789')  # Tuo SHEET_ID
>>> print(sheet.title)
TanaLeague_Database
>>> exit()
```

Se vedi il nome del foglio, **la connessione funziona!** ✅

### 7. Run App Locale

```bash
cd tanaleague2
python app.py
```

Output atteso:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

Apri browser su `http://localhost:5000` per vedere la webapp.

**Per fermare**: `Ctrl+C` nel terminale

---

## 🌐 Deploy PythonAnywhere

### 1. Crea Account

1. Vai su [PythonAnywhere](https://www.pythonanywhere.com/)
2. Sign up (free tier va bene per test)
3. Verifica email

### 2. Upload Files

**Opzione A: Git (consigliato)**

Nel Bash console di PythonAnywhere:

```bash
cd ~
git clone <repository-url>
cd TanaLeague
```

**Opzione B: Upload Manuale**

1. Tab **Files**
2. Naviga in `/home/yourusername/`
3. Upload cartella `TanaLeague` (file by file o ZIP)

### 3. Upload Credenziali

**IMPORTANTE**: Non caricare `service_account_credentials.json` tramite git!

1. Tab **Files**
2. Naviga in `/home/yourusername/TanaLeague/tanaleague2/`
3. Click **Upload a file**
4. Seleziona `service_account_credentials.json` dal tuo computer

### 4. Installa Dipendenze

Apri **Bash console** in PythonAnywhere:

```bash
cd ~/TanaLeague
pip install --user -r requirements.txt
```

**Note**:
- Usa `pip` (non `pip3`)
- Flag `--user` installa nel tuo spazio utente
- Tempo richiesto: 2-5 minuti

### 5. Configura Web App

1. Tab **Web**
2. Click **Add a new web app**
3. Framework: **Flask**
4. Python version: **3.8** o superiore
5. Path: `/home/yourusername/TanaLeague/tanaleague2/app.py`

### 6. Configura WSGI File

Nel tab **Web**, click su **WSGI configuration file** link.

Sostituisci contenuto con:

```python
import sys

# Aggiungi path progetto
sys.path.insert(0, '/home/yourusername/TanaLeague/tanaleague2')

# Import app Flask
from app import app as application
```

**⚠️ IMPORTANTE**: Sostituisci `yourusername` con il tuo username PythonAnywhere!

Save file (`Ctrl+S` o click Save).

### 7. Configura Static Files (Opzionale)

Nel tab **Web**, sezione **Static files**:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/TanaLeague/tanaleague2/static/` |

### 8. Reload Web App

Nel tab **Web**, click grande pulsante verde **Reload**.

Attendi 10-20 secondi.

### 9. Test Online

Apri URL: `https://yourusername.pythonanywhere.com`

Se vedi la homepage, **deploy completato!** 🎉

---

## 🏅 Achievement System Setup

Dopo aver configurato Google Sheets e app, setup achievement system.

### 1. Run Setup Script

**In locale**:

```bash
cd tanaleague2
python setup_achievements.py
```

**Su PythonAnywhere** (Bash console):

```bash
cd ~/TanaLeague/tanaleague2
python setup_achievements.py
```

### 2. Output Atteso

```
🚀 SETUP ACHIEVEMENT SYSTEM
📋 Connessione a Google Sheets...
   ✅ Sheet: TanaLeague_Database

🔍 Check fogli esistenti...
   ⚠️  Foglio 'Achievement_Definitions' non trovato
   ⚠️  Foglio 'Player_Achievements' non trovato

📝 Creazione fogli...
   ✅ Achievement_Definitions creato
   ✅ Player_Achievements creato

📊 Popolamento Achievement_Definitions...
   ✅ 40 achievement inseriti

✅ SETUP COMPLETATO!

Achievement System pronto all'uso:
- 40 achievement definiti in 7 categorie
- Sheet Player_Achievements pronto per unlock
- Gli achievement verranno sbloccati automaticamente durante import tornei
```

### 3. Verifica Fogli Creati

Apri Google Sheet e verifica esistenza di:
- `Achievement_Definitions` (popolato con 40 achievement)
- `Player_Achievements` (vuoto, header only)

---

## ⚙️ Configurazione Stagioni

### Creare Nuova Stagione

1. Apri Google Sheet
2. Vai su foglio **Config**
3. Aggiungi riga con dati stagione

**Esempio One Piece**:
```
OP13  |  OP  |  OP13 - Primavera 2025  |  13  |  ACTIVE  |  5  |  4  |  best_n_minus_2  |  8
```

**Esempio Pokémon**:
```
PKM-WIN25  |  PKM  |  Winter League 2025  |  2  |  ACTIVE  |  0  |  0  |  best_n_minus_2  |  8
```

**Esempio Riftbound**:
```
RFB02  |  RFB  |  Riftbound Season 2  |  2  |  ACTIVE  |  0  |  0  |  best_n_minus_2  |  8
```

### Status Stagioni

- **ACTIVE**: Stagione corrente, classifiche in Seasonal_Standings_PROV
  - Applica regole competitive (scarto 2 tornei peggiori se >= 8 tornei)
  - Sblocca achievement per i giocatori
  - Visibile in UI (dropdown, liste, classifiche)

- **CLOSED**: Stagione finita, classifiche finali in Seasonal_Standings_FINAL
  - Applica regole competitive (scarto 2 tornei peggiori se >= 8 tornei)
  - Sblocca achievement per i giocatori
  - Visibile in UI (dropdown, liste, classifiche)

- **ARCHIVED**: Stagione vecchia, solo archivio dati
  - **NON** applica scarto tornei peggiori (conta TUTTI i tornei)
  - **NON** sblocca achievement
  - **NASCOSTA** da UI (dropdown, liste)
  - Serve solo per popolare stats aggregate nella webapp

### Chiudere Stagione

Per finalizzare una stagione:

1. Cambia `status` da `ACTIVE` a `CLOSED` nel foglio Config
2. Copia classifiche da `Seasonal_Standings_PROV` a `Seasonal_Standings_FINAL`
3. Rimuovi stagione da `Seasonal_Standings_PROV`

### Archiviare Stagione

Per nascondere stagioni vecchie dall'UI:

1. Cambia `status` da `CLOSED` a `ARCHIVED`
2. Le stagioni ARCHIVED non appariranno in dropdown e liste

---

## ✅ Verifica Setup

### Checklist Completa

- [ ] Google Cloud Project creato
- [ ] Google Sheets API abilitata
- [ ] Service Account creato con credenziali JSON
- [ ] Google Sheet creato e condiviso con service account
- [ ] Fogli base creati (Config, Tournaments, Results, Players, etc.)
- [ ] Config sheet popolato con almeno 1 stagione
- [ ] Repository clonato o scaricato
- [ ] Dipendenze Python installate
- [ ] `service_account_credentials.json` copiato in `tanaleague2/`
- [ ] `SHEET_ID` configurato in `config.py` o import scripts
- [ ] Test connessione Google Sheets riuscito
- [ ] App Flask avviata e accessibile su localhost
- [ ] Achievement system setup completato (40 achievement)
- [ ] (Opzionale) Deploy su PythonAnywhere completato

### Test Import

Prova import di test per verificare tutto funzioni:

**One Piece (CSV)**:

```bash
cd tanaleague2
python import_onepiece.py --csv test_tournament.csv --season OP12 --test
```

**Pokémon (TDF)**:

```bash
python import_pokemon.py --tdf test_tournament.tdf --season PKM-FS25 --test
```

**Riftbound (PDF)**:

```bash
python import_riftbound.py --pdf test_tournament.pdf --season RFB01 --test
```

Se l'output mostra parsing corretto e calcolo punti, **tutto funziona!**

### Test Webapp

Verifica le seguenti pagine:

- `/` - Homepage con 3 TCG cards
- `/classifiche` - Lista tutte le stagioni
- `/classifica/<season_id>` - Classifica singola stagione
- `/players` - Lista giocatori
- `/player/<membership>` - Profilo giocatore
- `/achievements` - Catalogo achievement
- `/stats/<scope>` - Statistiche avanzate

Se tutte le pagine caricano senza errori 500, **webapp OK!**

---

## 🔧 Troubleshooting Setup

### Errore: "gspread.exceptions.APIError: PERMISSION_DENIED"

**Causa**: Service account non ha accesso al Google Sheet

**Soluzione**:
1. Apri `service_account_credentials.json`
2. Copia `client_email`
3. Share Google Sheet con questa email (permessi Editor)

### Errore: "FileNotFoundError: service_account_credentials.json"

**Causa**: File credenziali non nella posizione corretta

**Soluzione**:
```bash
# Verifica posizione file
ls tanaleague2/service_account_credentials.json

# Deve esistere in tanaleague2/, NON in root!
```

### Errore: "ModuleNotFoundError: No module named 'gspread'"

**Causa**: Dipendenze non installate

**Soluzione**:
```bash
pip install -r requirements.txt

# Su PythonAnywhere
pip install --user -r requirements.txt
```

### Errore: "Sheet not found: Achievement_Definitions"

**Causa**: Achievement system non ancora configurato

**Soluzione**:
```bash
cd tanaleague2
python setup_achievements.py
```

### Webapp non carica su PythonAnywhere

**Verifica**:

1. **WSGI file corretto**: Path deve essere assoluto `/home/yourusername/...`
2. **Dipendenze installate**: `pip list` nel Bash console
3. **Error log**: Tab Web → Log files → Error log
4. **Reload**: Click Reload dopo ogni modifica

---

## 📞 Supporto

**Problemi durante setup?**

1. Verifica [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Check error logs (locale: terminale, PythonAnywhere: error log)
3. Apri issue su GitHub con:
   - Comando eseguito
   - Output completo
   - Sistema operativo e Python version

---

**Setup completato! Ora puoi:**
- ✅ Importare tornei per i 3 TCG
- ✅ Vedere classifiche aggiornate
- ✅ Tracciare achievement giocatori
- ✅ Visualizzare statistiche avanzate

Prossimo step → [IMPORT_GUIDE.md](IMPORT_GUIDE.md) 🚀
