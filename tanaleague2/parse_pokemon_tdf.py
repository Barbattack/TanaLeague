# -*- coding: utf-8 -*-
"""
=================================================================================
TanaLeague v2.0 - Pokémon TCG Tournament Import
=================================================================================

Script import tornei Pokémon da file TDF/XML esportato da Play! Pokémon Tournament software.

FUNZIONALITÀ COMPLETE:
1. Parsing TDF/XML (formato ufficiale Play! Pokémon):
   - Tournament meta (nome, ID, date, n_rounds)
   - Player list con membership numbers
   - Standings finali (rank, points, W-D-L record, OMW%)
   - Match H2H (head-to-head per future features)
2. Calcolo punti TanaLeague:
   - Punti: Wins * 3 + Draws * 1
   - Ranking points: (n_partecipanti - rank + 1)
   - Punti totali: Win points + Ranking points
3. Scrittura Google Sheets:
   - Tournaments: Meta torneo
   - Results: Risultati individuali giocatori
   - Players: Anagrafica giocatori (update)
   - Pokemon_Matches: Match H2H (opzionale)
4. Aggiornamento Seasonal_Standings_PROV (live rankings con drop logic)
5. Achievement unlock automatico per tutti i partecipanti

UTILIZZO:
    # Import normale
    python parse_pokemon_tdf.py --tdf tournament.tdf --season PKM-FS25

    # Test mode (dry run, no write)
    python parse_pokemon_tdf.py --tdf tournament.tdf --season PKM-FS25 --test

FORMATO TDF (XML Play! Pokémon):
    <?xml version="1.0"?>
    <tournament>
      <name>Fall League 2025</name>
      <players>
        <player id="12345" name="Mario Rossi" />
      </players>
      <standings>
        <standing rank="1" player="12345" points="12" record="4-0-0" />
      </standings>
    </tournament>

REQUIREMENTS:
    pip install gspread google-auth

OUTPUT CONSOLE:
    🚀 IMPORT TORNEO POKEMON: tournament.tdf
    📊 Stagione: PKM-FS25
    📂 Parsing TDF... ✅
    👥 Partecipanti: 12
    🎮 Round: 4
    🏆 Vincitore: Mario Rossi
    💾 Scrittura dati... ✅
    📈 Aggiornamento standings... ✅
    🎮 Check achievement... ✅
    ✅ IMPORT COMPLETATO!
=================================================================================
"""

import xml.etree.ElementTree as ET
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
import argparse
from achievements import check_and_unlock_achievements

