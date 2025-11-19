# 🔧 Troubleshooting - TanaLeague

Guida completa alla risoluzione dei problemi comuni in TanaLeague.

---

## 📋 Indice

- [Errori Google Sheets](#-errori-google-sheets)
- [Errori Import Tornei](#-errori-import-tornei)
- [Errori Webapp](#-errori-webapp)
- [Errori Achievement](#-errori-achievement)
- [Errori PythonAnywhere](#-errori-pythonanywhere)
- [Problemi Performance](#-problemi-performance)
- [Debug Generale](#-debug-generale)

---

## 📊 Errori Google Sheets

### `gspread.exceptions.APIError: PERMISSION_DENIED`

**Messaggio completo**:
```
gspread.exceptions.APIError: {
  "error": {
    "code": 403,
    "message": "The caller does not have permission",
    "status": "PERMISSION_DENIED"
  }
}
```

**Causa**: Service account non ha accesso al Google Sheet

**Soluzione**:

1. Apri file `service_account_credentials.json`
2. Trova e copia il valore di `client_email`:
   ```json
   {
     "client_email": "tanaleague-service@project-123456.iam.gserviceaccount.com"
   }
   ```
3. Apri Google Sheet in browser
4. Click **Share** in alto a destra
5. Incolla la `client_email`
6. Permessi: **Editor**
7. **DESELEZIONA** "Notify people"
8. Click **Share**

**Verifica**: Riprova comando, dovrebbe funzionare.

---

### `gspread.exceptions.SpreadsheetNotFound`

**Messaggio**:
```
gspread.exceptions.SpreadsheetNotFound: Spreadsheet not found
```

**Causa**: `SHEET_ID` errato o foglio cancellato

**Soluzione**:

1. Verifica URL del Google Sheet:
   ```
   https://docs.google.com/spreadsheets/d/1abc123def456ghi789/edit
                                         ^^^^^^^^^^^^^^^^^^^^
                                         SHEET_ID corretto
   ```
2. Apri `tanaleague2/config.py` (o script import) e verifica:
   ```python
   SHEET_ID = "1abc123def456ghi789"  # Deve corrispondere!
   ```
3. Se il foglio è stato cancellato, ricrea da backup

---

### `gspread.exceptions.WorksheetNotFound: Worksheet not found`

**Messaggio**:
```
gspread.exceptions.WorksheetNotFound: Achievement_Definitions
```

**Causa**: Foglio (tab) richiesto non esiste nel Google Sheet

**Soluzione per Achievement sheets**:
```bash
cd tanaleague2
python setup_achievements.py
```

**Soluzione per altri fogli**:

Crea manualmente il foglio mancante nel Google Sheet:
- `Config`
- `Tournaments`
- `Results`
- `Players`
- `Seasonal_Standings_PROV`
- `Seasonal_Standings_FINAL`
- `Vouchers` (One Piece)
- `Pokemon_Matches` (Pokemon)
- `Backup_Log`

---

### `gspread.exceptions.APIError: RESOURCE_EXHAUSTED`

**Messaggio**:
```
gspread.exceptions.APIError: {
  "error": {
    "code": 429,
    "message": "Quota exceeded for quota metric 'Read requests'",
    "status": "RESOURCE_EXHAUSTED"
  }
}
```

**Causa**: Troppi request a Google Sheets API in poco tempo (rate limit 100 req/100sec)

**Soluzione**:

1. **Aspetta 1-2 minuti** prima di riprovare
2. Evita import multipli simultanei
3. Usa cache webapp (auto-refresh ogni 5 min)
4. Se persistente, verifica loop infiniti in codice

**Prevenzione**:
- Non fare refresh continui della webapp
- Usa `--test` mode prima di import reali
- Batch import con pause

---

## 📥 Errori Import Tornei

### `ValueError: Date format not recognized in filename`

**Messaggio**:
```
ValueError: Date format not recognized in filename: torneo_one_piece.csv
Expected formats: YYYY_MM_DD, DD_MM_YYYY, YYYY-MM-DD, DD_Month_YYYY
```

**Causa**: Nome file CSV (One Piece) non contiene data in formato riconosciuto

**Soluzione**:

Rinomina file in uno dei formati supportati:
- `2025_06_12_OP12.csv`
- `12_06_2025_OP12.csv`
- `2025-06-12_OP12.csv`
- `12_June_2025_OP12.csv`

**Comando**:
```bash
mv torneo_one_piece.csv 2025_06_12_OP12.csv
```

---

### `FileNotFoundError: [Errno 2] No such file or directory`

**Messaggio**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'path/to/file.csv'
```

**Causa**: Path del file errato o file non esiste

**Soluzione**:

1. Verifica file esiste:
   ```bash
   ls path/to/file.csv
   ```

2. Usa path assoluto se relativo non funziona:
   ```bash
   # Relativo (potrebbe fallire)
   python import_tournament.py --csv ../files/tournament.csv --season OP12

   # Assoluto (più sicuro)
   python import_tournament.py --csv /home/user/files/tournament.csv --season OP12
   ```

3. Controlla current working directory:
   ```bash
   pwd
   # Deve essere: .../TanaLeague/tanaleague2
   ```

---

### `KeyError: 'Ranking'` (o altra colonna CSV)

**Messaggio**:
```
KeyError: 'Ranking'
```

**Causa**: CSV non ha le colonne attese (One Piece)

**Soluzione**:

Verifica header CSV:
```csv
Ranking,User Name,Membership Number,Win Points,OMW %,Record
```

**Colonne obbligatorie One Piece**:
- `Ranking`
- `User Name`
- `Membership Number`
- `Win Points`
- `OMW %`
- `Record`

Se export da Limitlesstcg è diverso, modifica header manualmente o aggiorna script parsing.

---

### `pdfplumber error: No tables found in PDF` (Riftbound)

**Messaggio**:
```
🔍 Parsing PDF: tournament.pdf
🔍 Strategia 1: Estrazione tabelle...
  📊 Pagina 1: 0 tabelle trovate
⚠️  Nessuna tabella trovata nel PDF
```

**Causa**: PDF non ha tabelle strutturate o formato non riconosciuto

**Soluzione**:

1. **Verifica PDF contiene tabelle** (non solo testo):
   - Apri PDF in viewer
   - Le colonne devono essere allineate e separate

2. **Controlla formato tabella**:
   ```
   Rank | Name (Nickname) | Points | W-L-D | OMW%
   1    | Rossi, M (nick) | 12     | 4-0-0 | 65%
   ```

3. **Nickname tra parentesi obbligatorio**:
   - ✅ `Rossi, Mario (HotelMotel)`
   - ❌ `Rossi, Mario HotelMotel` (mancano parentesi)

4. **Ri-esporta PDF** dal software con tabelle strutturate

5. **Debug avanzato**:
   ```python
   import pdfplumber
   with pdfplumber.open('tournament.pdf') as pdf:
       page = pdf.pages[0]
       tables = page.extract_tables()
       print(f"Tables found: {len(tables)}")
       if tables:
           print(tables[0])  # Prima tabella
   ```

---

### `Torneo già importato - Sovrascrivere? (y/n)`

**Messaggio**:
```
⚠️  ATTENZIONE: Torneo OP12_2025-06-12 già esistente!
Sovrascrivere dati esistenti? (y/n):
```

**Causa**: Tournament ID già presente in foglio `Tournaments`

**Opzioni**:

1. **Rispondi `y`**: Sovrascrive dati esistenti (backup automatico creato)
2. **Rispondi `n`**: Annulla import
3. **Cambia data** nel filename se è torneo diverso:
   ```bash
   mv 2025_06_12_OP12.csv 2025_06_13_OP12.csv
   ```

**Verifica backup**: Dopo sovrascrittura, check foglio `Backup_Log` per restore se necessario

---

### `ValueError: invalid literal for int() with base 10` (Pokemon TDF)

**Causa**: TDF file corrotto o formato inaspettato

**Soluzione**:

1. Verifica file TDF è XML valido:
   ```bash
   file tournament.tdf
   # Output atteso: XML document text
   ```

2. Apri con editor e verifica struttura:
   ```xml
   <?xml version="1.0"?>
   <tournament>
     <name>Pokemon League</name>
     <players>...</players>
     <standings>...</standings>
   </tournament>
   ```

3. Ri-esporta da Play! Pokémon Tournament software

4. Usa `--test` mode per debug:
   ```bash
   python parse_pokemon_tdf.py --tdf tournament.tdf --season PKM-FS25 --test
   ```

---

## 🌐 Errori Webapp

### `500 Internal Server Error`

**Causa**: Errore Python nel backend (variabili non definite, import fallito, etc.)

**Debug locale**:

1. Guarda terminale dove hai lanciato `python app.py`:
   ```
   Traceback (most recent call last):
     File "app.py", line 123, in index
       season = seasons[0]
   IndexError: list index out of range
   ```

2. Identifica errore e correggi

**Debug PythonAnywhere**:

1. Tab **Web** → sezione **Log files**
2. Click su **error log**
3. Scorri in fondo per vedere errore recente
4. Correggi codice e **Reload** webapp

**Errori comuni**:
- Foglio Google Sheet mancante
- SHEET_ID errato in `config.py`
- Credenziali JSON mancanti o path errato

---

### `TemplateNotFound: landing.html`

**Causa**: Template HTML non trovato o in path errato

**Soluzione**:

Verifica struttura directory:
```
tanaleague2/
├── app.py
├── templates/         ← Cartella templates DEVE esistere
│   ├── base.html
│   ├── landing.html
│   ├── classifica.html
│   └── ...
```

Se manca, crea cartella:
```bash
mkdir -p tanaleague2/templates
```

Su PythonAnywhere, verifica file uploadati correttamente.

---

### Cache non si aggiorna

**Sintomi**: Dati vecchi mostrati dopo import

**Causa**: Cache 5-min attiva

**Soluzione**:

1. **Aspetta 5 minuti** (auto-refresh)
2. **Refresh manuale**: Visita `/api/refresh`
3. **Hard refresh browser**: `Ctrl+Shift+R` (o `Cmd+Shift+R` su Mac)
4. **Svuota cache browser**: Settings → Clear browsing data

**Debug cache**:
```bash
cd tanaleague2
ls -la *.pkl  # File cache

# Elimina cache manualmente
rm *.pkl
```

---

### Nome giocatore visualizzato male

**Sintomi**:
- Pokemon mostra nome completo invece di "Nome I."
- Riftbound mostra nome invece di nickname

**Causa**: TCG non identificato correttamente o filtro template non applicato

**Debug**:

1. Verifica `tcg` in foglio `Players`:
   ```
   membership | tcg  | name
   0000012345 | PKM  | Rossi, Mario
   ```

2. Verifica filtro applicato in template:
   ```html
   <!-- Corretto -->
   {{ player.name | format_player_name(player.tcg, player.membership) }}

   <!-- Errato -->
   {{ player.name }}  <!-- No filtro! -->
   ```

3. Check `format_player_name()` in `app.py`:
   ```python
   @app.template_filter('format_player_name')
   def format_player_name(name, tcg, membership=''):
       # Verifica logica...
   ```

---

## 🏅 Errori Achievement

### Achievement non sbloccati dopo import

**Causa possibile**:
1. Sheet `Player_Achievements` non esiste
2. Achievement già sbloccato
3. Condizione unlock non soddisfatta
4. Errore in `achievements.py`

**Soluzione**:

**1. Verifica sheet esiste**:
```bash
cd tanaleague2
python3
>>> import gspread
>>> from google.oauth2.service_account import Credentials
>>> # Connetti...
>>> sheet.worksheet("Player_Achievements")
```

Se errore, run:
```bash
python setup_achievements.py
```

**2. Check già sbloccato**:

Apri Google Sheet `Player_Achievements`, cerca:
```
membership   | achievement_id
0000012345   | ACH_GLO_001
```

Se esiste, achievement già unlocked (non si può sbloccare 2 volte).

**3. Verifica condizione**:

Esempio `ACH_GLO_002` (King of the Hill - 3 vittorie):
- Apri `Results` sheet
- Filtra per membership del giocatore
- Conta righe con `rank = 1`
- Se < 3, achievement non si sblocca ancora

**4. Debug logica**:

Aggiungi print in `achievements.py`:
```python
def check_simple_achievements(stats, achievements, unlocked):
    to_unlock = []

    print(f"  DEBUG stats: {stats}")  # ← Aggiungi

    for ach_id, ach in achievements.items():
        # ...
```

Ri-esegui import e leggi output.

---

### Warning: `Achievement check failed (non bloccante)`

**Messaggio**:
```
🎮 Check achievement...
⚠️  Errore achievement check (non bloccante): Worksheet not found
```

**Causa**: Achievement sheet mancante ma import procede comunque (errore catturato)

**Soluzione**:
```bash
cd tanaleague2
python setup_achievements.py
```

Ri-importa torneo per sbloccare achievement retroattivamente.

---

### Achievement mostrato in profilo ma senza emoji/descrizione

**Causa**: `Achievement_Definitions` non caricato o ID mismatch

**Soluzione**:

1. Verifica `achievement_id` in `Player_Achievements` corrisponde a ID in `Achievement_Definitions`
2. Refresh cache webapp (`/api/refresh`)
3. Hard refresh browser

**Debug**:

In `app.py` route `/player/<membership>`:
```python
# Verifica achievement definition trovata
for ach_unlocked in unlocked_achievements:
    ach_id = ach_unlocked[1]
    ach_def = [a for a in all_achievements if a[0] == ach_id]
    print(f"DEBUG: {ach_id} → {ach_def}")  # ← Aggiungi
```

---

## 🚀 Errori PythonAnywhere

### `ImportError: No module named 'gspread'`

**Causa**: Dipendenze non installate su PythonAnywhere

**Soluzione**:

Apri **Bash console** in PythonAnywhere:
```bash
cd ~/TanaLeague
pip install --user -r requirements.txt
```

Attendi 2-5 minuti, poi **Reload** webapp.

---

### `FileNotFoundError: service_account_credentials.json`

**Causa**: File credenziali non uploadato o path errato

**Soluzione**:

1. Tab **Files** in PythonAnywhere
2. Naviga in `/home/yourusername/TanaLeague/tanaleague2/`
3. Verifica presenza di `service_account_credentials.json`
4. Se mancante, upload manuale (NO git, per sicurezza!)

**Path atteso**:
```
/home/yourusername/TanaLeague/tanaleague2/service_account_credentials.json
```

---

### WSGI file error: `No module named 'app'`

**Causa**: Path errato in WSGI configuration

**Soluzione**:

Tab **Web** → click su **WSGI configuration file** link

Verifica contenuto:
```python
import sys

# Path DEVE essere assoluto e corretto!
sys.path.insert(0, '/home/yourusername/TanaLeague/tanaleague2')

from app import app as application
```

**⚠️ Sostituisci `yourusername`** con il tuo username PythonAnywhere!

Save (`Ctrl+S`) e **Reload** webapp.

---

### Webapp mostra errore dopo Reload

**Causa**: Errore Python in qualche file

**Debug**:

1. Tab **Web** → **Error log**
2. Leggi ultimi errori:
   ```
   ModuleNotFoundError: No module named 'achievements'
   ```
3. Identifica problema
4. Correggi codice
5. **Reload**

**Tip**: Testa modifiche in locale PRIMA di uploadare su PythonAnywhere!

---

### Modifiche file non visibili dopo upload

**Causa**: File uploadato ma webapp non riavviata

**Soluzione**:

Dopo OGNI modifica a file Python:
1. Tab **Web**
2. Click grande pulsante verde **Reload**
3. Attendi 10-20 secondi
4. Ricarica pagina browser

Per modifiche a **template HTML** o **CSS**, Reload non sempre necessario (solo cache browser).

---

## ⚡ Problemi Performance

### Webapp lenta (loading > 10 sec)

**Causa**: Troppe chiamate a Google Sheets API

**Soluzione**:

1. **Usa cache**: Default 5 min, OK per la maggior parte dei casi
2. **Aumenta TTL cache** in `cache.py`:
   ```python
   CACHE_TTL = 300  # 5 min → 600  # 10 min
   ```
3. **Batch read** invece di read singoli (già implementato)

**Verifica performance**:
- Usa browser DevTools → Network tab
- Identifica chiamate lente
- Ottimizza query Google Sheets

---

### Import script timeout

**Sintomi**: Import si blocca a metà

**Causa**: Torneo molto grande (100+ giocatori) + Google Sheets slow response

**Soluzione**:

1. **Usa `--test` mode** per verificare parsing prima:
   ```bash
   python import_tournament.py --csv huge_tournament.csv --season OP12 --test
   ```

2. **Batch write più piccoli**: Modifica script import per appendere righe in batch da 50 invece di tutte insieme

3. **Aspetta e riprova**: A volte Google Sheets ha slowdown temporanei

---

## 🐛 Debug Generale

### Abilita Debug Mode (Locale)

In `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True)  # ← Debug attivo
```

Output dettagliato in console con traceback completi.

**⚠️ NON attivare in produzione (PythonAnywhere)!**

---

### Print Debug Info

Aggiungi print strategici:

**Esempio in app.py**:
```python
@app.route('/player/<membership>')
def player_profile(membership):
    print(f"DEBUG: Loading player {membership}")  # ← Debug

    player_data = get_player_data(membership)
    print(f"DEBUG: Data loaded: {player_data}")  # ← Debug

    return render_template('player.html', player=player_data)
```

**Esempio in import script**:
```python
print(f"DEBUG: Tournament ID = {tournament_id}")
print(f"DEBUG: Participants = {n_participants}")
```

Leggi output in console (locale) o error log (PythonAnywhere).

---

### Test Connessione Google Sheets

Script test rapido:

```python
# test_connection.py
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = "1abc123def456ghi789"  # Tuo SHEET_ID

creds = Credentials.from_service_account_file(
    'service_account_credentials.json',
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)

print(f"✅ Connesso a: {sheet.title}")
print(f"📋 Fogli disponibili:")
for ws in sheet.worksheets():
    print(f"  - {ws.title}")

print("\n✅ Test superato!")
```

Run:
```bash
cd tanaleague2
python test_connection.py
```

---

### Verifica Versioni Dipendenze

```bash
pip list | grep -E "(gspread|google-auth|flask|pandas|pdfplumber)"
```

**Versioni consigliate**:
- `gspread >= 5.10.0`
- `google-auth >= 2.22.0`
- `flask >= 2.3.0`
- `pandas >= 2.0.0`
- `pdfplumber >= 0.10.0`

Se versioni troppo vecchie, aggiorna:
```bash
pip install --upgrade gspread google-auth flask pandas pdfplumber
```

---

### Logs Strutturati

Per debug avanzato, usa logging invece di print:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Uso
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

Output:
```
2024-11-17 10:30:45 - app - INFO - Loading player 0000012345
2024-11-17 10:30:46 - app - DEBUG - Data loaded: {...}
```

---

## 📞 Supporto

### Se il problema persiste

1. **Cerca in questa guida** per errore specifico
2. **Controlla [SETUP.md](SETUP.md)** per configurazione corretta
3. **Testa in locale** prima di deploy
4. **Check logs**:
   - Locale: terminale output
   - PythonAnywhere: Error log
5. **Verifica Google Sheet**: Dati corretti, fogli esistenti
6. **Apri issue su GitHub** con:
   - Descrizione problema
   - Comando eseguito
   - Output completo (error traceback)
   - Sistema operativo e Python version

---

## 🔍 Quick Reference Errori Comuni

| Errore | Causa | Soluzione Rapida |
|--------|-------|------------------|
| `PERMISSION_DENIED` | Service account non ha accesso | Share Google Sheet con service account email |
| `SpreadsheetNotFound` | SHEET_ID errato | Verifica SHEET_ID in config.py |
| `WorksheetNotFound` | Foglio mancante | Crea foglio o run setup_achievements.py |
| `RESOURCE_EXHAUSTED` | Troppi API calls | Aspetta 2 minuti, evita loop |
| `Date format not recognized` | Nome file CSV errato | Rinomina in YYYY_MM_DD_SeasonID.csv |
| `No tables found in PDF` | PDF senza tabelle | Ri-esporta con tabelle strutturate |
| `500 Internal Server Error` | Errore Python backend | Check error log, correggi codice |
| `TemplateNotFound` | Template HTML mancante | Verifica cartella templates/ |
| `No module named X` | Dipendenze non installate | pip install -r requirements.txt |
| `service_account_credentials.json not found` | File credenziali mancante | Upload in tanaleague2/ |

---

**Buon troubleshooting! 🛠️**

Se trovi soluzione a problema non documentato qui, considera aprire PR per aggiornare questa guida! 🙏
