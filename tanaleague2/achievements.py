#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=================================================================================
TanaLeague v2.0 - Achievement System
=================================================================================

Sistema di unlock automatico achievement durante import tornei.

ARCHITETTURA:
- 2 fogli Google Sheets:
  * Achievement_Definitions: 40 achievement con meta (name, points, rarity, etc.)
  * Player_Achievements: Track unlock per giocatore

WORKFLOW:
1. Script import (CSV/PDF/TDF) chiama check_and_unlock_achievements()
2. Per ogni giocatore del torneo:
   - Calcola stats lifetime complete (tornei, wins, top8, streaks, etc.)
   - Check achievement semplici (contatori: tournaments_played, wins, top8)
   - Check achievement special (logica custom: streaks, patterns, multi-TCG)
   - Sblocca nuovi achievement non ancora unlocked
3. Scrive in Player_Achievements con timestamp

FUNZIONI PRINCIPALI:
- load_achievement_definitions(): Carica achievement da Google Sheet (cache 5min)
- calculate_player_stats(): Calcola tutte le stats lifetime del giocatore
- check_simple_achievements(): Check achievement basati su contatori
- check_special_achievements(): Check achievement con logica complessa
- unlock_achievement(): Scrive unlock in Player_Achievements
- check_and_unlock_achievements(): Main function chiamata dagli import scripts

UTILIZZO negli import scripts:
    from achievements import check_and_unlock_achievements

    # Dopo aver importato torneo e aggiornato standings
    data = {
        'tournament': [tournament_id, season_id, date, n_participants, ...],
        'players': {membership: name, ...}
    }
    check_and_unlock_achievements(sheet, data)
