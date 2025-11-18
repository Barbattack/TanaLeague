# 📥 Guida Import Tornei

Guida completa per importare tornei da CSV, PDF e TDF nei 3 TCG supportati.

---

## 📋 Indice

- [One Piece (CSV)](#-one-piece-tcg-csv)
- [Pokémon (TDF/XML)](#-pokémon-tcg-tdfxml)
- [Riftbound (PDF)](#-riftbound-tcg-pdf)
- [Test Mode](#-test-mode-dry-run)
- [Troubleshooting](#-troubleshooting)

---

## 🏴‍☠️ One Piece TCG (CSV)

### Formato File

**Sorgente**: Export CSV dal portale Bandai ufficiale per il gioco organizzato One Piece TCG

**Formato**: CSV con le seguenti colonne (ordine importante):
```
Ranking, User Name, Membership Number, Win Points, OMW %, Record, Points_Victory, Points_Ranking, Points_Total
```

**Esempio CSV:**
```csv
Ranking,User Name,Membership Number,Win Points,OMW %,Record
1,Cogliati Pietro,12345,12,65.5,4-0
2,Rossi Mario,67890,9,62.3,3-1
...
```

### Nome File

Il nome del file **deve** contenere la data in uno dei seguenti formati:

- `YYYY_MM_DD_OP12.csv` → es. `2025_06_12_OP12.csv`
- `DD_MM_YYYY_OP12.csv` → es. `12_06_2025_OP12.csv`
- `YYYY-MM-DD_OP12.csv` → es. `2025-06-12_OP12.csv`
- `DD_Month_YYYY_OP12.csv` → es. `12_June_2025_OP12.csv`

**La data viene estratta automaticamente dal nome file!**

### Import Command

```bash
cd tanaleague2
python import_tournament.py --csv path/to/file.csv --season OP12
```

### Parametri

- `--csv`: Path al file CSV (obbligatorio)
- `--season`: ID stagione (es. OP12, OP13) (obbligatorio)
- `--test`: Test mode - verifica senza scrivere (opzionale)

### Cosa Fa

1. ✅ Valida formato CSV e data nel filename
2. ✅ Calcola punti TanaLeague (vittoria + ranking)
3. ✅ Identifica X-0, X-1, Altri per buoni negozio
4. ✅ Calcola distribuzione buoni
5. ✅ Scrive in: Tournaments, Results, Vouchers, Players
6. ✅ Aggiorna Seasonal_Standings_PROV
7. ✅ Check e sblocca achievement automaticamente
8. ✅ Crea backup in Backup_Log

### Output Esempio

```
🚀 IMPORT TORNEO: 2025_06_12_OP12.csv
📊 Stagione: OP12

📂 Lettura CSV...
   👥 Partecipanti: 16
   📅 Data: 2025-06-12
   🎮 Round: 4
   🏆 Vincitore: Cogliati Pietro

⚙️  Recupero configurazione OP12...
   💶 Entry fee: 5€
   📦 Pack cost: 4€

🧮 Calcolo punti...
🎯 Identificazione X-0/X-1...
💰 Calcolo buoni negozio...
   💵 Fondo totale: 80€
   📦 Costo buste: 64€
   💸 Distribuito: 80€
   💰 Rimane: 0€

💾 Creazione backup...
📝 Scrittura dati...
   📊 Foglio Tournaments...
   📊 Foglio Results...
   📊 Foglio Vouchers...
   📊 Foglio Players...
   📊 Foglio Seasonal_Standings...
   🎮 Check achievement...
   🏆 0000012345: 🎬 First Blood
   ✅ 1 achievement sbloccato!

✅ IMPORT COMPLETATO!
```

---

## ⚡ Pokémon TCG (TDF/XML)

### Formato File

**Sorgente**: Export da Play! Pokémon Tournament software

**Formato**: TDF (XML interno)

**Contenuto**: File XML che contiene:
- Informazioni torneo (nome, data, formato)
- Lista giocatori (player ID, nome)
- Standings finali (rank, record, tiebreakers)
- Match results H2H (opzionale)

### Import Command

```bash
cd tanaleague2
python parse_pokemon_tdf.py --tdf path/to/tournament.tdf --season PKM-FS25
```

### Parametri

- `--tdf`: Path al file TDF (obbligatorio)
- `--season`: ID stagione (es. PKM-FS25, PKM-WIN25) (obbligatorio)
- `--test`: Test mode (opzionale)

### Cosa Fa

1. ✅ Parsa XML del file TDF
2. ✅ Estrae standings con rank, W-L-D, tiebreakers
3. ✅ Calcola punti TanaLeague
4. ✅ Estrae match H2H (se disponibili)
5. ✅ Scrive in: Tournaments, Results, Pokemon_Matches, Players
6. ✅ Aggiorna Seasonal_Standings_PROV
7. ✅ Check e sblocca achievement automaticamente

### Output Esempio

```
🚀 IMPORT POKEMON TOURNAMENT

📂 Parsing TDF file: tournament.tdf
   🏆 Torneo: Pokemon League Cup
   📅 Data: 2025-06-15
   👥 Partecipanti: 24

🧮 Calcolo punti TanaLeague...
📊 Importazione Pokemon TDF...

✅ Tournament: PKM-FS25_2025-06-15
✅ Results: 24 giocatori
✅ Matches: 96 match
✅ Players: 8 nuovi, 16 aggiornati
✅ Seasonal Standings aggiornate per PKM-FS25

🎮 Check achievement...
🏆 0000067890: 🎬 Debutto
🏆 0000012345: 📅 Regular
✅ 2 achievement sbloccati!

🎉 IMPORT COMPLETATO!
```

### Note Pokémon

- **Display Nomi**: I nomi vengono mostrati come "Nome I." (es. "Pietro C.")
- **Match H2H**: Se disponibili, vengono salvati in `Pokemon_Matches` sheet
- **Sistema Punti**: W=3, D=1, L=0 (supporta pareggi)

---

## 🌌 Riftbound TCG (CSV Multi-Round)

### Formato File

**Sorgente**: Export CSV dal software di gestione tornei (uno per ogni round)

**Formato**: CSV con colonne strutturate (uno per round)

**Colonne Chiave:**
```csv
Table Number, ..., Player 1 User ID, Player 1 First Name, Player 1 Last Name, ...,
Player 2 User ID, Player 2 First Name, Player 2 Last Name, ...,
Player 1 Event Record, Player 2 Event Record, ...
```

**Esempio Riga CSV:**
```csv
1,false,false,false,56480,semm,riva,semriva202.08@gmail.com,97041,Giuseppe,Piazza,o0giuse0o91@gmail.com,COMPLETE,Giuseppe Piazza: 2-0-0,0-2-0,2-0-0,0-2-2,1-1-2,...
```

**Note Importanti:**
- **User ID** (Col 5 e 9) diventa il Membership Number
- **Event Record** (Col 17 e 18) contiene W-L-D totale torneo
- **Multi-round**: Importa tutti i CSV insieme per stats complete!

### Nome File

Formato consigliato: `RFB_YYYY_MM_DD_RX.csv`

Esempio:
- `RFB_2025_11_17_R1.csv` → Round 1
- `RFB_2025_11_17_R2.csv` → Round 2
- `RFB_2025_11_17_R3.csv` → Round 3

### Import Command

**Import Singolo Round** (ok ma meno dati):
```bash
cd tanaleague2
python import_riftbound.py --csv RFB_2025_11_17_R1.csv --season RFB01
```

**Import Multi-Round** (RACCOMANDATO):
```bash
cd tanaleague2
python import_riftbound.py --csv RFB_2025_11_17_R1.csv,RFB_2025_11_17_R2.csv,RFB_2025_11_17_R3.csv --season RFB01
```

### Parametri

- `--csv`: Path al file CSV (o più file separati da virgola) (obbligatorio)
- `--season`: ID stagione (es. RFB01, RFB-WIN25) (obbligatorio)
- `--test`: Test mode (opzionale)

### Cosa Fa

1. ✅ Parsa tutti i CSV round
2. ✅ Aggrega risultati per User ID
3. ✅ Estrae Event Record finale (W-L-D)
4. ✅ Calcola ranking basato su punti Swiss (W*3 + D*1)
5. ✅ **Traccia match wins dettagliati** (come Pokémon!)
6. ✅ Scrive in: Tournaments, Results, Players
7. ✅ Aggiorna Seasonal_Standings_PROV
8. ✅ Check e sblocca achievement automaticamente

### Output Esempio

```
🚀 IMPORT TORNEO RIFTBOUND
📊 Stagione: RFB01
📅 Data: 2025-11-17
📂 File CSV: 3

📂 Parsing 3 CSV file(s)...
   📄 Round 1: RFB_2025_11_17_R1.csv
      ✅ 8 matches
   📄 Round 2: RFB_2025_11_17_R2.csv
      ✅ 8 matches
   📄 Round 3: RFB_2025_11_17_R3.csv
      ✅ 8 matches

   📊 16 giocatori totali trovati!

✅ Parsing completato!
   🏆 Winner: Riccardo Farumi
   👥 Partecipanti: 16
   🔄 Round: 3

📊 Importazione Riftbound CSV...
✅ Tournament: RFB01_2025-11-17
✅ Results: 16 giocatori
✅ Players: 4 nuovi, 12 aggiornati

   🔄 Aggiornamento classifica stagionale RFB01...
      Tornei stagione: 5
      Scarto: NESSUNO (stagione < 8 tornei)
      ✅ Classifica aggiornata: 28 giocatori

🎮 Check achievement...
✅ 8 achievement sbloccati!

🎉 IMPORT COMPLETATO!
```

### Note Riftbound

- **User ID**: Usato come Membership Number (es. 56480, 97041)
- **Stats Avanzate**: Con CSV multi-round hai W-L-D dettagliati come Pokémon!
- **Sistema Punti**: W=3, D=1, L=0 (supporta pareggi)
- **Achievement**: Sistema completo attivo con dati dettagliati
- **Display Nomi**: Mostra First Name + Last Name del giocatore

---

## 🧪 Test Mode (Dry Run)

**Tutti e 3 gli script** supportano la modalità test per verificare il file senza scrivere su Google Sheets.

### One Piece

```bash
python import_tournament.py --csv file.csv --season OP12 --test
```

### Pokémon

```bash
python parse_pokemon_tdf.py --tdf file.tdf --season PKM-FS25 --test
```

### Riftbound

```bash
python import_riftbound.py --csv file.csv --season RFB01 --test
# Multi-round
python import_riftbound.py --csv R1.csv,R2.csv,R3.csv --season RFB01 --test
```

### Cosa Fa Test Mode

- ✅ Legge e parsa il file
- ✅ Valida formato e dati
- ✅ Calcola punti e standings
- ✅ Mostra output completo
- ❌ **NON scrive** su Google Sheets
- ❌ **NON crea** backup
- ❌ **NON sblocca** achievement

**Usa test mode per:**
- Verificare formato file prima di importare
- Debuggare problemi di parsing
- Vedere anteprima risultati

---

## 🔧 Troubleshooting

### Errore: "Nessun giocatore trovato nei CSV" (Riftbound)

**Causa**: CSV non ha formato atteso o colonne mancanti

**Soluzione**:
1. Verifica che il CSV abbia tutte le colonne richieste (almeno 18)
2. Controlla che User ID (Col 5 e 9) siano presenti
3. Verifica che Event Record (Col 17 e 18) esistano
4. Prova a esportare nuovamente il CSV dal software

### Errore: "ValueError: Date format not recognized"

**Causa**: Nome file CSV non contiene data in formato riconosciuto

**Soluzione**:
Rinomina il file in uno di questi formati:
- `2025_06_12_OP12.csv`
- `12_06_2025_OP12.csv`
- `2025-06-12_OP12.csv`

### Errore: "Torneo già importato"

**Causa**: Tournament ID già esiste nel foglio Tournaments

**Opzioni**:
1. Rispondi `y` per sovrascrivere (sostituisce dati)
2. Rispondi `n` per annullare
3. Cambia data nel filename se è un torneo diverso

### Errore: "gspread.exceptions.APIError: RESOURCE_EXHAUSTED"

**Causa**: Troppi request a Google Sheets API

**Soluzione**:
- Aspetta 1-2 minuti
- Riprova import
- Evita import multipli simultanei

### Warning: "Achievement check failed"

**Causa**: Sheet Achievement_Definitions o Player_Achievements non esistono

**Soluzione**:
```bash
cd tanaleague2
python setup_achievements.py
```

Questo crea i fogli necessari.

### Nickname con spazi non rilevati (Riftbound)

**Causa**: Multilinea nel PDF - il parser attuale gestisce questo caso!

**Verifica**:
- Il nickname deve essere tra parentesi: `(Hotel Motel)`
- Lo script sostituisce `\n` con spazi automaticamente

---

## 📊 Confronto Import

| Feature | One Piece (CSV) | Pokémon (TDF) | Riftbound (PDF) |
|---------|----------------|---------------|-----------------|
| **Formato** | CSV | XML/TDF | PDF |
| **Sorgente** | Limitlesstcg | Play! Pokémon | Software gestione |
| **Match H2H** | ❌ No | ✅ Sì | ❌ No |
| **Pareggi** | ❌ No (W/L) | ✅ Sì (W/D/L) | ✅ Sì (W/D/L) |
| **Buoni Negozio** | ✅ Sì | ❌ No | ❌ No |
| **Display Nome** | Full Name | Nome I. | Nickname |
| **Test Mode** | ✅ Sì | ✅ Sì | ✅ Sì |
| **Achievement** | ✅ Auto | ✅ Auto | ✅ Auto |
| **Standings** | ✅ Auto | ✅ Auto | ✅ Auto |

---

## 🎯 Best Practices

1. **Usa sempre Test Mode prima** dell'import reale
2. **Verifica formato file** prima di importare
3. **Backup Google Sheet** prima di import grandi
4. **Un import alla volta** (evita race conditions)
5. **Controlla output** per eventuali warning
6. **Verifica standings** sulla webapp dopo import

---

## 📞 Supporto

**Problemi non risolti?**

1. Controlla [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Verifica log output dettagliato
3. Apri issue su GitHub con:
   - Comando eseguito
   - Output completo
   - File di esempio (se possibile)

---

**Happy Importing! 🎮**
