# 🧪 GUIDA TEST POKEMON IMPORT

## 📋 Setup Completato

✅ Google Sheet di TEST creato
✅ Service account autorizzato
✅ Script di test pronto (`parse_pokemon_tdf_TEST.py`)

**IMPORTANTE:** Questo script scrive SOLO sul foglio di test, NON su quello di produzione!

---

## 🎯 STEP 1: Prepara Fogli TEST

**A) Foglio Config** - Aggiungi stagione Pokemon:
```
Season_ID: PKM-TEST01
TCG: PKM
Season_Name: Pokemon Test Season
Start_Date: 2025-11-01
Status: ACTIVE
```

**B) Foglio Players** - Aggiungi colonna TCG (colonna C, dopo Name):
```
Membership | Name | TCG | First_Seen | Last_Seen | Tournaments | Wins | Match_W | Match_T | Match_L | Points
```
⚠️ **IMPORTANTE:** La colonna TCG serve per distinguere stats Pokemon vs One Piece!

---

## 🎯 STEP 2: Prepara un file TDF

Scegli UNO dei tuoi file TDF Pokemon (anche se disordinato/vecchio, va bene per testare!)

Ad esempio: `novembre_2025_11_12.tdf`

---

## 🎯 STEP 3: Esegui l'Import TEST (dry-run)

**Prima fai un test senza scrivere nulla:**

```bash
cd tanaleague2
python parse_pokemon_tdf_TEST.py --tdf novembre_2025_11_12.tdf --season PKM-TEST01 --test
```

**Cosa succede:**
- ✅ Legge il file TDF
- ✅ Parsa i dati (giocatori, match, risultati)
- ✅ Mostra cosa farebbe
- ❌ NON scrive nulla sul foglio

**Output atteso:**
```
🔍 Trovati X player nella sezione principale
✅ Tournament: PKM-TEST01_2025-11-12
✅ Results: X giocatori
✅ Matches: X match
✅ Players: X totali
⚠️  TEST COMPLETATO - Nessun dato scritto
```

Se vedi errori, fermati e dimmi quale errore!

---

## 🎯 STEP 4: Esegui l'Import REALE (sul foglio test)

**Se il test è ok, fai l'import vero:**

```bash
python parse_pokemon_tdf_TEST.py --tdf novembre_2025_11_12.tdf --season PKM-TEST01
```

(senza --test)

**Cosa succede:**
- ✅ Scrive dati sul Google Sheet di TEST
- ✅ Crea torneo in "Tournaments"
- ✅ Aggiunge risultati in "Results"
- ✅ Traccia match in "Pokemon_Matches"
- ✅ Aggiunge giocatori in "Players"

**Output atteso:**
```
📊 Importazione Pokemon TDF su FOGLIO TEST...
✅ Tournament: PKM-TEST01_2025-11-12
✅ Results: X giocatori
✅ Matches: X match
✅ Players: X nuovi
🎉 IMPORT COMPLETATO su FOGLIO TEST!
API calls: 4
```

---

## 🎯 STEP 5: Verifica i Dati

Apri il Google Sheet di TEST e controlla:

### **Foglio "Tournaments"**
- [ ] C'è una riga con Tournament_ID: `PKM-TEST01_2025-11-12`
- [ ] Participants corretto
- [ ] Winner corretto

### **Foglio "Results"**
- [ ] Ci sono X righe (una per giocatore)
- [ ] Colonna Rank è corretta (1, 2, 3...)
- [ ] Win_Points sono corretti (W*3 + T*1)
- [ ] OMW% ha valori sensati (0-100)
- [ ] Points_Total calcolati

### **Foglio "Pokemon_Matches"**
- [ ] Ci sono i match giocati
- [ ] Round, Winner_ID, Loser_ID compilati

### **Foglio "Players"**
- [ ] Nuovi giocatori aggiunti
- [ ] Name e Membership corretti

---

## ✅ Tutto OK? Cosa fare dopo

**Se i dati sono CORRETTI:**
1. 🎉 La logica Pokemon funziona!
2. Puoi importare altri TDF sul foglio test per verificare
3. Quando sei sicuro, usi lo script normale (`parse_pokemon_tdf.py`) sul foglio vero

**Se i dati sono SBAGLIATI:**
1. Dimmi cosa non va (screenshot o descrizione)
2. Sistemiamo insieme la logica
3. Cancelli le righe sbagliate dal foglio test
4. Riprovi

---

## 🗑️ Come Cancellare un Test Sbagliato

**Per ricominciare da zero:**

1. Apri Google Sheet di TEST
2. **Foglio "Tournaments":** Trova riga con `PKM-TEST01_2025-11-12` → Click destro → Elimina riga
3. **Foglio "Results":** Filtra colonna Tournament_ID = `PKM-TEST01_2025-11-12` → Seleziona tutte → Elimina righe
4. **Foglio "Pokemon_Matches":** Filtra colonna Tournament_ID = `PKM-TEST01_2025-11-12` → Seleziona tutte → Elimina righe
5. **Foglio "Players":** (opzionale) Lascia così o cancella giocatori test

Fatto! Puoi reimportare.

---

## 🚀 Prossimi Passi

Quando tutto funziona:
1. Organizzi i tuoi TDF Pokemon in ordine cronologico
2. Crei stagione vera nel foglio di PRODUZIONE (es: `PKM-FS25`)
3. Usi `parse_pokemon_tdf.py` (quello normale) per importare nel foglio vero
4. Profit! 🎉

---

## 🆘 Problemi Comuni

**Errore: "Sezione <players> non trovata"**
- Il file TDF è corrotto o non standard
- Prova con un altro file

**Errore: "Permission denied"**
- Controlla che il service account abbia accesso al foglio
- Verifica che il file `secrets/service_account.json` esista

**Errore: "Worksheet not found"**
- Controlla che i fogli abbiano ESATTAMENTE questi nomi:
  - Config
  - Tournaments
  - Results
  - Pokemon_Matches
  - Players

**I dati sembrano strani:**
- Fammi vedere screenshot del foglio
- Dimmi cosa ti aspettavi vs cosa vedi

---

**Buon test! 🧪**
