# 🧪 GUIDA TEST ONE PIECE IMPORT (con W/T/L)

## 📋 Setup Completato

✅ Google Sheet di TEST creato (stesso di Pokemon)
✅ Service account autorizzato
✅ Script di test pronto (`import_tournament_TEST.py`)

**IMPORTANTE:** Questo script scrive SOLO sul foglio di test, NON su quello di produzione!

---

## 🎯 STEP 1: Prepara Fogli TEST

**A) Foglio Config** - Aggiungi stagione One Piece:
```
Season_ID: OP-TEST01
TCG: OP
Season_Name: One Piece Test Season
Entry_Fee: 5
Pack_Cost: 4
```

**B) Foglio Players** - Aggiungi colonna TCG (colonna C, dopo Name):
```
Membership | Name | TCG | First_Seen | Last_Seen | Tournaments | Wins | Match_W | Match_T | Match_L | Points
```
⚠️ **IMPORTANTE:** La colonna TCG serve per distinguere stats One Piece vs Pokemon!

---

## 🎯 STEP 2: Prepara CSV di Test

**Metti un CSV One Piece nella cartella `tanaleague2/`** (NON in sottocartelle!)

**Il CSV One Piece deve contenere:**
- Ranking, Membership Number, User Name, Win Points, OMW%, Record
- **NON** contiene W/T/L espliciti - lo script li CALCOLA automaticamente!

**Esempio:** Se il tuo CSV si chiama `OP11_2025_07_03.csv`, copialo in:
```
/home/user/TanaLeague/tanaleague2/OP11_2025_07_03.csv
```

---

## 🎯 STEP 3: TEST IMPORT (verifica calcolo W/T/L)

**Esegui l'import di test:**

```bash
cd tanaleague2
python import_tournament_TEST.py --csv NOME_TUO_FILE.csv --season OP-TEST01
```

**Esempio:**
```bash
python import_tournament_TEST.py --csv OP11_2025_07_03.csv --season OP-TEST01
```

**Cosa succede:**
- ✅ Legge il CSV
- ✅ Calcola W/T/L da Win Points:
  - Match_W = Win_Points / 3
  - Match_T = 0 (One Piece NON ha pareggi)
  - Match_L = n_rounds - Match_W
- ✅ Scrive dati sul Google Sheet di TEST
- ✅ Crea torneo in "Tournaments"
- ✅ Aggiunge risultati in "Results" (con W/T/L)
- ✅ Traccia vouchers in "Vouchers"
- ✅ Aggiunge/aggiorna giocatori in "Players" (con W/T/L aggregati)

**Output atteso:**
```
📂 Lettura CSV...
   👥 Partecipanti: X
   📅 Data: 2025-07-03
   🎮 Round: Y
   🏆 Vincitore: [Nome]

📝 Scrittura dati...
   📊 Foglio Tournaments...
   📊 Foglio Results...
   📊 Foglio Vouchers...
   📊 Foglio Players...

✅ IMPORT COMPLETATO!
```

---

## 🎯 STEP 4: Verifica i Dati

Apri il Google Sheet di TEST e controlla:

### **Foglio "Results"**
- [ ] Ci sono 3 colonne NUOVE alla fine (dopo Player_Name):
  - **Colonna 10: Match_W** - Vittorie (es: 4, 3, 2...)
  - **Colonna 11: Match_T** - Pareggi (sempre 0 per One Piece)
  - **Colonna 12: Match_L** - Sconfitte (es: 0, 1, 2...)

**Esempio di riga corretta:**
```
Rank=1, Win_Points=12 → Match_W=4, Match_T=0, Match_L=0 (4-0)
Rank=2, Win_Points=9  → Match_W=3, Match_T=0, Match_L=1 (3-1)
Rank=3, Win_Points=6  → Match_W=2, Match_T=0, Match_L=2 (2-2)
```

### **Foglio "Players"**
- [ ] Colonne Match_W, Match_T, Match_L aggiornate
- [ ] Match_T sempre 0 per One Piece
- [ ] Totali corretti (somma di tutti i tornei)

### **Foglio "Tournaments"**
- [ ] C'è una riga con Tournament_ID: `OP-TEST01_2025-07-03`
- [ ] Winner corretto

---

## ✅ VERIFICA CALCOLI

**Per verificare che W/T/L siano calcolati correttamente:**

1. Prendi un giocatore dal foglio Results
2. Guarda il suo Win_Points (es: 9)
3. Calcola mentalmente:
   - Match_W = 9 / 3 = **3**
   - Match_T = **0** (One Piece non ha pareggi)
   - Se torneo ha 4 round: Match_L = 4 - 3 = **1**
   - Risultato: 3-0-1 (3W, 0T, 1L)
4. Verifica che le colonne 10, 11, 12 abbiano questi valori

---

## ✅ CONFRONTO con POKEMON

**Differenza chiave:**

| TCG | Win Points | Match_T | Match_L |
|-----|------------|---------|---------|
| **One Piece** | W=3, L=0 | Sempre 0 | Calcolato (rounds - W) |
| **Pokemon** | W=3, T=1, L=0 | Può essere > 0 | Letto da TDF |

**Similarità:**
- Entrambi scrivono 13 colonne in Results (stessa struttura)
- Entrambi aggregano W/T/L in Players
- Retrocompatibilità: leggono W/T/L se esistono, altrimenti calcolano

---

## 🗑️ Come Cancellare un Test Sbagliato

**Per ricominciare da zero:**

1. Apri Google Sheet di TEST
2. **Foglio "Tournaments":** Trova riga con `OP-TEST01_2025-07-03` → Elimina riga
3. **Foglio "Results":** Filtra Tournament_ID = `OP-TEST01_2025-07-03` → Elimina righe
4. **Foglio "Vouchers":** Filtra Tournament_ID = `OP-TEST01_2025-07-03` → Elimina righe
5. **Foglio "Players":** (opzionale) Ricalcola stats o lascia così

Fatto! Puoi reimportare.

---

## ⚠️ NOTA: Retrocompatibilità

**Lo script è retrocompatibile!**

Se nel foglio Results ci sono già righe SENZA le colonne W/T/L (vecchi import), lo script:
- ✅ Le legge correttamente
- ✅ Calcola W/T/L da Win_Points (fallback)
- ✅ Non va in errore

Questo significa che puoi:
1. Importare un torneo con lo script VECCHIO (senza W/T/L)
2. Importare un torneo con lo script NUOVO (con W/T/L)
3. Aggregazione Players funziona con ENTRAMBI

---

## 🚀 Prossimi Passi

**Quando il test è OK:**
1. Verifica che W/T/L siano calcolati correttamente
2. Verifica che Players sia aggiornato correttamente
3. Applica le stesse modifiche a `import_tournament.py` (produzione)
4. Aggiungi colonne W/T/L al foglio di PRODUZIONE
5. Importa tornei reali

---

## 🆘 Problemi Comuni

**Errore: "Worksheet not found"**
- Controlla che i fogli abbiano ESATTAMENTE questi nomi:
  - Config
  - Tournaments
  - Results
  - Vouchers
  - Players

**Match_W/T/L sembrano sbagliati:**
- Verifica la formula: Match_W = Win_Points / 3
- Verifica che n_rounds sia corretto (dipende da n_participants)
- Esempio: 4 partecipanti = 3 rounds

**Players non aggiornati:**
- Controlla che existing_players non abbia righe vuote prima dei dati
- Verifica che Membership Number nel CSV corrisponda a quello in Players

---

**Buon test! 🧪**
