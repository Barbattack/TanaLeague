# -*- coding: utf-8 -*-
"""
parse_pokemon_tdf_TEST.py - Pokemon Tournament Import from TDF (TEST VERSION)
============================================================================
QUESTO SCRIPT USA IL GOOGLE SHEET DI TEST - NON QUELLO DI PRODUZIONE!
"""

import xml.etree.ElementTree as ET
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
import argparse

# CONFIG - FOGLIO DI TEST!
SHEET_ID = "1vvcvFlx7m_eKpF1gKBM1b81JyeXju14zp0xVjeVIf4s"  # ← FOGLIO TEST!
CREDENTIALS_FILE = "secrets/service_account.json"  # Per uso locale
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def connect_sheet():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

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
        points_victory = win_points / 3
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
            round(points_victory, 2),
            round(points_ranking, 2),
            round(points_total, 2),
            players[uid],
            w,  # Match_W (col 10) - Pokemon specific
            t,  # Match_T (col 11) - Pokemon specific
            l   # Match_L (col 12) - Pokemon specific
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

def import_to_sheet(data, test_mode=False):
    sheet = connect_sheet()

    # Check duplicates
    ws_tournaments = sheet.worksheet("Tournaments")
    existing = ws_tournaments.col_values(1)[3:] if len(ws_tournaments.col_values(1)) > 3 else []
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

    print("📊 Importazione Pokemon TDF su FOGLIO TEST...")
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
            ws_results.append_rows(data['results'])
    print(f"✅ Results: {len(data['results'])} giocatori")

    # 3. Matches (batch)
    if not test_mode:
        ws_matches = sheet.worksheet("Pokemon_Matches")
        if data['matches']:
            ws_matches.append_rows(data['matches'])
    print(f"✅ Matches: {len(data['matches'])} match")

    # 4. Update Players (con aggregazione lifetime stats come One Piece)
    if not test_mode:
        ws_players = sheet.worksheet("Players")

        # IMPORTANTE: Re-fetch Results per avere i dati appena scritti
        import time
        time.sleep(1)  # Aspetta che Google Sheets propaghi
        ws_results = sheet.worksheet("Results")

        # Deriva TCG dal season_id (es: PKM-TEST01 → PKM)
        tcg = ''.join(ch for ch in data['tournament'][0].split('_')[0] if ch.isalpha()).upper()

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

            # Deriva TCG dal Tournament_ID
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

        for uid, name in data['players'].items():
            uid_padded = uid.zfill(10)
            tournament_date = data['tournament'][2]
            key = (uid_padded, tcg)

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
                    uid_padded,
                    name,
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

        print(f"✅ Players: {len(players_to_add)} nuovi, {len(players_to_update)} aggiornati")
    else:
        # Test mode - simulate
        print(f"✅ Players: {len(data['players'])} totali (stats non calcolate in test mode)")

    if test_mode:
        print("\n⚠️  TEST COMPLETATO - Nessun dato scritto")
    else:
        print("\n🎉 IMPORT COMPLETATO su FOGLIO TEST!")
    print(f"API calls: {0 if test_mode else '~6-8 (inclusa aggregazione stats)'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Pokemon tournament from TDF file (TEST VERSION)')
    parser.add_argument('--tdf', required=True, help='Path to .tdf file')
    parser.add_argument('--season', required=True, help='Season ID (es: PKM-TEST01)')
    parser.add_argument('--test', action='store_true', help='Test mode (no write)')

    args = parser.parse_args()

    print("=" * 60)
    print("🧪 TEST VERSION - USA FOGLIO TEST!")
    print("=" * 60)
    print(f"🔍 Parsing TDF: {args.tdf}")
    print(f"📅 Season: {args.season}\n")

    data = parse_tdf(args.tdf, args.season)
    import_to_sheet(data, test_mode=args.test)
