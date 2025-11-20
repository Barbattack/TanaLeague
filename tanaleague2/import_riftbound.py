#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=================================================================================
TanaLeague v2.0 - Riftbound TCG Tournament Import (CSV Multi-Round)
=================================================================================

Script import tornei Riftbound da CSV esportati dal software di gestione tornei.

FUNZIONALITÀ COMPLETE:
1. Parsing CSV Multi-Round:
   - Supporto file multipli (Round 1, Round 2, Round 3, etc.)
   - Aggregazione automatica risultati per User ID
   - Estrazione dati dettagliati: W-L-D, Event Record, Round Record
   - Estrazione match H2H con vincitori (NEW!)
2. Estrazione dati:
   - User ID univoco (usato come Membership Number)
   - Nome completo (First Name + Last Name)
   - Event Record finale (dal CSV ultimo round)
   - Match wins dettagliati per stats avanzate
   - Match dettagliati: Player 1/2, Winner, Round, Table, Result (NEW!)
3. Calcolo punti TanaLeague:
   - Win points: Wins * 3 + Draws * 1
   - Ranking points: (n_partecipanti - rank + 1)
   - Punti totali: Win points + Ranking points
4. Scrittura Google Sheets:
   - Tournaments: Meta torneo
   - Results: Risultati individuali giocatori con W-L-D
   - Riftbound_Matches: Match dettagliati con vincitori (NEW!)
   - Players: Anagrafica giocatori (update con User ID come membership)
5. Aggiornamento Seasonal_Standings_PROV (live rankings con drop logic)
6. Achievement unlock automatico per tutti i partecipanti

FORMATO CSV ATTESO (da software Riftbound):
    Colonne chiave:
    - Col 0: Table Number
    - Col 4: Player 1 User ID
    - Col 5-6: Player 1 First/Last Name
    - Col 8: Player 2 User ID
    - Col 9-10: Player 2 First/Last Name
    - Col 13: Match Result (formato: "Nome Cognome: 2-0-0") ← Vincitore match!
    - Col 16: Player 1 Event Record (W-L-D totale torneo)
    - Col 17: Player 2 Event Record (W-L-D totale torneo)

UTILIZZO:
    # Import singolo round
    python import_riftbound.py --csv RFB_2025_11_17_R1.csv --season RFB01

    # Import multi-round (RACCOMANDATO)
    python import_riftbound.py --csv RFB_2025_11_17_R1.csv,RFB_2025_11_17_R2.csv,RFB_2025_11_17_R3.csv --season RFB01

    # Test mode (dry run, no write)
    python import_riftbound.py --csv file1.csv,file2.csv --season RFB01 --test

REQUIREMENTS:
    pip install gspread google-auth

OUTPUT CONSOLE:
    🚀 IMPORT TORNEO RIFTBOUND: 3 CSV files
    📊 Stagione: RFB01
    📂 Parsing CSV...
       ✅ Round 1: 8 matches
       ✅ Round 2: 8 matches
       ✅ Round 3: 8 matches
       📊 16 giocatori totali
       🎮 Match estratti: 24
    💾 Scrittura dati... ✅
    ✅ Riftbound_Matches: 24 match salvati (NEW!)
    📈 Aggiornamento standings... ✅
    🎮 Check achievement... ✅
    ✅ IMPORT COMPLETATO!
