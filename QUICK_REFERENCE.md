# ⚡ QUICK REFERENCE - Riftbound Import

**Comandi e codice pronti all'uso per debugging rapido**

---

## 🏃 COMANDI RAPIDI

### Test import
```bash
cd ~/tanaleague2
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01 --test
```

### Import reale
```bash
python import_riftbound.py --pdf RFB_2025_11_10.pdf --season RFB01
```

### Debug PDF con Python
```bash
python3 << 'EOF'
import pdfplumber

pdf_path = 'RFB_2025_11_10.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]

    # Test extract_text
    text = page.extract_text()
    print(f"extract_text(): {len(text)} caratteri")
    print("Prime 500:")
    print(text[:500])
    print("\n" + "="*60 + "\n")

    # Test extract_words
    words = page.extract_words()
    print(f"extract_words(): {len(words)} parole")
    print("Prime 10:")
    for i, w in enumerate(words[:10]):
        print(f"  {i}: {w['text']} @ ({w['x0']:.1f}, {w['top']:.1f})")
    print("\n" + "="*60 + "\n")

    # Test extract_tables
    tables = page.extract_tables()
    print(f"extract_tables(): {len(tables)} tabelle")
    if tables:
        print(f"Tabella 1: {len(tables[0])} righe")
        for i, row in enumerate(tables[0][:3]):
            print(f"  Riga {i}: {row}")
EOF
```

---

## 📋 COSA DIRE A "CLAUDE NORMALE"

Se devi passare il lavoro a un altro Claude:

```
Ciao! Sto lavorando sull'implementazione dell'import Riftbound per TanaLeague.

CONTESTO COMPLETO:
Ho 3 file di documentazione nella root del repo:
1. CONTEXT_SESSION.md - Context generale sessione
2. RIFTBOUND_TECHNICAL.md - Documentazione tecnica completa
3. QUICK_REFERENCE.md - Quick reference (questo file)

SITUAZIONE ATTUALE:
- Script: tanaleague2/import_riftbound.py
- PDF test: tanaleague2/RFB_2025_11_10.pdf (16 giocatori)
- Branch: claude/review-session-description-0176B9YCmJsgwPAUHxMH7UuG
- Commit: 3ff678a

PROBLEMA:
Il parser PDF non trova tutti i giocatori. Ho testato e questo è l'output:
[INCOLLA L'OUTPUT DEL TEST QUI]

STRATEGIA:
Usa extract_words() con coordinate invece di extract_text().
Il codice attuale implementa questa strategia ma serve debugging.

OBIETTIVO:
Far funzionare l'import così che il test mode mostri "16 giocatori trovati" con tutti i rank da 1 a 16.

Per favore leggi CONTEXT_SESSION.md e RIFTBOUND_TECHNICAL.md per il contesto completo, poi aiutami a debuggare.
```

---

## 🔍 SNIPPET DEBUGGING

### Aggiungi debug al parser

Inserisci dopo la linea 100 di `import_riftbound.py`:

```python
print(f"  📏 Raggruppate in {len(sorted_lines)} righe")

# === DEBUG: Mostra prime 30 righe ===
print("\n🐛 DEBUG - Prime 30 righe ricostruite:")
for i, (y, words) in enumerate(sorted_lines[:30]):
    words.sort(key=lambda w: w['x0'])
    text = ' '.join([w['text'] for w in words])
    print(f"  {i:2d} (y={y:3d}): [{text}]")
print("=" * 60 + "\n")
# === FINE DEBUG ===
```

### Test regex patterns

```python
import re

# Test data
test_lines = [
    "1",
    "Cogliati, Pietro",
    "(2metalupo)",
    "12 4-0-0 62.5% 100% 62.5%",
    "2 Viganò, Federico (Squicco) 9 3-1-0 64.5% 75% 64.5%"
]

# Pattern rank
rank_pattern = r'^(\d{1,2})\b'
for line in test_lines:
    match = re.match(rank_pattern, line)
    if match:
        print(f"RANK: [{line}] → {match.group(1)}")

# Pattern nickname
nick_pattern = r'\(([^)]+)\)'
for line in test_lines:
    match = re.search(nick_pattern, line)
    if match:
        print(f"NICK: [{line}] → {match.group(1)}")

# Pattern stats
stats_pattern = r'(\d+)\s+(\d+)-(\d+)-(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%'
for line in test_lines:
    match = re.search(stats_pattern, line)
    if match:
        print(f"STATS: [{line}]")
        print(f"  Points={match.group(1)}, W={match.group(2)}, L={match.group(3)}, D={match.group(4)}")
        print(f"  OMW={match.group(5)}%, GW={match.group(6)}%, OGW={match.group(7)}%")
```

---

## 📊 DATI DI TEST

### I 16 giocatori del PDF