=================================================================================
"""

import gspread
from datetime import datetime
from typing import Dict, List, Set, Tuple


# ============================================================================
# CACHE IN-MEMORY (evita letture ripetute Achievement_Definitions)
# ============================================================================
_achievement_cache = None
_cache_timestamp = None


# ============================================================================
# LOAD FUNCTIONS - Caricamento dati da Google Sheets
# ============================================================================

def load_achievement_definitions(sheet) -> Dict[str, Dict]:
    """
    Carica achievement definitions dal Google Sheet.
    Usa cache in-memory per evitare letture ripetute.

    Returns:
        Dict mapping achievement_id -> achievement_data
    """
    global _achievement_cache, _cache_timestamp

    # Cache valida per 5 minuti
    if _achievement_cache is not None:
        age = (datetime.now() - _cache_timestamp).total_seconds()
        if age < 300:  # 5 minuti
            return _achievement_cache

    ws = sheet.worksheet("Achievement_Definitions")
    rows = ws.get_all_values()[4:]  # Skip header (primi 4 righe)

    achievements = {}
    for row in rows:
        if not row or not row[0]:
            continue

        ach_id = row[0]
        achievements[ach_id] = {
            'id': ach_id,
            'name': row[1],
            'description': row[2],
            'category': row[3],
            'rarity': row[4],
            'emoji': row[5],
            'points': int(row[6]) if row[6] else 0,
            'requirement_type': row[7],
            'requirement_value': row[8]
        }

    _achievement_cache = achievements
    _cache_timestamp = datetime.now()

    return achievements

def load_player_achievements(sheet, membership: str) -> Set[str]:
    """
    Carica achievement già sbloccati da un giocatore.

    Returns:
        Set di achievement_id già sbloccati
    """
    ws = sheet.worksheet("Player_Achievements")
    rows = ws.get_all_values()[4:]  # Skip header

    unlocked = set()
    for row in rows:
        if row and row[0] == membership:
            unlocked.add(row[1])  # achievement_id

    return unlocked

def calculate_player_stats(sheet, membership: str, tcg: str = None) -> Dict:
    """
    Calcola statistiche complete di un giocatore dai fogli Results.

    Args:
        sheet: Google Sheet connesso
        membership: Membership number del giocatore
        tcg: Filtra per TCG specifico (opzionale)

    Returns:
        Dict con tutte le stats necessarie per check achievement
    """
    ws_results = sheet.worksheet("Results")
    all_results = ws_results.get_all_values()[3:]  # Skip header

    # Filtra risultati del giocatore
    player_results = [r for r in all_results if r and len(r) >= 10 and r[2] == membership]

    if tcg:
        # Filtra per TCG
        player_results = [r for r in player_results if r[0].startswith(tcg)]

    # Calcoli base
    tournaments_played = len(player_results)
    tournament_wins = sum(1 for r in player_results if r[3] and int(r[3]) == 1)
    top8_count = sum(1 for r in player_results if r[3] and int(r[3]) <= 8)

    # Ranks
    ranks = [int(r[3]) for r in player_results if r[3]]
    best_rank = min(ranks) if ranks else 999

    # Perfect wins (4-0 o 5-0 senza sconfitte)
    perfect_wins = 0
    for r in player_results:
        if r[3] and int(r[3]) == 1:  # Vittoria
            # Check se senza sconfitte (serve parse W-L-D se disponibile)
            # Per ora contiamo solo vittorie
            perfect_wins += 1

    # TCG giocati
    tcgs_played = set()
    tcg_wins = {}
    tcg_top8 = {}
    for r in player_results:
        season_id = r[0]
        tcg_code = season_id.split('-')[0] if '-' in season_id else 'OP'
        tcgs_played.add(tcg_code)

        if r[3] and int(r[3]) == 1:
            tcg_wins[tcg_code] = tcg_wins.get(tcg_code, 0) + 1
        if r[3] and int(r[3]) <= 8:
            tcg_top8[tcg_code] = tcg_top8.get(tcg_code, 0) + 1

    # Streak calculation (top8 consecutivi)
    current_streak_top8 = 0
    max_streak_top8 = 0
    for r in sorted(player_results, key=lambda x: x[1]):  # Ordina per tournament_id (data)
        if r[3] and int(r[3]) <= 8:
            current_streak_top8 += 1
            max_streak_top8 = max(max_streak_top8, current_streak_top8)
        else:
            current_streak_top8 = 0

    # Rank frequency (per achievement tipo "Silver Collector")
    rank_frequency = {}
    for r in player_results:
        if r[3]:
            rank = int(r[3])
            rank_frequency[rank] = rank_frequency.get(rank, 0) + 1

    # Ultimi 3 tornei (per Rookie Struggles)
    first_3_results = player_results[:3] if len(player_results) >= 3 else player_results
    first_3_wins = sum(1 for r in first_3_results if r[4] and float(r[4])/3 >= 1)

    stats = {
        'tournaments_played': tournaments_played,
        'tournament_wins': tournament_wins,
        'top8_count': top8_count,
        'best_rank': best_rank,
        'max_streak_top8': max_streak_top8,
        'tcgs_played': tcgs_played,
        'tcg_wins': tcg_wins,
        'tcg_top8': tcg_top8,
        'rank_frequency': rank_frequency,
        'first_3_wins': first_3_wins,
        'player_results': player_results  # Per check avanzati
    }

    return stats

def unlock_achievement(sheet, membership: str, achievement_id: str, tournament_id: str, progress: str = ""):
    """
    Sblocca un achievement per un giocatore.
    Scrive in Player_Achievements.

    Args:
        sheet: Google Sheet connesso
        membership: Membership number
        achievement_id: ID achievement
        tournament_id: ID torneo che ha triggato l'unlock
        progress: Opzionale, es. "3/3" per achievement progressivi
    """
    ws = sheet.worksheet("Player_Achievements")

    unlocked_date = datetime.now().strftime("%Y-%m-%d")

    row_data = [
        membership,
        achievement_id,
        unlocked_date,
        tournament_id,
        progress
    ]

    ws.append_row(row_data)


# ============================================================================
# ACHIEVEMENT CHECK FUNCTIONS - Logica unlock
# ============================================================================

def check_simple_achievements(stats: Dict, achievements: Dict, unlocked: Set) -> List[str]:
    """
    Controlla achievement semplici basati su contatori.

    Achievement "semplici" hanno requirement_type in:
    - tournaments_played: X tornei giocati
    - tournament_wins: X vittorie
    - top8_count: X top8

    Confronta valore stats con requirement_value.
    Se condizione soddisfatta, aggiunge a lista unlock.

    Args:
        stats: Stats lifetime del giocatore (da calculate_player_stats)
        achievements: Tutte le definitions (da load_achievement_definitions)
        unlocked: Set achievement_id già sbloccati (evita duplicati)

    Returns:
        Lista di achievement_id da sbloccare

    Esempi:
        ACH_LEG_001 (Debutto): tournaments_played >= 1
        ACH_GLO_001 (First Blood): tournament_wins >= 1
        ACH_CON_001 (Hot Streak): top8_count >= 2
    """
    to_unlock = []

    for ach_id, ach in achievements.items():
        if ach_id in unlocked:
            continue  # Già sbloccato

        req_type = ach['requirement_type']
        req_value = ach['requirement_value']

        # Achievement contatori semplici
        if req_type == 'tournaments_played':
            if stats['tournaments_played'] >= int(req_value):
                to_unlock.append(ach_id)

        elif req_type == 'tournament_wins':
            if stats['tournament_wins'] >= int(req_value):
                to_unlock.append(ach_id)

        elif req_type == 'top8_count':
            if stats['top8_count'] >= int(req_value):
                to_unlock.append(ach_id)

    return to_unlock

def check_special_achievements(stats: Dict, achievements: Dict, unlocked: Set, current_tournament: Dict) -> List[Tuple[str, str]]:
    """
    Controlla achievement "special" con logica complessa custom.

    Achievement "special" hanno requirement_type = "special" e requirement_value
    con chiave logica custom implementata in questa funzione.

    Logiche supportate:
    - streak_top8_N: N top8 consecutivi (es. streak_top8_4 = 4 top8 di fila)
    - rookie_struggles: Primi 3 tornei con max 3 wins totali
    - rank9_3x: Finito 9° almeno 3 volte
    - second_3x_no_wins: Finito 2° almeno 3 volte SENZA mai vincere
    - 10tournaments_no_top8: 10 tornei senza mai fare top8
    - rank_7: Finito esattamente 7°
    - rank3_3x: Finito 3° almeno 3 volte
    - multi_tcg_3+: Almeno 3 tornei in 2+ TCG diversi
    - top8_2tcg: Almeno 2 top8 in 2+ TCG diversi
    - win_all_tcg: Almeno 1 vittoria in tutti e 3 i TCG (OP, PKM, RFB)

    Args:
        stats: Stats lifetime del giocatore
        achievements: Achievement definitions
        unlocked: Achievement già sbloccati
        current_tournament: Dati torneo corrente (non sempre usato)

    Returns:
        Lista di tuple (achievement_id, progress_string) da sbloccare

    Esempio:
        streak_top8_4 → Se max_streak_top8 >= 4, ritorna ("ACH_CON_003", "4/4")
    """
    to_unlock = []

    for ach_id, ach in achievements.items():
        if ach_id in unlocked:
            continue

        if ach['requirement_type'] != 'special':
            continue

        req_value = ach['requirement_value']

        # === CONSISTENCY ACHIEVEMENTS ===
        if req_value == 'streak_top8_2' and stats['max_streak_top8'] >= 2:
            to_unlock.append((ach_id, f"{stats['max_streak_top8']}/2"))

        elif req_value == 'streak_top8_4' and stats['max_streak_top8'] >= 4:
            to_unlock.append((ach_id, f"{stats['max_streak_top8']}/4"))

        elif req_value == 'streak_top8_6' and stats['max_streak_top8'] >= 6:
            to_unlock.append((ach_id, f"{stats['max_streak_top8']}/6"))

        # === HEARTBREAK ACHIEVEMENTS ===
        elif req_value == 'rookie_struggles':
            # Primi 3 tornei con max 3 vittorie totali
            if stats['tournaments_played'] >= 3 and stats['first_3_wins'] <= 3:
                to_unlock.append((ach_id, f"{stats['first_3_wins']}/3 wins"))

        elif req_value == 'rank9_3x':
            # Piazzato 9° almeno 3 volte
            if stats['rank_frequency'].get(9, 0) >= 3:
                to_unlock.append((ach_id, f"{stats['rank_frequency'][9]}/3"))

        elif req_value == 'second_3x_no_wins':
            # Piazzato 2° almeno 3 volte SENZA MAI vincere
            if stats['rank_frequency'].get(2, 0) >= 3 and stats['tournament_wins'] == 0:
                to_unlock.append((ach_id, f"{stats['rank_frequency'][2]}/3"))

        elif req_value == '10tournaments_no_top8':
            # 10+ tornei senza mai top8
            if stats['tournaments_played'] >= 10 and stats['top8_count'] == 0:
                to_unlock.append((ach_id, f"{stats['tournaments_played']} tournaments"))

        # === WILDCARDS ACHIEVEMENTS ===
        elif req_value == 'rank_7':
            # Piazzato esattamente 7°
            if stats['rank_frequency'].get(7, 0) >= 1:
                to_unlock.append((ach_id, "Rank 7"))

        elif req_value == 'rank3_3x':
            # Piazzato 3° almeno 3 volte
            if stats['rank_frequency'].get(3, 0) >= 3:
                to_unlock.append((ach_id, f"{stats['rank_frequency'][3]}/3"))

        # === LEGACY ACHIEVEMENTS ===
        elif req_value == 'multi_tcg_3+':
            # Almeno 3 tornei in 2 TCG diversi
            tcg_counts = {}
            for tcg in stats['tcgs_played']:
                count = sum(1 for r in stats['player_results'] if r[0].startswith(tcg))
                tcg_counts[tcg] = count

            tcgs_with_3plus = [tcg for tcg, count in tcg_counts.items() if count >= 3]
            if len(tcgs_with_3plus) >= 2:
                to_unlock.append((ach_id, f"{len(tcgs_with_3plus)} TCGs"))

        elif req_value == 'top8_2tcg':
            # 2 top8 in almeno 2 TCG diversi
            tcgs_with_2top8 = [tcg for tcg, count in stats['tcg_top8'].items() if count >= 2]
            if len(tcgs_with_2top8) >= 2:
                to_unlock.append((ach_id, f"{len(tcgs_with_2top8)} TCGs"))

        elif req_value == 'win_all_tcg':
            # Vittoria in tutti e 3 i TCG
            if len(stats['tcg_wins']) >= 3:
                to_unlock.append((ach_id, "All 3 TCGs"))

        # === ACHIEVEMENT BASATI SU TORNEO CORRENTE ===
        # (Richiedono current_tournament data - implementato in fase 2)
        # Esempi: perfect_win, points_42, record_2-2, etc.

    return to_unlock


# ============================================================================
# MAIN FUNCTION - Called by import scripts
# ============================================================================

def check_and_unlock_achievements(sheet, import_data: Dict):
    """
    **FUNZIONE PRINCIPALE**: Controlla e sblocca achievement dopo import torneo.

    Questa funzione viene chiamata da tutti gli import scripts (One Piece,
    Pokemon, Riftbound) DOPO aver aggiornato Results e Seasonal_Standings.

    WORKFLOW COMPLETO:
    1. Carica achievement definitions (40 achievement)
    2. Per ogni giocatore nel torneo appena importato:
       a. Carica achievement già sbloccati
       b. Calcola stats lifetime complete
       c. Check achievement semplici (contatori)
       d. Check achievement special (logica complessa)
       e. Sblocca nuovi achievement (scrive in Player_Achievements)
       f. Print console con achievement sbloccati

    OUTPUT CONSOLE:
        🎮 Check achievement...
          📋 40 achievement caricati
          🏆 0000012345: 🎬 First Blood
          🏆 0000067890: 📅 Regular (5/5)
          ✅ 2 achievement sbloccati!

    Args:
        sheet: Google Sheet connesso (gspread.Spreadsheet)
        import_data (Dict): Dati torneo importato con chiavi:
            - 'tournament': [tournament_id, season_id, date, n_participants, ...]
            - 'players': {membership: name, ...}

    Returns:
        None (scrive direttamente in Player_Achievements sheet)

    Esempio chiamata da import script:
        data = {
            'tournament': ['OP12_2025-11-18', 'OP12', '2025-11-18', 16, ...],
            'players': {'0000012345': 'Mario Rossi', '0000067890': 'Luigi Verdi'}
        }
        check_and_unlock_achievements(sheet, data)
    """
    print("🎮 Check achievement...")

    # 1. Carica achievement definitions
    achievements = load_achievement_definitions(sheet)
    print(f"  📋 {len(achievements)} achievement caricati")

    # 2. Estrai info torneo
    tournament_id = import_data['tournament'][0]
    players_in_tournament = import_data.get('players', {})

    if not players_in_tournament:
        print("  ⚠️  Nessun giocatore nel torneo, skip achievement check")
        return

    # 3. Processo ogni giocatore e raccogli achievement da sbloccare (BATCH)
    total_unlocked = 0
    achievements_to_unlock = []  # Lista di [membership, ach_id, date, tournament_id, progress]

    for membership in players_in_tournament.keys():
        membership_padded = membership.zfill(10)

        # Carica achievement già sbloccati
        unlocked = load_player_achievements(sheet, membership_padded)

        # Calcola stats
        stats = calculate_player_stats(sheet, membership_padded)

        # Check achievement semplici
        simple_unlocks = check_simple_achievements(stats, achievements, unlocked)

        # Check achievement special
        current_tournament_data = {}  # TODO: estrarre da import_data
        special_unlocks = check_special_achievements(stats, achievements, unlocked, current_tournament_data)

        # Raccogli achievement da sbloccare (non scrivere ancora!)
        unlocked_date = datetime.now().strftime("%Y-%m-%d")

        for ach_id in simple_unlocks:
            achievements_to_unlock.append([
                membership_padded,
                ach_id,
                unlocked_date,
                tournament_id,
                ""  # progress vuoto
            ])
            total_unlocked += 1
            print(f"  🏆 {membership_padded}: {achievements[ach_id]['emoji']} {achievements[ach_id]['name']}")

        for ach_id, progress in special_unlocks:
            achievements_to_unlock.append([
                membership_padded,
                ach_id,
                unlocked_date,
                tournament_id,
                progress
            ])
            total_unlocked += 1
            print(f"  🏆 {membership_padded}: {achievements[ach_id]['emoji']} {achievements[ach_id]['name']} ({progress})")

    # 4. BATCH WRITE - scrivi TUTTI gli achievement in una volta sola!
    if achievements_to_unlock:
        ws_player_ach = sheet.worksheet("Player_Achievements")
        ws_player_ach.append_rows(achievements_to_unlock, value_input_option='RAW')
        print(f"  ✅ {total_unlocked} achievement sbloccati!")
    else:
        print("  ✅ Nessun nuovo achievement sbloccato")

# === HELPER FUNCTIONS PER ACHIEVEMENT AVANZATI (FASE 2) ===

def check_tournament_specific_achievements(tournament_data: Dict, achievements: Dict, unlocked: Set) -> List[str]:
    """
    Check achievement basati sul singolo torneo (es. Perfect Storm, The Answer).
    Richiede dati dettagliati del torneo corrente.

    TODO: Implementare in fase 2 quando abbiamo match data completo
    """
    to_unlock = []

    # Esempio: Perfect Storm (vittoria senza sconfitte)
    # rank = tournament_data.get('rank')
    # record = tournament_data.get('record')  # W-L-D
    # if rank == 1 and 'L' component == 0:
    #     to_unlock.append('ACH_GLO_005')

    return to_unlock

def check_seasonal_achievements(sheet, membership: str, season_id: str, achievements: Dict, unlocked: Set) -> List[str]:
    """
    Check achievement stagionali (es. Opening Act, Grand Finale, Season Sweep).
    Richiede analisi della stagione completa.

    TODO: Implementare in fase 2
    """
    to_unlock = []

    return to_unlock
