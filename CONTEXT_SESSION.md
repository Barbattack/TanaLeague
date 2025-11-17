# 🎯 CONTEXT SESSION - TanaLeague Riftbound Implementation

**Data:** 17 Novembre 2025
**Sessione:** Implementazione import Riftbound da PDF
**Branch:** `claude/review-session-description-0176B9YCmJsgwPAUHxMH7UuG`

---

## 📋 COSA STIAMO FACENDO

Stiamo implementando l'**import automatico dei tornei Riftbound** da file PDF nel sistema TanaLeague.

### Il Sistema TanaLeague

**TanaLeague** è una webapp Flask per gestire classifiche e statistiche di leghe competitive TCG (Trading Card Games).

**TCG supportati:**
- ✅ **One Piece TCG** - Import da CSV
- ✅ **Pokémon TCG** - Import da TDF/XML (con gestione pareggi e BYE)
- 🔧 **Riftbound** - Import da PDF (IN SVILUPPO)

**Stack tecnologico:**
- Backend: Python 3.10+, Flask 3.0.0
- Database: Google Sheets (via gspread 5.12.0)
- Auth: Google Service Account
- Cache: JSON file-based
- Frontend: HTML5, CSS3, Jinja2, Chart.js
- Hosting: PythonAnywhere (free tier)

**Repository:** https://github.com/Barbattack/TanaLeague

---

## 🎮 RIFTBOUND - SPECIFICHE

### Formato PDF
Il torneo Riftbound viene esportato in PDF con questo formato:

```
Standings - Release Event - Lunedì 10 Novembre
Round 4                    Page 1/1                    Rank 1 - 16

Rank  Player                    Points  W-L-D   OMW    GW     OGW
1
Cogliati, Pietro
(2metalupo)
12 4-0-0 62.5% 100% 62.5%

2
Viganò, Federico
(Squicco)
9 3-1-0 64.5% 75% 64.5%

...
```

**Caratteristiche formato:**
- **Rank** su una riga separata
- **Nome completo** (Cognome, Nome) su riga successiva
- **(Nickname)** tra parentesi su riga successiva - QUESTO È IL MEMBERSHIP NUMBER
- **Stats** su riga successiva: Points W-L-D OMW% GW% OGW%

### Sistema Punti Riftbound

**Come Pokémon - Con pareggi:**
- Vittoria (W) = 3 punti match
- Pareggio (D) = 1 punto match
- Sconfitta (L) = 0 punti match

**Formula TanaLeague per punti classifica:**
```python
points_victory = (w * 3 + d * 1) / 3
points_ranking = n_participants - (rank - 1)
points_total = points_victory + points_ranking
```

**Tracking nel Google Sheet:**
- TCG = "RFB"
- Colonne 10-12 in Results: W, T (Ties/Draws), L
- Sistema identico a Pokémon

---

## 🐛 PROBLEMA ATTUALE

### Situazione
Lo script `import_riftbound.py` è stato creato ma **non riesce a estrarre i dati dal PDF correttamente**.

### Errori riscontrati

**Primo tentativo (parser riga per riga):**
```bash
🔍 DEBUG: Trovati 0 ranks, 12 nicknames
ValueError: ❌ Nessun giocatore trovato nel PDF!
```

**Problema:** `extract_text()` recupera solo **1034 caratteri** invece del contenuto completo. Non trova nessun rank (righe con solo numero).

**Causa:** Font/layout del PDF non compatibili con estrazione testo base di pdfplumber.

### Soluzioni tentate

1. **Parser multilinea regex** - ❌ Fallito
2. **Parser riga per riga** - ❌ Fallito (0 ranks trovati)
3. **Parser con extract_words() + coordinate** - 🔧 IN TEST

---

## 💡 STRATEGIA ATTUALE (Commit 3ff678a)

### Approccio ibrido - Due strategie

**STRATEGIA 1: Estrazione tabelle**
```python
tables = page.extract_tables()
```
Prova a estrarre tabelle strutturate (più affidabile ma non sempre funziona).

**STRATEGIA 2: Analisi coordinate (MAIN)**
```python
words = page.extract_words()  # Ogni parola con coordinate X,Y
```