=================================================================================
"""

import csv
import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import argparse
from typing import Dict, List
from achievements import check_and_unlock_achievements

# CONFIG
SHEET_ID = "19ZF35DTmgZG8v1GfzKE5JmMUTXLo300vuw_AdrgQPFE"
CREDENTIALS_FILE = "/home/latanadellepulci/tanaleague2/service_account_credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def connect_sheet():
    """Connette al Google Sheet"""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def parse_wld_record(record_str: str) -> tuple:
    """
    Parse W-L-D record string.
    Input: "2-1-0" or "3-0-1"
    Output: (wins, losses, draws)
    """
    match = re.match(r'(\d+)-(\d+)-(\d+)', record_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0

def parse_csv_rounds(csv_files: List[str], season_id: str, tournament_date: str) -> Dict:
    """
    Legge tutti i CSV dei round e aggrega i risultati finali.

    Args:
        csv_files: Lista di path ai CSV (uno per round)
        season_id: ID stagione (es. RFB01)
        tournament_date: Data torneo (YYYY-MM-DD)

    Returns:
        Dict con chiavi:
        - tournament: [tid, season_id, date, participants, rounds, filename, import_date, winner]
        - results: [[result_id, tid, membership, rank, win_points, omw, pts_victory, pts_ranking, pts_total, name, w, t, l], ...]
        - players: {membership: name, ...}
        - matches: [[tid, p1_membership, p1_name, p2_membership, p2_name, winner_membership, round, table, match_result], ...]
    """
    print(f"📂 Parsing {len(csv_files)} CSV file(s)...")

    tournament_id = f"{season_id}_{tournament_date}"
    players_data = {}  # user_id -> {name, event_record, rounds_played}
    matches_data = []  # Lista di match dettagliati

    # Leggi tutti i CSV
    for csv_idx, csv_path in enumerate(csv_files, 1):
        print(f"   📄 Round {csv_idx}: {csv_path.split('/')[-1]}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header

            match_count = 0
            for row in reader:
                if len(row) < 18:
                    continue

                # Player 1
                p1_id = row[4].strip()
                p1_first = row[5].strip()
                p1_last = row[6].strip()
                p1_event_record = row[16].strip() if len(row) > 16 else ""

                # Player 2
                p2_id = row[8].strip()
                p2_first = row[9].strip()
                p2_last = row[10].strip()
                p2_event_record = row[17].strip() if len(row) > 17 else ""

                # Match data
                table_number = row[0].strip() if row[0] else ""
                match_result = row[13].strip() if len(row) > 13 else ""

                if not p1_id or not p2_id:
                    continue

                match_count += 1

                # Memorizza dati giocatori (sovrascrive con ogni round, l'ultimo avrà il record finale)
                p1_name = f"{p1_first} {p1_last}".strip()
                p2_name = f"{p2_first} {p2_last}".strip()

                if p1_id:
                    players_data[p1_id] = {
                        'name': p1_name,
                        'event_record': p1_event_record,
                        'rounds_played': csv_idx
                    }

                if p2_id:
                    players_data[p2_id] = {
                        'name': p2_name,
                        'event_record': p2_event_record,
                        'rounds_played': csv_idx
                    }

                # Parse vincitore dal Match Result (formato: "Nome Cognome: 2-0-0")
                winner_membership = ""
                if match_result and ":" in match_result:
                    winner_name = match_result.split(":")[0].strip()
                    # Match con Player 1 o Player 2
                    if winner_name.lower() == p1_name.lower():
                        winner_membership = p1_id
                    elif winner_name.lower() == p2_name.lower():
                        winner_membership = p2_id
                    else:
                        # Fallback: cerca se il nome del vincitore contiene parte del nome del giocatore
                        if p1_last.lower() in winner_name.lower() or p1_first.lower() in winner_name.lower():
                            winner_membership = p1_id
                        elif p2_last.lower() in winner_name.lower() or p2_first.lower() in winner_name.lower():
                            winner_membership = p2_id

                # Salva match
                matches_data.append([
                    tournament_id,
                    p1_id,
                    p1_name,
                    p2_id,
                    p2_name,
                    winner_membership,
                    csv_idx,  # Round number
                    table_number,
                    match_result
                ])

            print(f"      ✅ {match_count} matches")

    if not players_data:
        raise ValueError("❌ Nessun giocatore trovato nei CSV! Verifica il formato.")

    print(f"\n   📊 {len(players_data)} giocatori totali trovati!")

    # Calcola ranking finale basato su Event Record dell'ultimo round
    results_data = []

    for user_id, data in players_data.items():
        w, l, d = parse_wld_record(data['event_record'])

        # Calcola punti Swiss (come MTG/Pokemon)
        points = w * 3 + d * 1

        results_data.append({
            'membership': user_id,
            'name': data['name'],
            'w': w,
            'l': l,
            'd': d,
            'points': points,
            'rounds_played': data['rounds_played']
        })

    # Ordina per punti (poi per wins se pari punti)
    results_data.sort(key=lambda x: (x['points'], x['w']), reverse=True)

    # Assegna rank
    for rank, player in enumerate(results_data, 1):
        player['rank'] = rank

    n_participants = len(results_data)
    n_rounds = max(p['rounds_played'] for p in results_data)

    # Calcola punti TanaLeague
    formatted_results = []
    for r in results_data:
        rank = r['rank']
        win_points = r['w'] * 3 + r['d'] * 1

        # Formula TanaLeague
        points_victory = win_points  # win_points è già corretto (W*3 + D*1)
        points_ranking = n_participants - (rank - 1)
        points_total = points_victory + points_ranking

        result_id = f"{tournament_id}_{r['membership']}"

        formatted_results.append([
            result_id,
            tournament_id,
            r['membership'],
            rank,
            win_points,
            0,  # OMW (non disponibile nei CSV, lasciamo 0)
            points_victory,      # No decimals - già intero
            points_ranking,      # No decimals - già intero
            points_total,        # No decimals - già intero
            r['name'],
            r['w'],
            r['d'],  # T (ties/draws)
            r['l']
        ])

    # Winner
    winner_name = results_data[0]['name']

    # Tournament metadata
    csv_filenames = ",".join([f.split('/')[-1] for f in csv_files])
    tournament_data = [
        tournament_id,
        season_id,
        tournament_date,
        n_participants,
        n_rounds,
        csv_filenames,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        winner_name
    ]

    # Players dict (membership -> name)
    players = {r['membership']: r['name'] for r in results_data}

    print(f"\n✅ Parsing completato!")
    print(f"   🏆 Winner: {winner_name}")
    print(f"   👥 Partecipanti: {n_participants}")
    print(f"   🔄 Round: {n_rounds}")
    print(f"   🎮 Match estratti: {len(matches_data)}")

    return {
        'tournament': tournament_data,
        'results': formatted_results,
        'players': players,
        'matches': matches_data
    }

def check_duplicate_tournament(sheet, tournament_id: str) -> bool:
    """Controlla se il torneo esiste già"""
    ws_tournaments = sheet.worksheet("Tournaments")
    existing = ws_tournaments.col_values(1)[3:]  # Skip header

    if tournament_id in existing:
        print(f"⚠️  Torneo {tournament_id} già importato!")
        resp = input("Sovrascrivere? (y/n): ")
        if resp.lower() != 'y':
            print("Import annullato.")
            return False
    return True

def get_season_config(sheet, season_id: str) -> Dict:
    """Recupera configurazione stagione dal foglio Config"""
    ws = sheet.worksheet("Config")
    all_values = ws.get_all_values()
    headers = all_values[3]

    clean_headers = []
    for h in headers:
        if h and h.strip():
            clean_headers.append(h.strip())
        else:
            break

    data = []
    for row in all_values[4:]:
        if not any(row[:len(clean_headers)]):
            continue
        row_dict = {}
        for i, header in enumerate(clean_headers):
            if i < len(row):
                row_dict[header] = row[i]
        if row_dict.get('Season_ID'):
            data.append(row_dict)

    def to_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace(',', '.'))

    for row in data:
        if row['Season_ID'] == season_id:
            return {
                'season_id': season_id,
                'entry_fee': to_float(row.get('Entry_Fee', 5)),
                'pack_cost': to_float(row.get('Pack_Cost', 6))
            }

    raise ValueError(f"Stagione {season_id} non trovata nel foglio Config!")

def update_seasonal_standings(sheet, season_id: str, tournament_date: str):
    """
    Aggiorna la classifica stagionale con i nuovi risultati.

    Applica lo scarto dinamico:
    - Se stagione < 8 tornei: conta tutto
    - Se stagione >= 8 tornei: conta (totale - 2) migliori

    Args:
        sheet: Oggetto Spreadsheet
        season_id: ID stagione
        tournament_date: Data torneo
    """
    ws_standings = sheet.worksheet("Seasonal_Standings_PROV")
    ws_results = sheet.worksheet("Results")
    ws_tournaments = sheet.worksheet("Tournaments")
    ws_config = sheet.worksheet("Config")

    # Leggi status season dalla Config
    config_data = ws_config.get_all_values()
    season_status = None
    for row in config_data[4:]:  # Skip header (righe 1-3)
        if row and row[0] == season_id:  # Col 0 = Season_ID
            season_status = row[4].strip().upper() if len(row) > 4 else ""  # Col 4 = Status
            break

    # Conta quanti tornei ci sono in questa stagione
    all_tournaments = ws_tournaments.get_all_values()
    season_tournaments = [row for row in all_tournaments[3:] if row and row[1] == season_id]
    total_tournaments = len(season_tournaments)

    print(f"\n   🔄 Aggiornamento classifica stagionale {season_id}...")
    print(f"      Tornei stagione: {total_tournaments}")
    print(f"      Status stagione: {season_status}")

    # Calcola quanti tornei contare
    if season_status == "ARCHIVED":
        max_to_count = total_tournaments
        print(f"      Scarto: NESSUNO (stagione ARCHIVED - archivio dati)")
    elif total_tournaments < 8:
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

        # Leggi Match_W se disponibile (colonna 10)
        match_w = int(row[10]) if len(row) > 10 and row[10] else 0

        player_data[membership]['tournaments'].append({
            'date': result_tournament_id.split('_')[1] if '_' in result_tournament_id else '',
            'points': points,
            'rank': ranking,
            'win_points': float(row[4]) if len(row) > 4 and row[4] else 0,
            'match_w': match_w
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

        # Tournament_Wins = quanti 1° posti
        tournament_wins = sum(1 for t in tournaments_played if t['rank'] == 1)

        # Match_Wins = quante partite vinte (leggi da Match_W se disponibile)
        match_wins = sum(t.get('match_w', int(t['win_points'] / 3)) for t in tournaments_played)

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
            i  # Position
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

def import_to_sheet(data: Dict, test_mode: bool = False):
    """Importa i dati nel Google Sheet"""
    sheet = connect_sheet()

    tid = data['tournament'][0]

    if not check_duplicate_tournament(sheet, tid):
        return

    print(f"\n📊 Importazione Riftbound CSV...")
    if test_mode:
        print("⚠️  TEST MODE - Nessuna scrittura effettiva\n")

    # 1. Tournaments
    if not test_mode:
        ws_tournaments = sheet.worksheet("Tournaments")
        ws_tournaments.append_row(data['tournament'])
    print(f"✅ Tournament: {tid}")

    # 2. Results
    if not test_mode:
        ws_results = sheet.worksheet("Results")
        if data['results']:
            ws_results.append_rows(data['results'], value_input_option='RAW')
    print(f"✅ Results: {len(data['results'])} giocatori")

    # 3. Riftbound_Matches (NEW!)
    if not test_mode and 'matches' in data and data['matches']:
        try:
            ws_matches = sheet.worksheet("Riftbound_Matches")
            ws_matches.append_rows(data['matches'], value_input_option='RAW')
            print(f"✅ Riftbound_Matches: {len(data['matches'])} match salvati")
        except Exception as e:
            print(f"⚠️  Warning: Impossibile scrivere Riftbound_Matches: {e}")
            print(f"   Assicurati che il foglio 'Riftbound_Matches' esista con header corretto!")
    elif test_mode and 'matches' in data:
        print(f"✅ Riftbound_Matches: {len(data['matches'])} match (non salvati in test mode)")

    # 4. Update Players
    if not test_mode:
        ws_players = sheet.worksheet("Players")

        import time
        time.sleep(1)
        ws_results = sheet.worksheet("Results")

        tcg = ''.join(ch for ch in data['tournament'][0].split('_')[0] if ch.isalpha()).upper()

        existing_players = ws_players.get_all_values()
        existing_dict = {(row[0], row[2]): i for i, row in enumerate(existing_players[3:], start=4) if row and len(row) > 2}

        all_results = ws_results.get_all_values()
        lifetime_stats = {}

        for row in all_results[3:]:
            if not row or len(row) < 10:
                continue
            membership = row[2]
            tournament_id = row[1]

            season_id = tournament_id.split('_')[0] if '_' in tournament_id else ''
            row_tcg = ''
            for ch in season_id:
                if ch.isalpha():
                    row_tcg += ch
                else:
                    break
            row_tcg = row_tcg.upper()

            if row_tcg != tcg:
                continue

            ranking = int(row[3]) if row[3] else 999
            win_points = float(row[4]) if row[4] else 0
            points_total = float(row[8]) if row[8] else 0

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

        players_to_update = []
        players_to_add = []

        for membership, name in data['players'].items():
            tournament_date = data['tournament'][2]
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
                row_idx = existing_dict[key]
                players_to_update.append({
                    'range': f"D{row_idx}:K{row_idx}",
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
                player_row = [
                    membership,
                    name,
                    tcg,
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

        if players_to_update:
            ws_players.batch_update(players_to_update, value_input_option='RAW')

        if players_to_add:
            ws_players.append_rows(players_to_add, value_input_option='RAW')

        print(f"✅ Players: {len(players_to_add)} nuovi, {len(players_to_update)} aggiornati")

        # 5. Aggiorna Seasonal_Standings
        season_id = data['tournament'][1]
        tournament_date = data['tournament'][2]
        update_seasonal_standings(sheet, season_id, tournament_date)

        # 6. Check e sblocca achievement
        check_and_unlock_achievements(sheet, data)
    else:
        print(f"✅ Players: {len(data['players'])} totali (stats non calcolate in test mode)")

    if test_mode:
        print("\n⚠️  TEST COMPLETATO - Nessun dato scritto")
    else:
        print("\n🎉 IMPORT COMPLETATO!")

def parse_date_from_filename(filename: str) -> str:
    """
    Estrae data dal nome file CSV.
    Formato atteso: RFB_YYYY_MM_DD_RX.csv
    """
    match = re.search(r'(\d{4})[_-](\d{1,2})[_-](\d{1,2})', filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Fallback: usa data odierna
    print(f"⚠️  WARNING: Data non trovata nel filename, uso data odierna")
    return datetime.now().strftime('%Y-%m-%d')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Riftbound tournament from CSV (multi-round support)')
    parser.add_argument('--csv', required=True, help='Path to CSV file(s), comma-separated for multi-round (es: R1.csv,R2.csv,R3.csv)')
    parser.add_argument('--season', required=True, help='Season ID (es: RFB01)')
    parser.add_argument('--test', action='store_true', help='Test mode (no write)')

    args = parser.parse_args()

    # Parse CSV list
    csv_files = [f.strip() for f in args.csv.split(',')]

    # Parse date from first filename
    tournament_date = parse_date_from_filename(csv_files[0])

    print(f"🚀 IMPORT TORNEO RIFTBOUND")
    print(f"📊 Stagione: {args.season}")
    print(f"📅 Data: {tournament_date}")
    print(f"📂 File CSV: {len(csv_files)}\n")

    data = parse_csv_rounds(csv_files, args.season, tournament_date)
    import_to_sheet(data, test_mode=args.test)
