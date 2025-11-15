#!/usr/bin/env python3
"""
PULCI LEAGUE - Tournament Import Script (TEST VERSION)
=======================================================
⚠️  QUESTO SCRIPT USA IL GOOGLE SHEET DI TEST - NON QUELLO DI PRODUZIONE!

Questo script importa i CSV dei tornei nel Google Sheet Pulci League TEST.

COSA FA:
1. Legge il CSV del torneo
2. Calcola i punti (vittoria + ranking)
3. Identifica X-0, X-1, Altri
4. Calcola i buoni negozio
5. Aggiorna tutte le classifiche
6. Crea backup automatico
7. NOVITÀ: Traccia W/T/L separatamente (allineamento con Pokemon)

UTILIZZO:
    python import_tournament_TEST.py --csv path/to/tournament.csv --season OP-TEST01

REQUIREMENTS:
    pip install gspread google-auth pandas
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import math
from datetime import datetime
import re
from typing import Dict, List, Tuple
import argparse


# ============================================
# CONFIGURAZIONE
# ============================================

# Scopes necessari per Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ID del tuo Google Sheet (lo troverai nell'URL)
# Esempio URL: https://docs.google.com/spreadsheets/d/ABC123XYZ/edit
# ABC123XYZ è il SHEET_ID
SHEET_ID = "1vvcvFlx7m_eKpF1gKBM1b81JyeXju14zp0xVjeVIf4s"  # ← FOGLIO TEST!

# Path al file JSON delle credenziali del Service Account
CREDENTIALS_FILE = "secrets/service_account.json"  # Per uso locale


# ============================================
# FUNZIONI DI CALCOLO
# ============================================

def calculate_rounds_from_participants(n_participants: int) -> int:
    """
    Calcola il numero di round in base ai partecipanti.

    Regola standard TCG:
    - 4-8 partecipanti: 3 round
    - 9-16 partecipanti: 4 round
    - 17-32 partecipanti: 5 round
    - 33-64 partecipanti: 6 round

    Args:
        n_participants: Numero di partecipanti

    Returns:
        Numero di round
    """
    if 4 <= n_participants <= 8:
        return 3
    elif 9 <= n_participants <= 16:
        return 4
    elif 17 <= n_participants <= 32:
        return 5
    elif 33 <= n_participants <= 64:
        return 6
    elif 65 <= n_participants <= 128:
        return 7
    else:
        # Fallback: calcola da max win points
        return None


import re
from datetime import datetime

def parse_csv_date_universal(filename: str) -> str:
    """
    Parsing date UNIVERSALE - accetta TUTTI i formati comuni.

    Formati supportati:
    1. YYYY_MM_DD_OP11.csv        → 2025_06_12_OP11.csv
    2. DD_Month_YYYY_OP12.csv     → 11_September_2025_OP12.csv
    3. [DD_Month_YYYY]_...        → [11_September_2025]_torneo.csv
    4. DD_MM_YYYY_OP11.csv        → 12_06_2025_OP11.csv
    5. YYYY-MM-DD_OP11.csv        → 2025-06-12_OP11.csv
    6. DD-MM-YYYY_OP11.csv        → 12-06-2025_OP11.csv

    Returns:
        str: Data formato YYYY-MM-DD
    """

    # Pattern 1: YYYY_MM_DD (priorità - formato preferito)
    match = re.search(r'(\d{4})[_-](\d{1,2})[_-](\d{1,2})', filename)
    if match:
        year, month, day = match.groups()
        # Verifica se è YYYY-MM-DD (anno > 31)
        if int(year) > 31:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Pattern 2: DD_Month_YYYY (inglese)
    match = re.search(r'(\d+)_(\w+)_(\d{4})', filename)
    if not match:
        match = re.search(r'\[(\d+)_(\w+)_(\d{4})\]', filename)

    if match:
        day, month_name, year = match.groups()
        months = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12',
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12',
            'Gennaio': '01', 'Febbraio': '02', 'Marzo': '03', 'Aprile': '04',
            'Maggio': '05', 'Giugno': '06', 'Luglio': '07', 'Agosto': '08',
            'Settembre': '09', 'Ottobre': '10', 'Novembre': '11', 'Dicembre': '12'
        }
        if month_name in months:
            return f"{year}-{months[month_name]}-{day.zfill(2)}"

    # Pattern 3: DD_MM_YYYY o DD-MM-YYYY
    match = re.search(r'(\d{1,2})[_-](\d{1,2})[_-](\d{4})', filename)
    if match:
        day, month, year = match.groups()
        # Verifica se è DD-MM-YYYY (giorno < 32)
        if int(day) <= 31:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # FALLBACK: Usa data di oggi
    print(f"⚠️  WARNING: Formato data non riconosciuto in '{filename}'")
    print(f"   Uso data odierna: {datetime.now().strftime('%Y-%m-%d')}")
    return datetime.now().strftime('%Y-%m-%d')


# TEST
if __name__ == "__main__":
    test_files = [
        "OP11_2025_06_12.csv",
        "2025_06_12_OP11.csv",
        "11_September_2025_OP12.csv",
        "[11_September_2025]_torneo.csv",
        "12_06_2025_OP11.csv",
        "2025-06-12_OP11.csv",
        "12-06-2025_OP11.csv",
    ]

    print("TEST PARSING DATE UNIVERSALE:\n")
    for f in test_files:
        result = parse_csv_date_universal(f)
        print(f"✅ {f:40s} → {result}")

def calculate_tournament_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola i punti per ogni giocatore in un torneo.

    Formula:
    - Punti Vittoria = Win Points / 3
    - Punti Ranking = N_partecipanti - (Ranking - 1)
    - Punti Totali = Punti Vittoria + Punti Ranking

    Args:
        df: DataFrame con i risultati dal CSV

    Returns:
        DataFrame arricchito con i punti calcolati
    """
    df = df.copy()
    n_participants = len(df)

    # Calcolo punti vittoria
    df['Points_Victory'] = df['Win Points'] / 3

    # Calcolo punti ranking
    df['Points_Ranking'] = n_participants - (df['Ranking'] - 1)

    # Totale
    df['Points_Total'] = df['Points_Victory'] + df['Points_Ranking']

    return df


