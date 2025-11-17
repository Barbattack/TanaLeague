#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_riftbound.py - Riftbound Tournament Import from PDF
============================================================

Importa tornei Riftbound da PDF esportati dal software di gestione.

FORMATO PDF ATTESO:
Rank  Player                    Points  W-L-D   OMW    GW     OGW
1     Cogliati, Pietro          12      4-0-0   62.5%  100%   62.5%
      (2metalupo)

UTILIZZO:
    python import_riftbound.py --pdf path/to/tournament.pdf --season RFB01

Il nickname tra parentesi viene usato come Membership Number.
"""

import re
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import argparse
import pdfplumber
from typing import Dict, List

# CONFIG
SHEET_ID = "19ZF35DTmgZG8v1GfzKE5JmMUTXLo300vuw_AdrgQPFE"
CREDENTIALS_FILE = "/home/latanadellepulci/tanaleague2/service_account_credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def connect_sheet():
    """Connette al Google Sheet"""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def extract_nickname(player_line: str) -> str:
    """
    Estrae il nickname dalle parentesi.
    Input: "Cogliati, Pietro (2metalupo)"
    Output: "2metalupo"
    """
    match = re.search(r'\(([^)]+)\)', player_line)
    if match:
        return match.group(1)
    return ""

def parse_pdf(pdf_path: str, season_id: str, tournament_date: str) -> Dict:
    """
    Legge il PDF e estrae i dati del torneo.
    Usa strategia ibrida: tabelle + testo + layout analysis.

    Returns:
        Dict con chiavi:
        - tournament: [tid, season_id, date, participants, rounds, filename, import_date, winner]
        - results: [[result_id, tid, membership, rank, win_points, omw, pts_victory, pts_ranking, pts_total, name, w, t, l], ...]
        - players: {membership: name, ...}
    """
    print(f"📄 Apertura PDF: {pdf_path}")

    tournament_id = f"{season_id}_{tournament_date}"
    results_data = []
    players = {}

    with pdfplumber.open(pdf_path) as pdf:
        # STRATEGIA 1: Prova estrazione tabelle (più affidabile)
        print("🔍 Strategia 1: Estrazione tabelle...")

        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if tables:
                print(f"  📊 Pagina {page_num}: {len(tables)} tabelle trovate")

                for table_idx, table in enumerate(tables):
                    print(f"    Tabella {table_idx + 1}: {len(table)} righe")

                    # DEBUG: Stampa TUTTE le righe per capire il formato
                    print(f"    🐛 DEBUG - Analisi righe:")
                    for i, row in enumerate(table):
                        if row and len(row) > 0:
                            rank_col = row[0] if len(row) > 0 else "N/A"
                            name_col = row[1][:30] if len(row) > 1 and row[1] else "N/A"
                            cols_count = len(row)
                            print(f"      Row {i}: Cols={cols_count}, Rank=[{rank_col}], Name=[{name_col}...]")

                    # Processa ogni riga della tabella
                    for row_idx, row in enumerate(table):
                        if not row or len(row) < 7:
                            continue

                        # Formato: [Rank, Name\n(Nick), Points, W-L-D, OMW%, GW%, OGW%]
                        try:
                            rank_str = row[0].strip() if row[0] else ""
                            name_nick = row[1].strip() if row[1] else ""
                            points_str = row[2].strip() if row[2] else ""
                            wld_str = row[3].strip() if row[3] else ""
                            omw_str = row[4].strip().replace('%', '') if row[4] else ""
                            gw_str = row[5].strip().replace('%', '') if row[5] else ""
                            ogw_str = row[6].strip().replace('%', '') if row[6] else ""

                            # Valida rank (deve essere numero)
                            if not rank_str.isdigit():
                                continue

                            rank = int(rank_str)

                            # Estrai nome e nickname
                            # Formato: "Cogliati, Pietro\n(2metalupo)"
                            if '\n' in name_nick and '(' in name_nick:
                                parts = name_nick.split('\n')
                                name = parts[0].strip()
                                # Estrai nickname dalle parentesi
                                nick_match = re.search(r'\(([^)]+)\)', parts[1])
                                if not nick_match:
                                    continue
                                nickname = nick_match.group(1)
                            else:
                                # Fallback: cerca nickname in tutto il testo
                                nick_match = re.search(r'\(([^)]+)\)', name_nick)
                                if not nick_match:
                                    continue
                                nickname = nick_match.group(1)
                                name = name_nick[:nick_match.start()].replace('\n', ' ').strip()

                            # Parse W-L-D
                            wld_match = re.match(r'(\d+)-(\d+)-(\d+)', wld_str)
                            if not wld_match:
                                continue

                            w = int(wld_match.group(1))
                            l = int(wld_match.group(2))
                            d = int(wld_match.group(3))

                            points = int(points_str)
                            omw = float(omw_str) if omw_str else 0.0
                            gw = float(gw_str) if gw_str else 0.0
                            ogw = float(ogw_str) if ogw_str else 0.0

                            win_points = w * 3 + d * 1

                            players[nickname] = name

                            results_data.append({
                                'rank': rank,
                                'name': name,
                                'membership': nickname,
                                'points': points,
                                'w': w,
                                'l': l,
                                'd': d,
                                'win_points': win_points,
                                'omw': omw,
                                'gw': gw,
                                'ogw': ogw
                            })

                            print(f"  ✓ Rank {rank}: {name} ({nickname}) - {w}-{l}-{d}")

                        except (ValueError, IndexError, AttributeError) as e:
                            # Debug: stampa righe che vengono skippate
                            if row and len(row) >= 4 and row[0] and row[0].strip().isdigit():
                                print(f"  ⚠️  SKIPPED Row {row_idx}: Rank={row[0]}, Col1=[{row[1][:50] if row[1] else ''}], Error={type(e).__name__}")
                            continue

    # Fine estrazione PDF
    if not results_data:
        raise ValueError("❌ Nessun giocatore trovato nel PDF! Verifica il formato.")

    print(f"\n✅ Parsing completato: {len(results_data)} giocatori trovati!")
    # Ordina per rank
    results_data.sort(key=lambda x: x['rank'])

    n_participants = len(results_data)

    # Calcola rounds dal record del primo (assumendo tutti giocano stesso numero)
    first_player = results_data[0]
    n_rounds = first_player['w'] + first_player['l'] + first_player['d']

    # Calcola punti TanaLeague
    formatted_results = []
    for r in results_data:
        rank = r['rank']
        win_points = r['win_points']

        # Formula TanaLeague
        points_victory = win_points / 3
        points_ranking = n_participants - (rank - 1)
        points_total = points_victory + points_ranking

        result_id = f"{tournament_id}_{r['membership']}"

        formatted_results.append([
            result_id,
            tournament_id,
            r['membership'],
            rank,
            win_points,
            round(r['omw'], 2),
            round(points_victory, 2),
            round(points_ranking, 2),
            round(points_total, 2),
            r['name'],
            r['w'],
            r['d'],  # T (ties/draws)
            r['l']
        ])

    # Winner
    winner_name = results_data[0]['name']

    # Tournament metadata
    tournament_data = [
        tournament_id,
        season_id,
        tournament_date,
        n_participants,
        n_rounds,
        f"{pdf_path.split('/')[-1]}",
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        winner_name
    ]

    return {
        'tournament': tournament_data,
        'results': formatted_results,
        'players': players
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

def import_to_sheet(data: Dict, test_mode: bool = False):
    """Importa i dati nel Google Sheet"""
    sheet = connect_sheet()

    tid = data['tournament'][0]

    if not check_duplicate_tournament(sheet, tid):
        return

    print(f"\n📊 Importazione Riftbound PDF...")
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
            ws_results.append_rows(data['results'])
    print(f"✅ Results: {len(data['results'])} giocatori")

    # 3. Update Players
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
    else:
        print(f"✅ Players: {len(data['players'])} totali (stats non calcolate in test mode)")

    if test_mode:
        print("\n⚠️  TEST COMPLETATO - Nessun dato scritto")
    else:
        print("\n🎉 IMPORT COMPLETATO!")

def parse_date_from_filename(filename: str) -> str:
    """
    Estrae data dal nome file PDF.
    Formato atteso: RFB_YYYY_MM_DD.pdf
    """
    match = re.search(r'(\d{4})[_-](\d{1,2})[_-](\d{1,2})', filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Fallback: usa data odierna
    print(f"⚠️  WARNING: Data non trovata nel filename, uso data odierna")
    return datetime.now().strftime('%Y-%m-%d')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import Riftbound tournament from PDF')
    parser.add_argument('--pdf', required=True, help='Path to PDF file')
    parser.add_argument('--season', required=True, help='Season ID (es: RFB01)')
    parser.add_argument('--test', action='store_true', help='Test mode (no write)')

    args = parser.parse_args()

    # Parse date from filename
    tournament_date = parse_date_from_filename(args.pdf)

    print(f"🔍 Parsing PDF: {args.pdf}")
    print(f"📅 Season: {args.season}")
    print(f"📆 Date: {tournament_date}\n")

    data = parse_pdf(args.pdf, args.season, tournament_date)
    import_to_sheet(data, test_mode=args.test)
