#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_achievements.py - Achievement System Setup
=================================================

COSA FA:
- Crea 2 nuovi worksheet nel Google Sheet esistente:
  1. Achievement_Definitions (definizioni achievement)
  2. Player_Achievements (achievement sbloccati dai giocatori)

SICUREZZA:
- NON tocca worksheet esistenti (Results, Players, Config, etc.)
- Controlla se i worksheet esistono già prima di crearli
- Chiede conferma prima di sovrascrivere

UTILIZZO:
    python setup_achievements.py
"""

import gspread
from google.oauth2.service_account import Credentials

# CONFIG (stesse credenziali degli import scripts)
SHEET_ID = "19ZF35DTmgZG8v1GfzKE5JmMUTXLo300vuw_AdrgQPFE"
CREDENTIALS_FILE = "/home/latanadellepulci/tanaleague2/service_account_credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def connect_sheet():
    """Connette al Google Sheet"""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def get_achievement_data():
    """
    Restituisce lista di achievement da inserire in Achievement_Definitions.

    Formato: [achievement_id, name, description, category, rarity, emoji, points, requirement_type, requirement_value]
    """
    achievements = [
        # === GLORY - Momenti epici di vittoria ===
        ["ACH_GLO_001", "First Blood", "Vinci il tuo primo torneo", "Glory", "Uncommon", "🎬", 25, "tournament_wins", 1],
        ["ACH_GLO_002", "Podium Climber", "Raggiungi 3 top8", "Glory", "Uncommon", "🎯", 25, "top8_count", 3],
        ["ACH_GLO_003", "King of the Hill", "Vinci un torneo mentre sei rank #1 della stagione", "Glory", "Rare", "👑", 50, "special", "win_as_rank1"],
        ["ACH_GLO_004", "Phoenix Rising", "Vinci un torneo dopo essere stato ultimo nel precedente", "Glory", "Rare", "🔥", 50, "special", "comeback_win"],
        ["ACH_GLO_005", "Perfect Storm", "Vinci un torneo senza sconfitte (4-0 o 5-0)", "Glory", "Rare", "⚡", 50, "special", "perfect_win"],
        ["ACH_GLO_006", "Dynasty Builder", "Vinci 5 tornei totali", "Glory", "Legendary", "💎", 250, "tournament_wins", 5],
        ["ACH_GLO_007", "Undefeated Season", "Completa una stagione intera senza sconfitte", "Glory", "Legendary", "🌟", 250, "special", "season_undefeated"],

        # === GIANT SLAYER - Upset e rivalità ===
        ["ACH_GIA_001", "Lucky Shot", "Batti un giocatore rankato 5+ posizioni sopra di te", "Giant Slayer", "Common", "🎲", 10, "special", "upset_5plus"],
        ["ACH_GIA_002", "Dragonslayer", "Batti il rank #1 della stagione in uno scontro diretto", "Giant Slayer", "Rare", "🐉", 50, "special", "beat_rank1"],
        ["ACH_GIA_003", "Giant Killer", "Batti il vincitore della stagione precedente", "Giant Slayer", "Rare", "👹", 50, "special", "beat_prev_champ"],
        ["ACH_GIA_004", "Gatekeeper", "Impedisci a 3+ giocatori di entrare in top8 battendoli nell'ultimo round", "Giant Slayer", "Rare", "🗡️", 50, "special", "gatekeeper"],
        ["ACH_GIA_005", "Upset Artist", "Vinci un torneo partendo da seed bottom 50%", "Giant Slayer", "Rare", "🎭", 50, "special", "bottom_seed_win"],
        ["ACH_GIA_006", "Kingslayer", "Batti tutti i top3 della stagione in una singola stagione", "Giant Slayer", "Legendary", "👿", 250, "special", "beat_all_top3"],

        # === CONSISTENCY - Streak e longevità ===
        ["ACH_CON_001", "Back to Back", "Ottieni 2 top8 consecutivi", "Consistency", "Uncommon", "🔄", 25, "special", "streak_top8_2"],
        ["ACH_CON_002", "Regular", "Partecipa a 5 tornei in una stagione", "Consistency", "Common", "📅", 10, "special", "season_5tournaments"],
        ["ACH_CON_003", "Hot Streak", "Ottieni 4 top8 consecutivi", "Consistency", "Rare", "⚡", 50, "special", "streak_top8_4"],
        ["ACH_CON_004", "Iron Wall", "Finisci 5 tornei consecutivi sempre in top50%", "Consistency", "Rare", "🛡️", 50, "special", "streak_top50_5"],
        ["ACH_CON_005", "Sharpshooter", "Piazza 3 volte con lo STESSO piazzamento", "Consistency", "Rare", "🎯", 50, "special", "same_rank_3x"],
        ["ACH_CON_006", "Season Warrior", "100% partecipazione in una stagione (8+ tornei)", "Consistency", "Rare", "🏛️", 50, "special", "season_full_attendance"],
        ["ACH_CON_007", "Unstoppable Force", "Ottieni 6 top8 consecutivi", "Consistency", "Legendary", "🌊", 250, "special", "streak_top8_6"],
        ["ACH_CON_008", "The Old Guard", "2 anni di partecipazione continuativa", "Consistency", "Legendary", "⏰", 250, "special", "veteran_2years"],

        # === HEARTBREAK - Sconfitte eroiche (ironici ma affettuosi) ===
        ["ACH_HEA_001", "Rookie Struggles", "Completa i tuoi primi 3 tornei totalizzando massimo 3 vittorie", "Heartbreak", "Common", "🎬", 10, "special", "rookie_struggles"],
        ["ACH_HEA_002", "Participation Trophy", "Finisci ultimo in un torneo da 8+ giocatori", "Heartbreak", "Common", "😅", 10, "special", "last_place"],
        ["ACH_HEA_003", "So Close, Yet So Far", "Piazza 9° per 3 volte (sempre fuori top8)", "Heartbreak", "Uncommon", "😢", 25, "special", "rank9_3x"],
        ["ACH_HEA_004", "Forever Second", "Piazza 2° per 3 volte senza mai vincere", "Heartbreak", "Rare", "🥈", 50, "special", "second_3x_no_wins"],
        ["ACH_HEA_005", "Storm Cloud", "Partecipa a 10+ tornei senza mai fare top8", "Heartbreak", "Epic", "🌧️", 100, "special", "10tournaments_no_top8"],

        # === WILDCARDS - Easter egg e pattern creativi ===
        ["ACH_WIL_001", "The Answer", "Ottieni ESATTAMENTE 42 punti in un torneo", "Wildcards", "Epic", "🎯", 100, "special", "points_42"],
        ["ACH_WIL_002", "Perfectly Balanced", "Finisci 2-2 in un torneo da 4+ round", "Wildcards", "Common", "⚖️", 10, "special", "record_2-2"],
        ["ACH_WIL_003", "Lucky Seven", "Piazza esattamente 7° in un torneo", "Wildcards", "Uncommon", "🎰", 25, "special", "rank_7"],
        ["ACH_WIL_004", "Triple Threat", "Piazza 3° per 3 volte", "Wildcards", "Rare", "🔢", 50, "special", "rank3_3x"],

        # === LEGACY - Cross-TCG e milestone ===
        ["ACH_LEG_001", "Debutto", "Partecipa al tuo primo torneo", "Legacy", "Common", "🎬", 10, "tournaments_played", 1],
        ["ACH_LEG_002", "Veteran", "Completa 10 tornei", "Legacy", "Uncommon", "🗓️", 25, "tournaments_played", 10],
        ["ACH_LEG_003", "Multi-Format Warrior", "Gioca almeno 3 tornei in 2 TCG diversi", "Legacy", "Rare", "🌈", 50, "special", "multi_tcg_3+"],
        ["ACH_LEG_004", "TCG Master", "Ottieni 2 top8 in almeno 2 TCG diversi", "Legacy", "Rare", "🎯", 50, "special", "top8_2tcg"],
        ["ACH_LEG_005", "Gladiator", "Completa 25 tornei", "Legacy", "Rare", "⚔️", 50, "tournaments_played", 25],
        ["ACH_LEG_006", "Hat Trick", "Vinci 3 tornei totali", "Legacy", "Rare", "🏆", 50, "tournament_wins", 3],
        ["ACH_LEG_007", "Hall of Famer", "Completa 50 tornei", "Legacy", "Legendary", "🏛️", 250, "tournaments_played", 50],
        ["ACH_LEG_008", "Triple Crown", "Vinci almeno 1 torneo in TUTTI e 3 i TCG", "Legacy", "Legendary", "👑", 250, "special", "win_all_tcg"],

        # === SEASONAL - Eventi time-limited ===
        ["ACH_SEA_001", "Opening Act", "Vinci il PRIMO torneo di una nuova stagione", "Seasonal", "Rare", "🎉", 50, "special", "win_season_first"],
        ["ACH_SEA_002", "Grand Finale", "Vinci l'ULTIMO torneo di una stagione", "Seasonal", "Rare", "🎭", 50, "special", "win_season_last"],
        ["ACH_SEA_003", "Season Sweep", "Vinci almeno 3 tornei in una singola stagione", "Seasonal", "Legendary", "👑", 250, "special", "season_3wins"],
    ]

    return achievements

def create_achievement_definitions(sheet):
    """Crea e popola il worksheet Achievement_Definitions"""

    # Controlla se esiste già
    try:
        ws = sheet.worksheet("Achievement_Definitions")
        print("⚠️  Achievement_Definitions già esistente!")
        resp = input("Vuoi sovrascriverlo? (y/n): ")
        if resp.lower() != 'y':
            print("❌ Operazione annullata.")
            return False
        # Cancella contenuto esistente
        ws.clear()
        print("🗑️  Contenuto precedente cancellato")
    except gspread.exceptions.WorksheetNotFound:
        # Crea nuovo worksheet
        ws = sheet.add_worksheet(title="Achievement_Definitions", rows=100, cols=10)
        print("✅ Worksheet Achievement_Definitions creato")

    # Header row (riga 1-3: titolo + spiegazione)
    header_data = [
        ["ACHIEVEMENT DEFINITIONS", "", "", "", "", "", "", "", ""],
        ["Lista completa degli achievement disponibili nel sistema TanaLeague", "", "", "", "", "", "", "", ""],
        [""],
        ["achievement_id", "name", "description", "category", "rarity", "emoji", "points", "requirement_type", "requirement_value"]
    ]

    # Popola achievement
    achievement_data = get_achievement_data()

    # Combina header + data
    all_data = header_data + achievement_data

    # Scrivi tutto in batch
    ws.update(values=all_data, range_name=f"A1:I{len(all_data)}")

    # Formattazione header (bold)
    ws.format("A1:I1", {"textFormat": {"bold": True, "fontSize": 14}})
    ws.format("A4:I4", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})

    print(f"✅ {len(achievement_data)} achievement inseriti in Achievement_Definitions")
    return True

def create_player_achievements(sheet):
    """Crea il worksheet Player_Achievements (vuoto, solo header)"""

    # Controlla se esiste già
    try:
        ws = sheet.worksheet("Player_Achievements")
        print("⚠️  Player_Achievements già esistente!")
        resp = input("Vuoi sovrascriverlo? (y/n): ")
        if resp.lower() != 'y':
            print("❌ Operazione annullata.")
            return False
        # Cancella contenuto esistente
        ws.clear()
        print("🗑️  Contenuto precedente cancellato")
    except gspread.exceptions.WorksheetNotFound:
        # Crea nuovo worksheet
        ws = sheet.add_worksheet(title="Player_Achievements", rows=1000, cols=6)
        print("✅ Worksheet Player_Achievements creato")

    # Header row
    header_data = [
        ["PLAYER ACHIEVEMENTS", "", "", "", ""],
        ["Achievement sbloccati dai giocatori - Popolato automaticamente dagli import scripts", "", "", "", ""],
        [""],
        ["membership", "achievement_id", "unlocked_date", "tournament_id", "progress"]
    ]

    ws.update(values=header_data, range_name="A1:E4")

    # Formattazione header
    ws.format("A1:E1", {"textFormat": {"bold": True, "fontSize": 14}})
    ws.format("A4:E4", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})

    print("✅ Player_Achievements creato (vuoto, pronto per gli unlock)")
    return True

def main():
    print("=" * 60)
    print("🎮 SETUP ACHIEVEMENT SYSTEM - TanaLeague")
    print("=" * 60)
    print()
    print("Questo script creerà 2 nuovi worksheet nel Google Sheet:")
    print("  1. Achievement_Definitions (40 achievement)")
    print("  2. Player_Achievements (vuoto)")
    print()
    print("⚠️  NON toccherà i worksheet esistenti (Results, Players, etc.)")
    print()

    resp = input("Procedere? (y/n): ")
    if resp.lower() != 'y':
        print("❌ Operazione annullata.")
        return

    print("\n🔗 Connessione a Google Sheet...")
    try:
        sheet = connect_sheet()
        print(f"✅ Connesso a: {sheet.title}")
    except Exception as e:
        print(f"❌ Errore connessione: {e}")
        return

    print("\n📋 Creazione Achievement_Definitions...")
    if not create_achievement_definitions(sheet):
        return

    print("\n📋 Creazione Player_Achievements...")
    if not create_player_achievements(sheet):
        return

    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETATO!")
    print("=" * 60)
    print("\nWorksheet creati:")
    print("  ✅ Achievement_Definitions (40 achievement)")
    print("  ✅ Player_Achievements (pronto per unlock)")
    print("\nProssimi passi:")
    print("  1. Verifica i worksheet su Google Sheets")
    print("  2. Integra achievements.py negli import scripts")
    print("  3. Aggiorna webapp per visualizzare achievement")
    print()

if __name__ == "__main__":
    main()