```
Rank  Nome                        Nickname            W-L-D   Points
1     Cogliati, Pietro            2metalupo           4-0-0   12
2     Viganò, Federico            Squicco             3-1-0   9
3     riva, semm                  JankosOnDrugs       3-1-0   9
4     Scarinzi, Matteo            Hotel Motel         3-1-0   9
5     Mottarella, Sofia           HolidayInn          3-1-0   9
6     Dubini, Luca                DoodleLuke          2-2-0   6
7     R, Steve                    Her Risciux         2-2-0   6
8     Mellace, Samuele            MIBannanoPerNome    2-2-0   6
9     Fachin, Matteo              Seems Chill         2-2-0   6
10    Inverizzi, Diego            diegominchia        2-2-0   6
11    Granaglia, Alessandro       Cuthred             2-2-0   6
12    -, Ika                      His Ika             1-3-0   3
13    Alcantara, Marco            Alkii               1-3-0   3
14    Ravasi, Andrea              MrRavatar           1-3-0   3
15    Piazza, Giuseppe            D4rkd3ath91         1-3-0   3
16    Ghezzi, Davide              ArtiKron            0-4-0   0
```

### Validazione output

Dopo il test, verifica che tutti questi 16 giocatori siano stati trovati con i dati corretti.

---

## 🔧 FIX COMUNI

### Fix 1: Aumenta tolleranza raggruppamento Y

Se alcune righe non vengono raggruppate correttamente:

```python
# Invece di:
y = round(word['top'])

# Usa:
y = round(word['top'] / 2) * 2  # Raggruppa ogni 2 pixel
```

### Fix 2: Gestisci nickname su riga diversa

Se nickname non viene trovato subito dopo nome:

```python
# Cerca nickname nelle prossime 3 righe
if current_rank and not current_nickname:
    for next_y in range(y + 1, y + 15):  # Cerca 15 pixel sotto
        if next_y in lines_dict:
            # Controlla se contiene nickname
            ...
```

### Fix 3: Debug state machine

Traccia gli stati:

```python
print(f"  State: rank={current_rank}, name={current_name}, nick={current_nickname}")
print(f"  Line: [{line_text}]")
```

---

## 📝 CHECKLIST PRE-IMPORT REALE

Prima di fare import reale (senza --test):

- [ ] Test mode funziona e mostra 16 giocatori
- [ ] Tutti i giocatori hanno nome corretto
- [ ] Tutti i W-L-D corretti
- [ ] Foglio Config ha RFB01 configurato
- [ ] Service account credentials presente
- [ ] Backup del Google Sheet fatto (File → Scarica → Excel)

---

## 🎯 OUTPUT PERFETTO

Questo è l'output che DEVI vedere se tutto funziona:

```
🔍 Parsing PDF: RFB_2025_11_10.pdf
📅 Season: RFB01
📆 Date: 2025-11-10

📄 Apertura PDF: RFB_2025_11_10.pdf
🔍 Strategia 1: Estrazione tabelle...
  📊 Pagina 1: 0 tabelle trovate
  📊 Pagina 2: 0 tabelle trovate

🔍 Strategia 2: Estrazione layout...
  📝 Trovate 256 parole
  📏 Raggruppate in 64 righe
  ✓ Rank 1: Cogliati, Pietro (2metalupo) - 4-0-0
  ✓ Rank 2: Viganò, Federico (Squicco) - 3-1-0
  ✓ Rank 3: riva, semm (JankosOnDrugs) - 3-1-0
  ✓ Rank 4: Scarinzi, Matteo (Hotel Motel) - 3-1-0
  ✓ Rank 5: Mottarella, Sofia (HolidayInn) - 3-1-0
  ✓ Rank 6: Dubini, Luca (DoodleLuke) - 2-2-0
  ✓ Rank 7: R, Steve (Her Risciux) - 2-2-0
  ✓ Rank 8: Mellace, Samuele (MIBannanoPerNome) - 2-2-0
  ✓ Rank 9: Fachin, Matteo (Seems Chill) - 2-2-0
  ✓ Rank 10: Inverizzi, Diego (diegominchia) - 2-2-0
  ✓ Rank 11: Granaglia, Alessandro (Cuthred) - 2-2-0
  ✓ Rank 12: -, Ika (His Ika) - 1-3-0
  ✓ Rank 13: Alcantara, Marco (Alkii) - 1-3-0
  ✓ Rank 14: Ravasi, Andrea (MrRavatar) - 1-3-0
  ✓ Rank 15: Piazza, Giuseppe (D4rkd3ath91) - 1-3-0
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

## 🆘 HELP!

### Se sei bloccato

1. **Leggi i file di documentazione:**
   - `CONTEXT_SESSION.md` - Contesto generale
   - `RIFTBOUND_TECHNICAL.md` - Dettagli tecnici
   - `QUICK_REFERENCE.md` - Questo file

2. **Controlla i commit recenti:**
   ```bash
   git log --oneline -5
   ```

3. **Verifica file presenti:**
   ```bash
   ls -lh tanaleague2/import_riftbound.py
   ls -lh tanaleague2/RFB_2025_11_10.pdf
   ```

4. **Testa estrazione base:**
   ```bash
   python3 -c "import pdfplumber; print(pdfplumber.open('tanaleague2/RFB_2025_11_10.pdf').pages[0].extract_words()[:5])"
   ```

5. **Chiedi a Claude** fornendo:
   - I file di documentazione
   - L'output completo del test
   - Cosa hai già provato

---

**Fine Quick Reference**

Ultimo aggiornamento: 17 Novembre 2025