# CONFIG
SHEET_ID = "19ZF35DTmgZG8v1GfzKE5JmMUTXLo300vuw_AdrgQPFE"  # MODIFICA!
CREDENTIALS_FILE = "/home/latanadellepulci/tanaleague2/service_account_credentials.json"  # Path PythonAnywhere
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def connect_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def to_float(value):
    """
    Converte un valore in float gestendo formato italiano (virgola) e internazionale (punto).

    Args:
        value: Valore da convertire (str, int, float)

    Returns:
        float: Valore convertito

    Examples:
        to_float("14,33") -> 14.33
        to_float("14.33") -> 14.33
        to_float(14) -> 14.0
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Rimuovi spazi bianchi
        value = value.strip()
        if not value:
            return 0.0
        # Sostituisci virgola con punto
        value = value.replace(',', '.')
        return float(value)
    return 0.0

def parse_tdf(filepath, season_id):
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Tournament info
    tournament_name = root.find('.//name').text
    tournament_id = root.find('.//id').text
    tournament_date = root.find('.//startdate').text  # MM/DD/YYYY
    date_obj = datetime.strptime(tournament_date, '%m/%d/%Y')
    date_str = date_obj.strftime('%Y-%m-%d')

    # Tournament ID con season
    tid = f"{season_id}_{date_str}"

    # Players map - SOLO dalla sezione <players> principale
    players = {}
    players_section = root.find('./players')
    if players_section is None:
        raise ValueError("Sezione <players> non trovata nel TDF!")

    print(f"🔍 Trovati {len(players_section.findall('player'))} player nella sezione principale")

    for p in players_section.findall('player'):
        userid = p.get('userid')
        firstname = p.find('firstname').text.strip()
        lastname = p.find('lastname').text.strip()
        players[userid] = f"{firstname} {lastname}"

    # Standings
    standings = {}
    for s in root.findall('.//standings/pod[@category="2"]/player'):
        userid = s.get('id')
        place = int(s.get('place'))
        standings[userid] = place

    # Calculate records from matches
    records = {uid: {'w': 0, 'l': 0, 't': 0, 'opponents': []} for uid in players.keys()}
    matches_data = []

    for round_elem in root.findall('.//rounds/round'):
        round_num = round_elem.get('number')
        for match in round_elem.findall('matches/match'):
            outcome = match.get('outcome')
            timestamp = match.find('timestamp').text if match.find('timestamp') is not None else ''

            if outcome == '5':  # BYE
                continue

            p1_elem = match.find('player1')
            p2_elem = match.find('player2')

            if p1_elem is None or p2_elem is None:
                continue

            p1 = p1_elem.get('userid')
            p2 = p2_elem.get('userid')

            # Track opponents
            records[p1]['opponents'].append(p2)
            records[p2]['opponents'].append(p1)

            # outcome: 1=p1 win, 2=p2 win, 3=tie
            if outcome == '1':
                records[p1]['w'] += 1
                records[p2]['l'] += 1
                winner, loser = p1, p2
            elif outcome == '2':
                records[p2]['w'] += 1
                records[p1]['l'] += 1
                winner, loser = p2, p1
            elif outcome == '3':
                records[p1]['t'] += 1
                records[p2]['t'] += 1
                winner, loser = None, None
            else:
                winner, loser = None, None

            # Save match
            if winner:
                match_id = f"{tid}_R{round_num}_{winner}_{loser}"
                matches_data.append([match_id, tid, round_num, winner, loser, timestamp])

    # Calculate OMW%
    omw_pct = {}
    for uid in players.keys():
        opps = records[uid]['opponents']
        if not opps:
            omw_pct[uid] = 0.0
            continue
        opp_wins = sum(records[opp]['w'] for opp in opps)
        opp_total = sum(records[opp]['w'] + records[opp]['l'] + records[opp]['t'] for opp in opps)
        omw_pct[uid] = (opp_wins / opp_total * 100) if opp_total > 0 else 0.0

    # Calculate points (Pokemon system: W=3, T=1, L=0)
    results_data = []
    for uid in players.keys():
        if uid not in standings:
            continue

        rank = standings[uid]
        w, l, t = records[uid]['w'], records[uid]['l'], records[uid]['t']
        win_points = w * 3 + t * 1

        # Points formula
        n_participants = len(standings)
        points_victory = win_points  # win_points è già corretto (W*3 + T*1)
        points_ranking = n_participants - (rank - 1)
        points_total = points_victory + points_ranking

        result_id = f"{tid}_{uid.zfill(10)}"
        results_data.append([
            result_id,
            tid,
            uid.zfill(10),
            rank,
            win_points,
            round(omw_pct[uid], 2),
            points_victory,      # No decimals - già intero
            points_ranking,      # No decimals - già intero
            points_total,        # No decimals - già intero
            players[uid],
            w,  # Match_W
            t,  # Match_T
            l   # Match_L
        ])

    # Sort by rank
    results_data.sort(key=lambda x: x[3])

    tournament_data = [
        tid,
        season_id,
        date_str,
        len(standings),
        len(root.findall('.//rounds/round')),
        f"{tournament_name}_{tournament_id}.tdf",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        results_data[0][9] if results_data else ''
    ]

    return {
        'tournament': tournament_data,
        'results': results_data,
        'matches': matches_data,
        'players': players
    }

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

    # Conta quanti tornei ci sono in questa stagione
    all_tournaments = ws_tournaments.get_all_values()
    season_tournaments = [row for row in all_tournaments[3:] if row and row[1] == season_id]
    total_tournaments = len(season_tournaments)

    print(f"\n   🔄 Aggiornamento classifica stagionale {season_id}...")
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
        points = to_float(row[8]) if row[8] else 0
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
            'win_points': to_float(row[4]) if len(row) > 4 and row[4] else 0,
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

def import_to_sheet(data, test_mode=False):
    sheet = connect_sheet()

    # Check duplicates
    ws_tournaments = sheet.worksheet("Tournaments")
    existing = ws_tournaments.col_values(1)[3:]
    tid = data['tournament'][0]

    if tid in existing:
        print(f"⚠️  Torneo {tid} già importato!")
        if test_mode:
            print("(Test mode - non sovrascrivo)")
            return
        resp = input("Sovrascrivere? (y/n): ")
        if resp.lower() != 'y':
            print("Import annullato.")
            return

    print("📊 Importazione Pokemon TDF...")
    if test_mode:
        print("⚠️  TEST MODE - Nessuna scrittura effettiva\n")

    # 1. Tournaments
    if not test_mode:
        ws_tournaments.append_row(data['tournament'])
    print(f"✅ Tournament: {tid}")

    # 2. Results (batch)
    if not test_mode:
        ws_results = sheet.worksheet("Results")
        if data['results']:
            ws_results.append_rows(data['results'], value_input_option='RAW')
    print(f"✅ Results: {len(data['results'])} giocatori")

    # 3. Matches (batch)
    if not test_mode:
        ws_matches = sheet.worksheet("Pokemon_Matches")
        if data['matches']:
            ws_matches.append_rows(data['matches'], value_input_option='RAW')
    print(f"✅ Matches: {len(data['matches'])} match")

    # 4. Update Players
    if not test_mode:
        ws_players = sheet.worksheet("Players")
        all_player_rows = ws_players.get_all_values()[3:]  # Skip header

        # Crea mapping membership -> [row_index, row_data]
        player_map = {}
        for i, row in enumerate(all_player_rows, start=4):  # Start from row 4
            if row and row[0]:
                player_map[row[0]] = {'index': i, 'data': row}

        new_players = []
        rows_to_update = []

        # Calcola statistiche dal torneo corrente per ogni giocatore
        player_stats = {}
        for result in data['results']:
            membership = result[2]
            rank = result[3]
            w = result[10]  # Match_W
            match_points = result[8]  # Points_Total

            player_stats[membership] = {
                'rank': rank,
                'wins': 1 if rank == 1 else 0,
                'match_wins': w,
                'points': match_points
            }

        for uid, name in data['players'].items():
            uid_padded = uid.zfill(10)
            stats = player_stats.get(uid_padded, {'rank': 999, 'wins': 0, 'match_wins': 0, 'points': 0})

            if uid_padded in player_map:
                # Aggiorna giocatore esistente
                existing = player_map[uid_padded]
                old_data = existing['data']

                # Leggi valori esistenti
                first_seen = old_data[2] if len(old_data) > 2 else data['tournament'][2]
                last_seen = data['tournament'][2]
                tournaments = int(old_data[4]) + 1 if len(old_data) > 4 and old_data[4] else 1
                wins = int(old_data[5]) + stats['wins'] if len(old_data) > 5 and old_data[5] else stats['wins']
                match_wins = int(old_data[6]) + stats['match_wins'] if len(old_data) > 6 and old_data[6] else stats['match_wins']
                total_points = to_float(old_data[7]) + stats['points'] if len(old_data) > 7 and old_data[7] else stats['points']

                updated_row = [
                    uid_padded,
                    name,
                    first_seen,
                    last_seen,
                    tournaments,
                    wins,
                    match_wins,
                    total_points
                ]

                rows_to_update.append({
                    'range': f"A{existing['index']}:H{existing['index']}",
                    'values': [updated_row]
                })
            else:
                # Nuovo giocatore
                new_players.append([
                    uid_padded,
                    name,
                    data['tournament'][2],  # first_seen
                    data['tournament'][2],  # last_seen
                    1,  # tournaments
                    stats['wins'],  # wins
                    stats['match_wins'],  # match_wins
                    stats['points']  # total_points
                ])

        # Batch update giocatori esistenti
        if rows_to_update:
            ws_players.batch_update(rows_to_update, value_input_option='RAW')

        # Batch append nuovi giocatori
        if new_players:
            ws_players.append_rows(new_players, value_input_option='RAW')

        print(f"✅ Players: {len(rows_to_update)} aggiornati, {len(new_players)} nuovi")
    else:
        # Test mode - simulate
        print(f"✅ Players: {len(data['players'])} totali")

    # 5. Aggiorna Seasonal_Standings
    if not test_mode:
        season_id = data['tournament'][1]
        tournament_date = data['tournament'][2]
        update_seasonal_standings(sheet, season_id, tournament_date)
        print(f"✅ Seasonal Standings aggiornate per {season_id}")

        # 6. Check e sblocca achievement
        check_and_unlock_achievements(sheet, data)

    if test_mode:
        print("\n⚠️  TEST COMPLETATO - Nessun dato scritto")
    else:
        print("\n🎉 IMPORT COMPLETATO!")
    print(f"API calls: {0 if test_mode else 4}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Pokemon tournament from TDF file')
    parser.add_argument('--tdf', required=True, help='Path to .tdf file')
    parser.add_argument('--season', required=True, help='Season ID (es: PKM-FS25)')
    parser.add_argument('--test', action='store_true', help='Test mode (no write)')

    args = parser.parse_args()

    print(f"🔍 Parsing TDF: {args.tdf}")
    print(f"📅 Season: {args.season}\n")

    data = parse_tdf(args.tdf, args.season)
    import_to_sheet(data, test_mode=args.test)