**Come funziona:**
1. Estrae ogni parola con coordinate fisiche (x0, y, x1, top, bottom, text)
2. Raggruppa parole per coordinata Y (stessa riga orizzontale)
3. Ordina righe dall'alto in basso (top → bottom)
4. Ordina parole in ogni riga da sinistra a destra (left → right)
5. **State machine** sequenziale:
   - Cerca rank (numero 1-99 all'inizio riga)
   - Cerca nome (testo sulla stessa riga o successiva)
   - Cerca nickname tra parentesi `(nickname)`
   - Cerca stats: `Points W-L-D OMW% GW% OGW%`
   - Quando trova tutto → salva player e resetta stato

**Vantaggi:**
- ✅ Non dipende da `extract_text()` che fallisce
- ✅ Usa posizioni fisiche delle parole
- ✅ Robusto contro layout variabili
- ✅ Funziona anche con font problematici

---

## 📂 FILE PRINCIPALI

### `/tanaleague2/import_riftbound.py`
Script di import Riftbound. Funzioni principali:

```python
def parse_pdf(pdf_path, season_id, tournament_date) -> Dict
    # Estrae dati dal PDF usando strategia ibrida
    # Returns: {tournament: [...], results: [...], players: {...}}

def import_to_sheet(data, test_mode=False)
    # Scrive dati nel Google Sheet
    # test_mode=True → mostra output senza scrivere

def get_season_config(sheet, season_id) -> Dict
    # Recupera config stagione da foglio Config

def update_players_stats(...)
    # Aggiorna foglio Players con lifetime stats
```

**Dipendenze:**
```
pdfplumber  # Parsing PDF
gspread     # Google Sheets API
google-auth # Autenticazione
```

**Utilizzo:**
```bash
# Test mode (senza scrivere)
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01 --test

# Import reale
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01
```

### `/tanaleague2/RFB_2025_11_10.pdf`
PDF di test con 16 giocatori del torneo Release Event del 10 Novembre 2025.

---

## 🗄️ STRUTTURA GOOGLE SHEET

Il Google Sheet ha questi fogli (worksheets):

### **Config**
Configurazione stagioni:
```
Season_ID | TCG | Season_Name              | Entry_Fee | Pack_Cost | Status
RFB01     | RFB | Riftbound Season 1       | 5         | 6         | ACTIVE
OP12      | OP  | One Piece Serie 12       | 5         | 6         | ACTIVE
PKM-FS25  | PKM | Pokemon Fiamme Spettrali | 5         | 6         | ACTIVE
```

### **Players**
Anagrafica giocatori:
```
Membership | Name           | TCG | First_Seen | Last_Seen  | Total_Tournaments | Tournament_Wins | Match_W | Match_T | Match_L | Total_Points
2metalupo  | Cogliati, Pietro| RFB | 2025-11-10 | 2025-11-10 | 1                 | 1               | 4       | 0       | 0       | 20.0
```

### **Results**
Risultati tornei (COLONNE 10-12 PER W/T/L!):
```
Result_ID          | Tournament_ID  | Membership | Rank | Win_Points | OMW  | Pts_Victory | Pts_Ranking | Pts_Total | Name             | W | T | L
RFB01_2025-11-10_2metalupo | RFB01_2025-11-10 | 2metalupo | 1 | 12 | 62.5 | 4.0 | 16 | 20.0 | Cogliati, Pietro | 4 | 0 | 0
```

### **Tournaments**
Metadata tornei:
```
Tournament_ID     | Season_ID | Date       | Participants | Rounds | Source_File          | Import_Date         | Winner
RFB01_2025-11-10 | RFB01     | 2025-11-10 | 16          | 4      | RFB_2025_11_10.pdf  | 2025-11-17 14:30:00 | Cogliati, Pietro
```

---

## 🔧 SETUP NECESSARIO

### 1. Configura stagione RFB nel foglio Config
Nel Google Sheet, aggiungi riga in **Config**:

| Season_ID | TCG | Season_Name | Entry_Fee | Pack_Cost | X0_Ratio | X1_Ratio | Rounding | Status | Next_Tournament |
|-----------|-----|-------------|-----------|-----------|----------|----------|----------|--------|-----------------|
| RFB01 | RFB | Riftbound Season 1 | 5 | 6 | 0.4 | 0.3 | 0.5 | ACTIVE | 2025-11-20 |

### 2. Installa dipendenze
```bash
pip install pdfplumber gspread google-auth
```

### 3. File credenziali
Assicurati che esista:
```
/home/latanadellepulci/tanaleague2/service_account_credentials.json
```

---

## 🧪 TESTING

### Comandi test
```bash
# Vai nella cartella
cd ~/tanaleague2

# Test mode
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01 --test
```

### Output atteso (quando funziona)
```
🔍 Parsing PDF: RFB_2025_11_10.pdf
📅 Season: RFB01
📆 Date: 2025-11-10

📄 Apertura PDF: RFB_2025_11_10.pdf
🔍 Strategia 1: Estrazione tabelle...
  📊 Pagina 1: X tabelle trovate

🔍 Strategia 2: Estrazione layout...
  📝 Trovate XXX parole
  📏 Raggruppate in XX righe
  ✓ Rank 1: Cogliati, Pietro (2metalupo) - 4-0-0
  ✓ Rank 2: Viganò, Federico (Squicco) - 3-1-0
  ...
  ✓ Rank 16: Ghezzi, Davide (ArtiKron) - 0-4-0

✅ Parsing completato: 16 giocatori trovati!

📊 Importazione Riftbound PDF...
⚠️  TEST MODE - Nessuna scrittura effettiva

✅ Tournament: RFB01_2025-11-10
✅ Results: 16 giocatori
✅ Players: 16 totali (stats non calcolate in test mode)

⚠️  TEST COMPLETATO - Nessun dato scritto
```

---

## 🚨 PROBLEMI COMUNI

### "Could get FontBBox from font descriptor"
**Cosa significa:** Warning di pdfplumber, font PDF problematici
**È un problema?** NO - è solo un warning, non blocca l'esecuzione

### "Trovati 0 ranks, 12 nicknames"
**Cosa significa:** `extract_text()` non funziona bene con questo PDF
**Soluzione:** Usa strategia 2 con `extract_words()`

### "ValueError: Nessun giocatore trovato"
**Causa:** Parser non riesce a matchare il formato PDF
**Debug:** Guarda output "Strategia 2" - quante parole/righe trova?

---

## 📝 PROSSIMI PASSI

1. ✅ **COMPLETARE TEST** - Verificare che strategia 2 trovi tutti i 16 giocatori
2. Se test OK → **Import reale** nel Google Sheet
3. Verificare dati corretti nel Sheet
4. **Documentare** procedura import RFB nel README
5. Aggiungere RFB alla landing page della webapp
6. Testare statistiche RFB

---

## 💰 IMPORTANTE - CREDITO RESIDUO

**Credito:** $212 (scadenza domani)
**Priorità:** Completare Riftbound import prima della scadenza

---

## 🔗 COLLEGAMENTI UTILI

- **Repository:** https://github.com/Barbattack/TanaLeague
- **Branch corrente:** `claude/review-session-description-0176B9YCmJsgwPAUHxMH7UuG`
- **Google Sheet ID:** `19ZF35DTmgZG8v1GfzKE5JmMUTXLo300vuw_AdrgQPFE`
- **Live webapp:** https://latanadellepulci.pythonanywhere.com

---

## 📞 SE CLAUDE SI DISCONNETTE

**Dare a "Claude normale" questi file:**
1. Questo file: `CONTEXT_SESSION.md`
2. File codice: `tanaleague2/import_riftbound.py`
3. PDF test: `tanaleague2/RFB_2025_11_10.pdf`
4. Output ultimo test che hai fatto

**Dire a Claude:**
> "Sto implementando l'import Riftbound per TanaLeague. Ho il context completo in CONTEXT_SESSION.md. Il parser PDF non funziona ancora - usa extract_text() che recupera solo 1034 caratteri e trova 0 ranks. Ho provato extract_words() ma ti serve l'output dell'ultimo test per debuggare. Ecco l'output: [incolla output]"

---

**🎯 OBIETTIVO FINALE:**
Import automatico tornei Riftbound da PDF → Google Sheet → Webapp TanaLeague

**✅ QUANDO FUNZIONA:**
Test mode mostra "16 giocatori trovati" e tutti i rank da 1 a 16 correttamente estratti.