def identify_record_categories(df: pd.DataFrame, n_rounds: int) -> pd.DataFrame:
    """
    Identifica le categorie X-0, X-1, Altri per ogni giocatore.

    Args:
        df: DataFrame con i risultati
        n_rounds: Numero di round del torneo

    Returns:
        DataFrame con colonna 'Category' aggiunta
    """
    df = df.copy()

    # Calcolo losses
    df['Losses'] = n_rounds - (df['Win Points'] / 3)

    # Categoria
    df['Category'] = df['Losses'].apply(lambda x:
        'X-0' if x == 0 else ('X-1' if x == 1 else 'OTHER')
    )

    # Record (es. "4-0", "3-1")
    df['Record'] = df.apply(
        lambda row: f"{int(row['Win Points']/3)}-{int(row['Losses'])}",
        axis=1
    )

    return df


def calculate_vouchers(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """
    Calcola i buoni negozio per un torneo.

    Logica:
    1. Fondo = partecipanti × entry_fee
    2. Costo buste = floor(partecipanti/3) × pack_cost
    3. Rimanente = Fondo - Costo buste
    4. 2€ a tutti gli "Altri" (non X-0 né X-1)
    5. Il resto diviso tra X-0 e X-1 con rapporto x0_ratio:x1_ratio
    6. Arrotondamento a 0.50€

    Args:
        df: DataFrame con risultati e categorie
        config: Dict con entry_fee, pack_cost, x0_ratio, x1_ratio, rounding

    Returns:
        DataFrame con colonna 'Voucher_Amount' aggiunta
    """
    df = df.copy()
    n_participants = len(df)

    # 1. Fondo totale
    entry_fee = config.get('entry_fee', 5.0)
    total_fund = n_participants * entry_fee

    # 2. Costo buste
    pack_cost = config.get('pack_cost', 6.0)
    n_packs = math.floor(n_participants / 3)
    packs_cost = n_packs * pack_cost

    # 3. Rimanente da distribuire
    remaining = total_fund - packs_cost

    # Prendo solo la top (min 8 o tutti se meno)
    top_size = min(8, n_participants)
    df_top = df.head(top_size).copy()

    # Conta per categoria nella top
    n_x0 = len(df_top[df_top['Category'] == 'X-0'])
    n_x1 = len(df_top[df_top['Category'] == 'X-1'])
    n_others = len(df_top[df_top['Category'] == 'OTHER'])

    # 4. Distribuzione agli "Altri"
    others_total = n_others * 2.0
    remaining_for_top = remaining - others_total

    # 5. Calcolo X-0 e X-1
    x0_ratio = config.get('x0_ratio', 1.90)
    x1_ratio = config.get('x1_ratio', 1.00)
    rounding = config.get('rounding', 0.50)

    if n_x0 > 0 or n_x1 > 0:
        divisor = n_x0 * x0_ratio + n_x1 * x1_ratio
        base_amount = remaining_for_top / divisor if divisor > 0 else 0

        x0_amount_raw = base_amount * x0_ratio
        x1_amount_raw = base_amount * x1_ratio

        # Arrotondamento
        x0_amount = round(x0_amount_raw / rounding) * rounding
        x1_amount = round(x1_amount_raw / rounding) * rounding
    else:
        x0_amount = 0
        x1_amount = 0

    # 6. Assegno i buoni
    df['Voucher_Amount'] = 0.0

    for idx, row in df_top.iterrows():
        if row['Category'] == 'X-0':
            df.loc[idx, 'Voucher_Amount'] = x0_amount
        elif row['Category'] == 'X-1':
            df.loc[idx, 'Voucher_Amount'] = x1_amount
        else:
            df.loc[idx, 'Voucher_Amount'] = 2.0

    # Calcolo leftover
    total_distributed = df['Voucher_Amount'].sum()
    leftover = remaining - total_distributed

    # Aggiungo info al dataframe per reference
    df.attrs['voucher_info'] = {
        'total_fund': total_fund,
        'packs_cost': packs_cost,
        'remaining': remaining,
        'total_distributed': total_distributed,
        'leftover': leftover,
        'n_x0': n_x0,
        'n_x1': n_x1,
        'n_others': n_others
    }

    return df


def _round_to_half(value: float) -> float:
    """Arrotonda a multipli di 0.50"""
    return round(value * 2) / 2


# ============================================
# FUNZIONI GOOGLE SHEETS
# ============================================

def connect_to_sheet():
    """
    Connette al Google Sheet usando le credenziali del Service Account.

    Returns:
        Oggetto Spreadsheet di gspread
    """
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    return sheet


def get_season_config(sheet, season_id: str) -> Dict:
    """
    Recupera la configurazione di una stagione dal foglio Config.

    Args:
        sheet: Oggetto Spreadsheet
        season_id: ID della stagione (es. "OP12")

    Returns:
        Dict con la configurazione
    """
    ws = sheet.worksheet("Config")

    # Leggiamo manualmente per evitare problemi con colonne vuote
    all_values = ws.get_all_values()

    # Auto-detect header row: produzione usa riga 4, TEST usa riga 1
    if len(all_values) >= 4 and all_values[3] and 'Season_ID' in all_values[3]:
        # Produzione: header a riga 4 (indice 3)
        header_idx = 3
        data_start_idx = 4
    else:
        # TEST: header a riga 1 (indice 0)
        header_idx = 0
        data_start_idx = 1

    headers = all_values[header_idx]

    # Puliamo gli header rimuovendo stringhe vuote
    clean_headers = []
    for h in headers:
        if h and h.strip():  # Solo header non vuoti
            clean_headers.append(h.strip())
        else:
            break  # Stop al primo header vuoto

    # Convertiamo in lista di dict
    data = []
    for row in all_values[data_start_idx:]:  # Dalla riga dopo header
        if not any(row[:len(clean_headers)]):  # Skip righe completamente vuote
            continue
        row_dict = {}
        for i, header in enumerate(clean_headers):
            if i < len(row):
                row_dict[header] = row[i]
        if row_dict.get('Season_ID'):  # Solo righe con Season_ID
            data.append(row_dict)

    # Funzione helper per convertire numeri (gestisce virgola italiana)
    def to_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        # Sostituisce virgola con punto
        return float(str(value).replace(',', '.'))

    # Cerca la stagione
    for row in data:
        if row['Season_ID'] == season_id:
            return {
                'season_id': row['Season_ID'],
                'tcg': row['TCG'],
                'season_name': row['Season_Name'],
                'entry_fee': to_float(row['Entry_Fee']),
                'pack_cost': to_float(row['Pack_Cost']),
                'x0_ratio': to_float(row['X0_Ratio']),
                'x1_ratio': to_float(row['X1_Ratio']),
                'rounding': to_float(row['Rounding'])
            }

    raise ValueError(f"Stagione {season_id} non trovata nel foglio Config!")


def update_seasonal_standings(sheet, season_id: str, df: pd.DataFrame, tournament_date: str, config: Dict):
    """
    Aggiorna la classifica stagionale con i nuovi risultati.

    Applica lo scarto dinamico:
    - Se stagione < 8 tornei: conta tutto
    - Se stagione >= 8 tornei: conta (totale - 2) migliori

    Args:
        sheet: Oggetto Spreadsheet
        season_id: ID stagione
        df: DataFrame con risultati torneo
        tournament_date: Data torneo
        config: Config stagione
    """
    ws_standings = sheet.worksheet("Seasonal_Standings_PROV")
    ws_results = sheet.worksheet("Results")
    ws_tournaments = sheet.worksheet("Tournaments")

    # Conta quanti tornei ci sono in questa stagione
    all_tournaments = ws_tournaments.get_all_values()
    season_tournaments = [row for row in all_tournaments[3:] if row and row[1] == season_id]
    total_tournaments = len(season_tournaments)

    print(f"      Tornei stagione: {total_tournaments}")

    # Calcola quanti tornei contare
    if total_tournaments < 8:
        max_to_count = total_tournaments
        print(f"      Scarto: NESSUNO (stagione < 8 tornei)")
    else:
        max_to_count = total_tournaments - 2
        print(f"      Scarto: Le peggiori 2 giornate (conta max {max_to_count})")

    # Leggi tutti i risultati della stagione
    all_results = ws_results.get_all_values()

    # Raggruppa per giocatore
    player_data = {}
    for row in all_results[3:]:  # Skip header
        if not row or len(row) < 9:
            continue

        result_tournament_id = row[1]
        # Verifica che sia della stagione corretta
        if not result_tournament_id.startswith(season_id):
            continue

        membership = row[2]
        points = float(row[8]) if row[8] else 0
        ranking = int(row[3]) if row[3] else 999

        if membership not in player_data:
            player_data[membership] = {
                'tournaments': [],
                'best_rank': 999
            }

        player_data[membership]['tournaments'].append({
            'date': result_tournament_id.split('_')[1] if '_' in result_tournament_id else '',
            'points': points,
            'rank': ranking,
            'win_points': float(row[4]) if len(row) > 4 and row[4] else 0
        })
        player_data[membership]['best_rank'] = min(player_data[membership]['best_rank'], ranking)

    # Calcola classifica finale con scarto
    final_standings = []

    # Crea mapping membership -> nome dai Results
    name_map = {}
    for row in all_results[3:]:
        if row and len(row) >= 10:
            membership = row[2]
            name = row[9] if len(row) > 9 and row[9] else membership
            name_map[membership] = name

    for membership, data in player_data.items():
        tournaments_played = data['tournaments']
        n_played = len(tournaments_played)

        # Ordina per punti
        sorted_tournaments = sorted(tournaments_played, key=lambda x: x['points'], reverse=True)

        # Prendi i migliori
        to_count = min(n_played, max_to_count)
        best_tournaments = sorted_tournaments[:to_count]

        total_points = sum(t['points'] for t in best_tournaments)
        
        # NUOVO: Tournament_Wins = quanti 1° posti
        tournament_wins = sum(1 for t in tournaments_played if t['rank'] == 1)
        
        # NUOVO: Match_Wins = quante partite vinte (da tutti i tornei giocati)
        match_wins = sum(int(t['win_points'] / 3) for t in tournaments_played)

        # Conta top 8
        top8_count = sum(1 for t in tournaments_played if t['rank'] <= 8)

        # Nome dal mapping
        player_name = name_map.get(membership, membership)

        final_standings.append({
            'membership': membership,
            'name': player_name,
            'total_points': total_points,
            'tournaments_played': n_played,
            'tournaments_counted': to_count,
            'tournament_wins': tournament_wins,
            'match_wins': match_wins,
            'best_rank': data['best_rank'],
            'top8_count': top8_count
        })

    # Ordina per punti
    final_standings.sort(key=lambda x: x['total_points'], reverse=True)

    # Pulisci il foglio Seasonal_Standings per questa stagione
    existing_standings = ws_standings.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(existing_standings[3:], start=4):
        if row and row[0] == season_id:
            rows_to_delete.append(i)

    # Prepara tutte le righe da scrivere
    rows_to_add = []
    for i, player in enumerate(final_standings, 1):
        standing_row = [
            season_id,
            player['membership'],
            player['name'],
            float(player['total_points']),
            int(player['tournaments_played']),
            int(player['tournaments_counted']),
            int(player['tournament_wins']),
            int(player['match_wins']),
            int(player['best_rank']),
            int(player['top8_count']),
            i
        ]
        rows_to_add.append(standing_row)

    # Trova dove iniziare a scrivere (dopo altre stagioni)
    write_start_row = 4
    for i, row in enumerate(existing_standings[3:], start=4):
        if not row or not row[0]:
            break
        if row[0] != season_id:
            write_start_row = i + 1
    
    # Se c'erano dati vecchi di questa stagione, scrivi da lì
    if rows_to_delete:
        write_start_row = min(rows_to_delete)
    
    # BATCH WRITE - scrivi da riga fissa
    if rows_to_add:
        end_row = write_start_row + len(rows_to_add) - 1
        ws_standings.update(values=rows_to_add, range_name=f"A{write_start_row}:K{end_row}", value_input_option='RAW')
        
        # Pulisci righe vecchie sotto (se ce ne sono)
        if rows_to_delete and max(rows_to_delete) > end_row:
            ws_standings.batch_clear([f"A{end_row+1}:K{max(rows_to_delete)}"])

    print(f"      ✅ Classifica aggiornata: {len(final_standings)} giocatori")


def create_backup(sheet, action: str, tournament_id: str, description: str, data: Dict):
    """
    Crea un backup prima di modificare i dati.

    Args:
        sheet: Oggetto Spreadsheet
        action: Tipo di azione (es. "IMPORT", "UPDATE", "DELETE")
        tournament_id: ID del torneo
        description: Descrizione del backup
        data: Dati da salvare in JSON
    """
    ws = sheet.worksheet("Backups")

    backup_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_json = json.dumps(data, ensure_ascii=False)

    ws.append_row([backup_id, timestamp, action, tournament_id, description, data_json])
    print(f"✅ Backup creato: {backup_id}")


def check_duplicate_tournament(sheet, tournament_id: str) -> bool:
    """
    Controlla se un torneo è già stato importato.
    Se esiste, chiede all'utente se sovrascrivere.

    Returns:
        True = Procedi (nuovo o sovrascrivi)
        False = Annulla import
    """
    ws_tournaments = sheet.worksheet("Tournaments")
    existing = ws_tournaments.get_all_values()

    # Cerca tournament_id esistente
    existing_row = None
    for i, row in enumerate(existing[3:], start=4):
        if row and row[0] == tournament_id:
            existing_row = i
            break

    if not existing_row:
        return True  # Nuovo torneo, procedi

    # Torneo già esistente!
    print("\n" + "="*60)
    print("⚠️  ATTENZIONE! TORNEO GIÀ IMPORTATO!")
    print("="*60)
    print(f"\nTournament_ID: {tournament_id}")
    print(f"Importato il: {existing[existing_row-1][6] if len(existing[existing_row-1]) > 6 else 'N/A'}")
    print("\nCosa vuoi fare?")
    print("  [S] Sovrascrivere (cancella vecchio + reimporta)")
    print("  [A] Annullare import")

    while True:
        choice = input("\nScelta [S/A]: ").strip().upper()
        if choice in ['S', 'A']:
            break
        print("❌ Scelta non valida! Digita S o A")

    if choice == 'A':
        print("\n❌ Import annullato dall'utente.")
        return False

    # Sovrascrittura: cancella vecchi dati
    print("\n🗑️  Cancellazione vecchi dati...")

    # Cancella da Tournaments (1 riga sola, OK così)
    ws_tournaments.delete_rows(existing_row)
    print("   ✅ Tournaments")

    # Cancella da Results (batch clear)
    ws_results = sheet.worksheet("Results")
    results_data = ws_results.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(results_data[3:], start=4):
        if row and row[1] == tournament_id:
            rows_to_delete.append(i)
    if rows_to_delete:
        first_row = min(rows_to_delete)
        last_row = max(rows_to_delete)
        ws_results.batch_clear([f"A{first_row}:J{last_row}"])
    print(f"   ✅ Results ({len(rows_to_delete)} righe)")

    # Cancella da Vouchers (batch clear)
    ws_vouchers = sheet.worksheet("Vouchers")
    vouchers_data = ws_vouchers.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(vouchers_data[3:], start=4):
        if row and row[1] == tournament_id:
            rows_to_delete.append(i)
    if rows_to_delete:
        first_row = min(rows_to_delete)
        last_row = max(rows_to_delete)
        ws_vouchers.batch_clear([f"A{first_row}:L{last_row}"])
    print(f"   ✅ Vouchers ({len(rows_to_delete)} righe)")

    print("\n✅ Vecchi dati cancellati. Procedo con reimport...\n")
    return True


def import_tournament_to_sheet(sheet, csv_path: str, season_id: str):
    """
    Importa un torneo completo nel Google Sheet.

    Questo è il MAIN WORKFLOW che:
    1. Legge il CSV
    2. Calcola tutto
    3. Fa backup
    4. Scrive nei vari fogli
    5. Aggiorna le classifiche

    Args:
        sheet: Oggetto Spreadsheet
        csv_path: Path al file CSV
        season_id: ID della stagione
    """
    print(f"\n🚀 IMPORT TORNEO: {csv_path}")
    print(f"📊 Stagione: {season_id}\n")

    # 0. VALIDAZIONE FILENAME (PRIMA DI TUTTO!)
    csv_filename = csv_path.split('/')[-1].split('\\')[-1]
    try:
        tournament_date = parse_csv_date_universal(csv_filename)
    except ValueError as e:
        print(f"\n{e}")
        return None

    tournament_id = f"{season_id}_{tournament_date}"

    # 0.1 CHECK DOPPIO IMPORT
    if not check_duplicate_tournament(sheet, tournament_id):
        return None  # Utente ha annullato

    # 1. Leggi CSV
    print("📂 Lettura CSV...")
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Info base
    n_participants = len(df)

    # Calcola round da numero partecipanti (Swiss standard)
    if n_participants <= 8:
        n_rounds = 3
    elif n_participants <= 16:
        n_rounds = 4
    elif n_participants <= 32:
        n_rounds = 5
    elif n_participants <= 64:
        n_rounds = 6
    elif n_participants <= 128:
        n_rounds = 7
    else:
        n_rounds = 8

    print(f"   👥 Partecipanti: {n_participants}")
    print(f"   📅 Data: {tournament_date}")
    print(f"   🎮 Round: {n_rounds}")
    print(f"   🏆 Vincitore: {df.iloc[0]['User Name']}")

    # 2. Recupera config stagione
    print(f"\n⚙️  Recupero configurazione {season_id}...")
    config = get_season_config(sheet, season_id)
    print(f"   💶 Entry fee: {config['entry_fee']}€")
    print(f"   📦 Pack cost: {config['pack_cost']}€")

    # 3. Calcola punti
    print(f"\n🧮 Calcolo punti...")
    df = calculate_tournament_points(df)

    # 4. Identifica categorie
    print(f"🎯 Identificazione X-0/X-1...")
    df = identify_record_categories(df, n_rounds)

    # 5. Calcola buoni
    print(f"💰 Calcolo buoni negozio...")
    df = calculate_vouchers(df, config)

    voucher_info = df.attrs.get('voucher_info', {})
    print(f"   💵 Fondo totale: {voucher_info.get('total_fund', 0)}€")
    print(f"   📦 Costo buste: {voucher_info.get('packs_cost', 0)}€")
    print(f"   💸 Distribuito: {voucher_info.get('total_distributed', 0)}€")
    print(f"   💰 Rimane: {voucher_info.get('leftover', 0)}€")

    # 6. Crea backup (DISABILITATO PER TEST)
    # print(f"\n💾 Creazione backup...")
    # backup_data = {
    #     'csv_filename': csv_filename,
    #     'date': tournament_date,
    #     'participants': n_participants,
    #     'config': config
    # }
    # create_backup(sheet, "IMPORT", tournament_id, f"Import {csv_filename}", backup_data)

    # 7. Scrivi dati nei fogli
    print(f"\n📝 Scrittura dati...")

    # 7.1 Scrivi nel foglio Tournaments
    print(f"   📊 Foglio Tournaments...")
    ws_tournaments = sheet.worksheet("Tournaments")
    tournament_row = [
        tournament_id,
        season_id,
        tournament_date,
        n_participants,
        n_rounds,
        csv_filename,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        df.iloc[0]['User Name']
    ]
    ws_tournaments.append_row(tournament_row)

    # 7.2 Scrivi nel foglio Results
    print(f"   📊 Foglio Results...")
    ws_results = sheet.worksheet("Results")
    for idx, row in df.iterrows():
        membership = str(row['Membership Number']).zfill(10)

        # Calcola W/T/L per One Piece (allineamento con Pokemon)
        win_points = int(row['Win Points'])
        match_w = int(win_points / 3)  # One Piece: W = 3 punti
        match_t = 0  # One Piece NON ha pareggi
        match_l = n_rounds - match_w  # Losses = round totali - vittorie

        result_row = [
            f"{tournament_id}_{membership}",
            tournament_id,
            membership,
            int(row['Ranking']),
            win_points,
            row['OMW %'],
            float(row['Points_Victory']),
            float(row['Points_Ranking']),
            float(row['Points_Total']),
            row['User Name'],
            match_w,  # Match_W (col 10) - One Piece specific
            match_t,  # Match_T (col 11) - sempre 0 per One Piece
            match_l   # Match_L (col 12) - One Piece specific
        ]
        ws_results.append_row(result_row)

    # 7.3 Scrivi nel foglio Vouchers (DISABILITATO PER TEST)
    # print(f"   📊 Foglio Vouchers...")
    # ws_vouchers = sheet.worksheet("Vouchers")
    # for idx, row in df.head(min(8, n_participants)).iterrows():
    #     membership = str(row['Membership Number']).zfill(10)
    #     voucher_row = [
    #         f"{tournament_id}_{membership}",
    #         tournament_id,
    #         membership,
    #         row['User Name'],
    #         int(row['Ranking']),
    #         row['Record'],
    #         row['Category'],
    #         float(row['Voucher_Amount']),
    #         float(row['Voucher_Amount']),
    #         'DRAFT',
    #         ''
    #     ]
    #     ws_vouchers.append_row(voucher_row)

    # 7.4 Aggiorna/crea giocatori nel foglio Players
    print(f"   📊 Foglio Players...")
    ws_players = sheet.worksheet("Players")

    # IMPORTANTE: Re-fetch Results per avere i dati appena scritti
    import time
    time.sleep(1)  # Aspetta che Google Sheets propaghi
    ws_results = sheet.worksheet("Results")

    # TCG corrente
    tcg = config['tcg']

    existing_players = ws_players.get_all_values()
    # Chiave: (Membership, TCG)
    existing_dict = {(row[0], row[2]): i for i, row in enumerate(existing_players[1:], start=2) if row and len(row) > 2}

    # Calcola statistiche lifetime da Results (filtrate per TCG)
    all_results = ws_results.get_all_values()
    lifetime_stats = {}

    for row in all_results[1:]:
        if not row or len(row) < 10:
            continue
        membership = row[2]
        tournament_id = row[1]

        # Deriva TCG dal Tournament_ID (es: OP12_2025-01-15 → OP)
        season_id = tournament_id.split('_')[0] if '_' in tournament_id else ''
        row_tcg = ''.join(ch for ch in season_id if ch.isalpha()).upper()

        # Filtra solo risultati del TCG corrente
        if row_tcg != tcg:
            continue

        ranking = int(row[3]) if row[3] else 999
        win_points = float(row[4]) if row[4] else 0
        points_total = float(row[8]) if row[8] else 0

        # Check W/T/L columns
        if len(row) >= 13 and row[10] and row[11] and row[12]:
            match_w = int(row[10])
            match_t = int(row[11])
            match_l = int(row[12])
        else:
            match_w = int(win_points / 3)
            match_t = 0
            match_l = 0

        key = (membership, tcg)
        if key not in lifetime_stats:
            lifetime_stats[key] = {
                'total_tournaments': 0,
                'tournament_wins': 0,
                'match_w': 0,
                'match_t': 0,
                'match_l': 0,
                'total_points': 0
            }

        lifetime_stats[key]['total_tournaments'] += 1
        if ranking == 1:
            lifetime_stats[key]['tournament_wins'] += 1
        lifetime_stats[key]['match_w'] += match_w
        lifetime_stats[key]['match_t'] += match_t
        lifetime_stats[key]['match_l'] += match_l
        lifetime_stats[key]['total_points'] += points_total
    
    # Aggiorna o crea giocatori
    players_to_update = []
    players_to_add = []

    for idx, row in df.iterrows():
        membership = str(row['Membership Number']).zfill(10)
        display_name = row['User Name']
        key = (membership, tcg)

        stats = lifetime_stats.get(key, {
            'total_tournaments': 0,
            'tournament_wins': 0,
            'match_w': 0,
            'match_t': 0,
            'match_l': 0,
            'total_points': 0
        })

        if key in existing_dict:
            # Aggiorna giocatore esistente
            row_idx = existing_dict[key]
            players_to_update.append({
                'range': f"D{row_idx}:K{row_idx}",  # Extended range with TCG + W/T/L
                'values': [[
                    tournament_date,
                    stats['total_tournaments'],
                    stats['tournament_wins'],
                    stats['match_w'],
                    stats['match_t'],
                    stats['match_l'],
                    stats['total_points']
                ]]
            })
        else:
            # Nuovo giocatore
            player_row = [
                membership,
                display_name,
                tcg,  # Colonna TCG
                tournament_date,
                tournament_date,
                stats['total_tournaments'],
                stats['tournament_wins'],
                stats['match_w'],
                stats['match_t'],
                stats['match_l'],
                stats['total_points']
            ]
            players_to_add.append(player_row)
    
    # BATCH WRITE - update esistenti (1 chiamata!)
    if players_to_update:
        ws_players.batch_update(players_to_update, value_input_option='RAW')
    
    # BATCH WRITE - nuovi giocatori (1 chiamata!)
    if players_to_add:
        ws_players.append_rows(players_to_add, value_input_option='RAW')

    # 7.5 Aggiorna classifica stagionale (DISABILITATO PER TEST)
    # print(f"   📊 Foglio Seasonal_Standings...")
    # update_seasonal_standings(sheet, season_id, df, tournament_date, config)

    # 7.6 Aggiorna Total_Tournaments in Config (DISABILITATO PER TEST)
    # print(f"   📊 Aggiorna Config...")
    # ws_config = sheet.worksheet("Config")
    # config_data = ws_config.get_all_values()
    # for i, row in enumerate(config_data[4:], start=5):
    #     if row and row[0] == season_id:
    #         current_count = int(row[5]) if row[5] else 0
    #         ws_config.update_cell(i, 6, current_count + 1)
    #         break

    print(f"\n✅ IMPORT COMPLETATO!")
    print(f"\n📊 RIASSUNTO:")
    print(f"   🏆 Vincitore: {df.iloc[0]['User Name']} ({df.iloc[0]['Record']})")
    print(f"   💰 Buono vincitore: {df.iloc[0]['Voucher_Amount']}€")
    print(f"   📈 Punti vincitore: {df.iloc[0]['Points_Total']:.1f}")

    print(f"\n🎯 TOP 5:")
    for idx, row in df.head(5).iterrows():
        print(f"   {row['Ranking']}° {row['User Name']}: {row['Points_Total']:.1f} pt, {row['Record']}, {row['Voucher_Amount']}€")

    return df


# ============================================
# MAIN
# ============================================

def main():
    """Entry point dello script"""
    parser = argparse.ArgumentParser(description='Import tournament CSV to Pulci League')
    parser.add_argument('--csv', required=True, help='Path to tournament CSV file')
    parser.add_argument('--season', required=True, help='Season ID (e.g. OP12)')
    parser.add_argument('--test', action='store_true', help='Test mode (no write to sheet)')

    args = parser.parse_args()

    if args.test:
        print("🧪 TEST MODE - Nessuna scrittura su Google Sheets\n")

    # Connetti al foglio
    print("🔗 Connessione a Google Sheets...")
    try:
        sheet = connect_to_sheet()
        print(f"✅ Connesso a: {sheet.title}\n")
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        print("\n💡 CONTROLLA:")
        print("   1. SHEET_ID è corretto")
        print("   2. CREDENTIALS_FILE esiste")
        print("   3. Service Account ha accesso al foglio")
        return

    # Import torneo
    try:
        df_result = import_tournament_to_sheet(sheet, args.csv, args.season)
        print("\n🎉 TUTTO OK!")

    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
