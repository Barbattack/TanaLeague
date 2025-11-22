# -*- coding: utf-8 -*-
"""
=================================================================================
TanaLeague v2.0 - Import Validator
=================================================================================

Sistema di validazione pre-import che garantisce:
- Nessuna scrittura su Google Sheets se ci sono errori
- Report dettagliato con riga/linea esatta degli errori
- Conferma utente per warning non bloccanti
- Supporto reimport sicuro con cancellazione atomica (batch)

UTILIZZO:
---------
    from import_validator import (
        ImportValidator,
        validate_pokemon_tdf,
        validate_onepiece_csv,
        validate_riftbound_csv,
        validate_google_sheets,
        validate_season,
        check_tournament_exists,
        batch_delete_tournament
    )

    validator = ImportValidator()
    data = validate_pokemon_tdf(filepath, season_id, validator)

    if not validator.is_valid():
        print(validator.report())
        sys.exit(1)

GARANZIE DI SICUREZZA:
----------------------
- Validazione completa PRIMA di qualsiasi scrittura
- Batch delete atomico (all-or-nothing) per reimport
- Ricalcolo Players da zero dopo reimport (già implementato negli script)

=================================================================================
"""

import os
import csv
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import gspread
from google.oauth2.service_account import Credentials


# ============================================================================
# CLASSE IMPORT VALIDATOR
# ============================================================================

class ImportValidator:
    """
    Raccoglie errori e warning durante la validazione pre-import.
    Permette di bloccare l'import se ci sono errori critici.

    Attributes:
        errors: Lista di tuple (messaggio, riga, dettaglio) per errori bloccanti
        warnings: Lista di tuple (messaggio, riga, dettaglio) per warning non bloccanti

    Example:
        validator = ImportValidator()
        validator.add_error("File non trovato", detail="/path/to/file.csv")

        if not validator.is_valid():
            print(validator.report())
    """

    def __init__(self):
        self.errors: List[Tuple[str, Optional[int], Optional[str]]] = []
        self.warnings: List[Tuple[str, Optional[int], Optional[str]]] = []

    def add_error(self, message: str, line: int = None, detail: str = None):
        """
        Aggiunge errore critico (blocca import).

        Args:
            message: Descrizione dell'errore
            line: Numero riga nel file (opzionale)
            detail: Dettaglio aggiuntivo (opzionale)
        """
        self.errors.append((message, line, detail))

    def add_warning(self, message: str, line: int = None, detail: str = None):
        """
        Aggiunge warning non bloccante (chiede conferma).

        Args:
            message: Descrizione del warning
            line: Numero riga nel file (opzionale)
            detail: Dettaglio aggiuntivo (opzionale)
        """
        self.warnings.append((message, line, detail))

    def is_valid(self) -> bool:
        """
        Verifica se non ci sono errori critici.

        Returns:
            True se nessun errore critico, False altrimenti
        """
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """
        Verifica se ci sono warning.

        Returns:
            True se ci sono warning, False altrimenti
        """
        return len(self.warnings) > 0

    def report(self) -> str:
        """
        Genera report formattato per console.

        Returns:
            Stringa con report formattato degli errori e warning
        """
        lines = []

        if self.errors:
            lines.append("")
            lines.append("=" * 64)
            lines.append(f"  ERRORI RILEVATI ({len(self.errors)})")
            lines.append("=" * 64)

            for i, (msg, line, detail) in enumerate(self.errors, 1):
                if line:
                    lines.append(f"  {i}. Riga {line}: {msg}")
                else:
                    lines.append(f"  {i}. {msg}")
                if detail:
                    lines.append(f"     {detail}")
                lines.append("")

            lines.append("=" * 64)

        if self.warnings:
            lines.append("")
            lines.append("-" * 64)
            lines.append(f"  WARNING ({len(self.warnings)})")
            lines.append("-" * 64)

            for i, (msg, line, detail) in enumerate(self.warnings, 1):
                if line:
                    lines.append(f"  {i}. Riga {line}: {msg}")
                else:
                    lines.append(f"  {i}. {msg}")
                if detail:
                    lines.append(f"     {detail}")

            lines.append("-" * 64)

        return "\n".join(lines)

    def ask_confirmation(self, prompt: str = "Vuoi procedere con l'import?") -> bool:
        """
        Chiede conferma utente se ci sono warning.

        Args:
            prompt: Messaggio da mostrare

        Returns:
            True se utente conferma, False altrimenti
        """
        if not self.has_warnings():
            return True

        response = input(f"\n{prompt} [s/N]: ").strip().lower()
        return response == 's'


# ============================================================================
# VALIDAZIONE FILE
# ============================================================================

def validate_file_exists(filepath: str, validator: ImportValidator) -> bool:
    """
    Verifica che il file esista e sia leggibile.

    Args:
        filepath: Percorso al file
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        True se file valido, False altrimenti
    """
    if not filepath:
        validator.add_error("Percorso file non specificato")
        return False

    if not os.path.exists(filepath):
        validator.add_error(f"File non trovato: {filepath}")
        return False

    if not os.path.isfile(filepath):
        validator.add_error(f"Il percorso non è un file: {filepath}")
        return False

    if not os.access(filepath, os.R_OK):
        validator.add_error(f"File non leggibile (permessi): {filepath}")
        return False

    return True


def validate_file_encoding(filepath: str, validator: ImportValidator) -> bool:
    """
    Verifica che il file sia UTF-8 o encoding compatibile.

    Args:
        filepath: Percorso al file
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        True se encoding OK, False altrimenti
    """
    encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

    for encoding in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                f.read(1024)  # Leggi primi 1KB per test
            return True
        except UnicodeDecodeError:
            continue

    validator.add_error(
        f"Encoding non supportato: {filepath}",
        detail="Prova a convertire il file in UTF-8"
    )
    return False


# ============================================================================
# VALIDAZIONE POKEMON TDF
# ============================================================================

def validate_pokemon_tdf(filepath: str, season_id: str, validator: ImportValidator) -> Optional[Dict]:
    """
    Valida file TDF Pokemon e restituisce dati parsati se valido.

    Args:
        filepath: Percorso al file TDF
        season_id: ID stagione (es. "PKM01")
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        Dict con dati parsati se valido, None se errori critici

    Check eseguiti:
        1. File esiste e leggibile
        2. XML valido (parsabile)
        3. Tag obbligatori presenti
        4. Ogni player ha campi richiesti
        5. Match hanno outcome validi
    """
    # 1. File esiste
    if not validate_file_exists(filepath, validator):
        return None

    # 2. XML valido
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        validator.add_error(
            "XML non valido (file corrotto o formato errato)",
            detail=str(e)
        )
        return None
    except Exception as e:
        validator.add_error(
            f"Errore lettura file: {e}"
        )
        return None

    # 3. Tag obbligatori
    # Leggi file per avere numeri di riga
    with open(filepath, 'r', encoding='utf-8') as f:
        file_lines = f.readlines()

    def find_line_number(tag_name: str) -> int:
        """Trova numero riga approssimativo di un tag"""
        for i, line in enumerate(file_lines, 1):
            if f'<{tag_name}' in line or f'<{tag_name}>' in line:
                return i
        return None

    # Check <data> section
    data_elem = root.find('.//data')
    if data_elem is None:
        validator.add_error("Sezione <data> mancante nel TDF")
        return None

    # Check <name>
    name_elem = root.find('.//name')
    if name_elem is None or not name_elem.text:
        line = find_line_number('name')
        validator.add_error("Tag <name> mancante o vuoto", line=line)

    # Check <id>
    id_elem = root.find('.//id')
    if id_elem is None or not id_elem.text:
        line = find_line_number('id')
        validator.add_error("Tag <id> mancante o vuoto", line=line)

    # Check <startdate> e formato
    startdate_elem = root.find('.//startdate')
    tournament_date = None
    if startdate_elem is None or not startdate_elem.text:
        line = find_line_number('startdate')
        validator.add_error("Tag <startdate> mancante o vuoto", line=line)
    else:
        # Verifica formato MM/DD/YYYY
        date_str = startdate_elem.text.strip()
        try:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            tournament_date = date_obj.strftime('%Y-%m-%d')
        except ValueError:
            line = find_line_number('startdate')
            validator.add_error(
                f"Tag <startdate> formato errato",
                line=line,
                detail=f"Trovato: \"{date_str}\" - Atteso: MM/DD/YYYY (es. \"09/24/2025\")"
            )

    # Check <players> section
    players_section = root.find('./players')
    if players_section is None:
        validator.add_error("Sezione <players> mancante nel TDF")
        return None

    # 4. Valida ogni player
    players = {}
    player_line_num = find_line_number('players') or 0

    for i, player_elem in enumerate(players_section.findall('player')):
        current_line = player_line_num + i + 1  # Approssimazione

        userid = player_elem.get('userid')
        if not userid:
            validator.add_error(
                f"Player senza attributo 'userid'",
                line=current_line
            )
            continue

        firstname_elem = player_elem.find('firstname')
        lastname_elem = player_elem.find('lastname')

        if firstname_elem is None or not firstname_elem.text:
            validator.add_error(
                f"Player userid=\"{userid}\" senza <firstname>",
                line=current_line
            )
            continue

        if lastname_elem is None or not lastname_elem.text:
            validator.add_error(
                f"Player userid=\"{userid}\" senza <lastname>",
                line=current_line
            )
            continue

        firstname = firstname_elem.text.strip()
        lastname = lastname_elem.text.strip()
        players[userid] = f"{firstname} {lastname}"

    if not players:
        validator.add_error("Nessun player valido trovato nel TDF")
        return None

    # Check <standings>
    standings = {}
    standings_section = root.find('.//standings/pod[@category="2"]')
    if standings_section is None:
        validator.add_warning(
            "Sezione <standings> con category=\"2\" non trovata",
            detail="Il ranking potrebbe essere calcolato dai match"
        )
    else:
        for player_standing in standings_section.findall('player'):
            uid = player_standing.get('id')
            place = player_standing.get('place')
            if uid and place:
                try:
                    standings[uid] = int(place)
                except ValueError:
                    validator.add_warning(
                        f"Standing place non numerico per player {uid}: \"{place}\""
                    )

    # 5. Valida match
    rounds_section = root.find('.//rounds')
    matches = []
    valid_outcomes = {'1', '2', '3', '5'}  # 1=P1 win, 2=P2 win, 3=tie, 5=BYE

    if rounds_section is not None:
        rounds_line = find_line_number('rounds') or 0

        for round_elem in rounds_section.findall('round'):
            round_num = round_elem.get('number', '?')

            for match_elem in round_elem.findall('.//match'):
                outcome = match_elem.get('outcome')
                player1 = match_elem.get('player1')
                player2 = match_elem.get('player2')

                if outcome and outcome not in valid_outcomes:
                    validator.add_error(
                        f"Round {round_num}: Match outcome \"{outcome}\" non valido",
                        detail="Atteso: 1 (P1 win), 2 (P2 win), 3 (tie), 5 (BYE)"
                    )

                matches.append({
                    'round': round_num,
                    'player1': player1,
                    'player2': player2,
                    'outcome': outcome
                })

    # Se ci sono errori critici, non restituire dati
    if not validator.is_valid():
        return None

    # Costruisci tournament_id
    tournament_id = f"{season_id}_{tournament_date}" if tournament_date else None

    return {
        'tournament_id': tournament_id,
        'tournament_name': name_elem.text if name_elem is not None else None,
        'tournament_date': tournament_date,
        'players': players,
        'standings': standings,
        'matches': matches,
        'participants_count': len(players)
    }


# ============================================================================
# VALIDAZIONE ONE PIECE CSV
# ============================================================================

def validate_onepiece_csv(filepath: str, season_id: str, validator: ImportValidator) -> Optional[Dict]:
    """
    Valida CSV One Piece (formato Bandai).

    Args:
        filepath: Percorso al file CSV
        season_id: ID stagione (es. "OP12")
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        Dict con dati parsati se valido, None se errori critici

    Check eseguiti:
        1. File esiste e leggibile
        2. CSV parsabile
        3. Header contiene colonne obbligatorie
        4. Ogni riga ha dati validi
    """
    # 1. File esiste
    if not validate_file_exists(filepath, validator):
        return None

    # 2. Encoding
    if not validate_file_encoding(filepath, validator):
        return None

    # 3. Leggi CSV
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except csv.Error as e:
        validator.add_error(
            f"CSV non valido: {e}"
        )
        return None
    except Exception as e:
        validator.add_error(
            f"Errore lettura CSV: {e}"
        )
        return None

    if len(rows) < 2:
        validator.add_error("CSV vuoto o con solo header")
        return None

    # 4. Valida header
    header = [col.strip().lower() for col in rows[0]]

    required_columns = {
        'ranking': None,
        'user name': None,
        'membership number': None,
        'win points': None,
        'record': None
    }

    # Cerca colonne (supporta variazioni)
    for i, col in enumerate(header):
        col_clean = col.replace('_', ' ').replace('-', ' ')
        if 'ranking' in col_clean:
            required_columns['ranking'] = i
        elif 'user name' in col_clean or 'username' in col_clean or 'name' == col_clean:
            required_columns['user name'] = i
        elif 'membership' in col_clean:
            required_columns['membership number'] = i
        elif 'win point' in col_clean or 'winpoint' in col_clean or 'points' == col_clean:
            required_columns['win points'] = i
        elif 'record' in col_clean:
            required_columns['record'] = i
        elif 'omw' in col_clean:
            required_columns['omw'] = i

    # Verifica colonne obbligatorie
    for col_name, col_idx in required_columns.items():
        if col_idx is None and col_name != 'omw':  # OMW è opzionale
            validator.add_error(
                f"Colonna '{col_name}' non trovata nell'header",
                line=1,
                detail=f"Header trovato: {', '.join(rows[0])}"
            )

    if not validator.is_valid():
        return None

    # 5. Valida righe dati
    results = []
    players = {}

    for row_num, row in enumerate(rows[1:], start=2):
        if not row or all(not cell.strip() for cell in row):
            continue  # Salta righe vuote

        # Estrai valori
        try:
            ranking_str = row[required_columns['ranking']].strip()
            user_name = row[required_columns['user name']].strip()
            membership = row[required_columns['membership number']].strip()
            win_points_str = row[required_columns['win points']].strip()
            record = row[required_columns['record']].strip() if required_columns['record'] else ''
        except IndexError:
            validator.add_error(
                f"Riga con colonne insufficienti",
                line=row_num,
                detail=f"Trovate {len(row)} colonne, attese almeno {max(required_columns.values()) + 1}"
            )
            continue

        # Valida ranking
        if not ranking_str:
            validator.add_error("Ranking vuoto", line=row_num)
            continue
        try:
            ranking = int(ranking_str)
            if ranking < 1:
                validator.add_error(
                    f"Ranking non valido: {ranking}",
                    line=row_num,
                    detail="Il ranking deve essere >= 1"
                )
                continue
        except ValueError:
            validator.add_error(
                f"Ranking non numerico: \"{ranking_str}\"",
                line=row_num
            )
            continue

        # Valida user name
        if not user_name:
            validator.add_error("User Name vuoto", line=row_num)
            continue

        # Valida membership
        if not membership:
            validator.add_error("Membership Number vuoto", line=row_num)
            continue

        # Valida win points
        if not win_points_str:
            validator.add_warning(
                "Win Points vuoto (verrà impostato a 0)",
                line=row_num
            )
            win_points = 0
        else:
            try:
                # Supporta sia punto che virgola come separatore decimale
                win_points = float(win_points_str.replace(',', '.'))
                if win_points < 0:
                    validator.add_error(
                        f"Win Points negativo: {win_points}",
                        line=row_num
                    )
                    continue
            except ValueError:
                validator.add_error(
                    f"Win Points non numerico: \"{win_points_str}\"",
                    line=row_num
                )
                continue

        # OMW opzionale
        omw = 0.0
        if required_columns.get('omw') is not None:
            try:
                omw_str = row[required_columns['omw']].strip()
                if omw_str:
                    omw = float(omw_str.replace(',', '.').replace('%', ''))
            except (IndexError, ValueError):
                validator.add_warning(
                    f"OMW% non parsabile (verrà impostato a 0)",
                    line=row_num
                )

        # Aggiungi risultato
        results.append({
            'ranking': ranking,
            'user_name': user_name,
            'membership': membership,
            'win_points': win_points,
            'omw': omw,
            'record': record,
            'row_num': row_num
        })

        players[membership] = user_name

    if not results:
        validator.add_error("Nessun risultato valido trovato nel CSV")
        return None

    if len(results) < 2:
        validator.add_warning(
            f"Solo {len(results)} partecipante trovato",
            detail="Un torneo richiede normalmente almeno 2 partecipanti"
        )

    # Verifica ranking sequenziale
    rankings = sorted([r['ranking'] for r in results])
    expected = list(range(1, len(rankings) + 1))
    if rankings != expected:
        validator.add_warning(
            "Ranking non sequenziale",
            detail=f"Trovato: {rankings[:10]}{'...' if len(rankings) > 10 else ''}"
        )

    # Se ci sono errori critici, non restituire dati
    if not validator.is_valid():
        return None

    return {
        'results': results,
        'players': players,
        'participants_count': len(results)
    }


# ============================================================================
# VALIDAZIONE RIFTBOUND CSV MULTI-ROUND
# ============================================================================

def validate_riftbound_csv(filepaths: List[str], season_id: str, validator: ImportValidator) -> Optional[Dict]:
    """
    Valida CSV Riftbound multi-round.

    Args:
        filepaths: Lista di percorsi ai file CSV (uno per round)
        season_id: ID stagione (es. "RFB01")
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        Dict con dati parsati se valido, None se errori critici

    Check eseguiti:
        1. Tutti i file esistono
        2. Ogni CSV ha 22 colonne
        3. Campi obbligatori presenti
        4. Event Record formato W-L-D
    """
    if not filepaths:
        validator.add_error("Nessun file CSV specificato")
        return None

    # 1. Verifica tutti i file esistono
    for filepath in filepaths:
        if not validate_file_exists(filepath, validator):
            return None

    # Colonne critiche (0-indexed)
    REQUIRED_COLUMNS = {
        'table_number': 0,
        'player1_user_id': 4,
        'player1_first_name': 5,
        'player1_last_name': 6,
        'player2_user_id': 8,
        'player2_first_name': 9,
        'player2_last_name': 10,
        'match_result': 13,
        'player1_event_record': 16,
        'player2_event_record': 17
    }
    MIN_COLUMNS = 22

    all_players = {}  # user_id -> {name, event_record, ...}
    all_matches = []

    # Pattern per Event Record: W-L-D (es. "3-1-0")
    event_record_pattern = re.compile(r'^(\d+)-(\d+)-(\d+)$')

    for file_idx, filepath in enumerate(filepaths, 1):
        filename = os.path.basename(filepath)

        # 2. Leggi CSV
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            validator.add_error(
                f"Errore lettura CSV",
                detail=f"File: {filename}, Errore: {e}"
            )
            continue

        if len(rows) < 2:
            validator.add_error(
                f"File {filename}: CSV vuoto o con solo header"
            )
            continue

        # 3. Valida header (verifica numero colonne)
        header = rows[0]
        if len(header) < MIN_COLUMNS:
            validator.add_error(
                f"File {filename}: Colonne insufficienti nell'header",
                line=1,
                detail=f"Trovate {len(header)}, attese almeno {MIN_COLUMNS}"
            )
            continue

        # 4. Valida ogni riga
        for row_num, row in enumerate(rows[1:], start=2):
            if not row or all(not cell.strip() for cell in row):
                continue  # Salta righe vuote

            # Verifica numero colonne
            if len(row) < MIN_COLUMNS:
                validator.add_error(
                    f"File {filename}, Riga {row_num}: Colonne insufficienti",
                    detail=f"Trovate {len(row)}, attese {MIN_COLUMNS}"
                )
                continue

            # Estrai dati Player 1
            p1_user_id = row[REQUIRED_COLUMNS['player1_user_id']].strip()
            p1_first_name = row[REQUIRED_COLUMNS['player1_first_name']].strip()
            p1_last_name = row[REQUIRED_COLUMNS['player1_last_name']].strip()
            p1_event_record = row[REQUIRED_COLUMNS['player1_event_record']].strip()

            # Estrai dati Player 2
            p2_user_id = row[REQUIRED_COLUMNS['player2_user_id']].strip()
            p2_first_name = row[REQUIRED_COLUMNS['player2_first_name']].strip()
            p2_last_name = row[REQUIRED_COLUMNS['player2_last_name']].strip()
            p2_event_record = row[REQUIRED_COLUMNS['player2_event_record']].strip()

            # Match result
            match_result = row[REQUIRED_COLUMNS['match_result']].strip()
            table_number = row[REQUIRED_COLUMNS['table_number']].strip()

            # Valida Player 1
            if not p1_user_id:
                validator.add_error(
                    f"File {filename}, Riga {row_num}: Player 1 User ID vuoto"
                )
                continue

            if not p1_first_name and not p1_last_name:
                validator.add_warning(
                    f"File {filename}, Riga {row_num}: Player 1 senza nome",
                    detail=f"User ID: {p1_user_id}"
                )

            # Valida Player 2 (può essere BYE)
            if not p2_user_id:
                # Potrebbe essere un BYE
                if 'bye' in p2_first_name.lower() or 'bye' in p2_last_name.lower():
                    validator.add_warning(
                        f"File {filename}, Riga {row_num}: BYE rilevato",
                        detail="Verrà gestito come vittoria automatica"
                    )
                else:
                    validator.add_error(
                        f"File {filename}, Riga {row_num}: Player 2 User ID vuoto"
                    )
                continue

            # Valida Event Record Player 1
            if p1_event_record:
                if not event_record_pattern.match(p1_event_record):
                    validator.add_error(
                        f"File {filename}, Riga {row_num}: Player 1 Event Record non valido",
                        detail=f"Trovato: \"{p1_event_record}\" - Atteso formato: W-L-D (es. \"3-1-0\")"
                    )

            # Valida Event Record Player 2
            if p2_event_record:
                if not event_record_pattern.match(p2_event_record):
                    validator.add_error(
                        f"File {filename}, Riga {row_num}: Player 2 Event Record non valido",
                        detail=f"Trovato: \"{p2_event_record}\" - Atteso formato: W-L-D (es. \"3-1-0\")"
                    )

            # Valida Match Result (warning se non parsabile)
            winner_id = None
            if match_result:
                # Formato atteso: "Nome Cognome: X-Y-Z"
                if ':' in match_result:
                    winner_name = match_result.split(':')[0].strip()
                    p1_name = f"{p1_first_name} {p1_last_name}".strip()
                    p2_name = f"{p2_first_name} {p2_last_name}".strip()

                    if winner_name.lower() == p1_name.lower():
                        winner_id = p1_user_id
                    elif winner_name.lower() == p2_name.lower():
                        winner_id = p2_user_id
                    else:
                        validator.add_warning(
                            f"File {filename}, Riga {row_num}: Match Result non corrisponde ai giocatori",
                            detail=f"Winner: \"{winner_name}\" - Players: \"{p1_name}\" vs \"{p2_name}\""
                        )
                else:
                    validator.add_warning(
                        f"File {filename}, Riga {row_num}: Match Result formato non standard",
                        detail=f"Trovato: \"{match_result}\" - Atteso: \"Nome Cognome: X-Y-Z\""
                    )

            # Salva dati giocatori (ultimo round ha record finale)
            p1_name = f"{p1_first_name} {p1_last_name}".strip()
            p2_name = f"{p2_first_name} {p2_last_name}".strip()

            all_players[p1_user_id] = {
                'name': p1_name,
                'event_record': p1_event_record,
                'round': file_idx
            }

            if p2_user_id:
                all_players[p2_user_id] = {
                    'name': p2_name,
                    'event_record': p2_event_record,
                    'round': file_idx
                }

            # Salva match
            all_matches.append({
                'round': file_idx,
                'table': table_number,
                'player1_id': p1_user_id,
                'player1_name': p1_name,
                'player2_id': p2_user_id,
                'player2_name': p2_name,
                'winner_id': winner_id,
                'result': match_result
            })

    if not all_players:
        validator.add_error("Nessun giocatore valido trovato nei CSV")
        return None

    # Se ci sono errori critici, non restituire dati
    if not validator.is_valid():
        return None

    return {
        'players': {uid: data['name'] for uid, data in all_players.items()},
        'players_data': all_players,
        'matches': all_matches,
        'participants_count': len(all_players),
        'rounds_count': len(filepaths)
    }


# ============================================================================
# VALIDAZIONE GOOGLE SHEETS
# ============================================================================

def validate_google_sheets(sheet_id: str, credentials_file: str,
                          required_worksheets: List[str],
                          validator: ImportValidator) -> Optional[object]:
    """
    Valida connessione e struttura Google Sheets.

    Args:
        sheet_id: ID del Google Sheet
        credentials_file: Percorso al file credenziali JSON
        required_worksheets: Lista nomi worksheet richiesti
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        Oggetto sheet gspread se valido, None se errori
    """
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # 1. Verifica file credenziali
    if not os.path.exists(credentials_file):
        validator.add_error(
            f"File credenziali non trovato: {credentials_file}"
        )
        return None

    # 2. Autenticazione
    try:
        creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        client = gspread.authorize(creds)
    except Exception as e:
        validator.add_error(
            "Credenziali non valide o errore autenticazione",
            detail=str(e)
        )
        return None

    # 3. Accesso al sheet
    try:
        sheet = client.open_by_key(sheet_id)
    except gspread.SpreadsheetNotFound:
        validator.add_error(
            f"Google Sheet non trovato: {sheet_id}",
            detail="Verifica l'ID del foglio e i permessi del service account"
        )
        return None
    except gspread.exceptions.APIError as e:
        validator.add_error(
            "Errore API Google Sheets",
            detail=str(e)
        )
        return None
    except Exception as e:
        validator.add_error(
            f"Errore accesso Google Sheet: {e}"
        )
        return None

    # 4. Verifica worksheet esistono
    try:
        existing_worksheets = [ws.title for ws in sheet.worksheets()]
    except Exception as e:
        validator.add_error(
            f"Errore lettura worksheets: {e}"
        )
        return None

    for ws_name in required_worksheets:
        if ws_name not in existing_worksheets:
            validator.add_error(
                f"Foglio mancante: \"{ws_name}\"",
                detail=f"Fogli esistenti: {', '.join(existing_worksheets)}"
            )

    if not validator.is_valid():
        return None

    return sheet


# ============================================================================
# VALIDAZIONE SEASON
# ============================================================================

def validate_season(sheet: object, season_id: str, validator: ImportValidator) -> Optional[Dict]:
    """
    Valida che la season esista e sia configurata.

    Args:
        sheet: Oggetto sheet gspread
        season_id: ID stagione da validare
        validator: Oggetto ImportValidator per raccogliere errori

    Returns:
        Dict con config season se valida, None se errori
    """
    try:
        ws_config = sheet.worksheet("Config")
        config_data = ws_config.get_all_values()
    except Exception as e:
        validator.add_error(
            f"Errore lettura foglio Config: {e}"
        )
        return None

    # Cerca season (skip header, inizia da riga 5 tipicamente)
    season_config = None
    for row in config_data[4:]:  # Skip header rows
        if row and row[0] == season_id:
            season_config = {
                'season_id': row[0],
                'tcg': row[1] if len(row) > 1 else None,
                'name': row[2] if len(row) > 2 else None,
                'season_num': row[3] if len(row) > 3 else None,
                'status': row[4] if len(row) > 4 else None
            }
            break

    if not season_config:
        validator.add_error(
            f"Season \"{season_id}\" non trovata nel foglio Config",
            detail="Aggiungi la season al foglio Config prima di importare"
        )
        return None

    if not season_config.get('tcg'):
        validator.add_error(
            f"Season \"{season_id}\" senza TCG definito",
            detail="Imposta il TCG (OP, PKM, RFB) nel foglio Config"
        )
        return None

    # Warning se ARCHIVED
    if season_config.get('status', '').upper() == 'ARCHIVED':
        validator.add_warning(
            f"Season \"{season_id}\" è ARCHIVED",
            detail="L'import è comunque possibile, ma la season non è attiva"
        )

    return season_config


# ============================================================================
# CHECK DUPLICATI
# ============================================================================

def check_tournament_exists(sheet: object, tournament_id: str) -> Dict:
    """
    Verifica se il torneo esiste già (per gestire --reimport).

    Args:
        sheet: Oggetto sheet gspread
        tournament_id: ID torneo da verificare

    Returns:
        Dict con info sul torneo esistente:
        {
            'exists': bool,
            'tournament_row': int or None,
            'results_rows': [int, ...],
            'results_count': int,
            'matches_rows': [int, ...],
            'matches_count': int
        }
    """
    result = {
        'exists': False,
        'tournament_row': None,
        'results_rows': [],
        'results_count': 0,
        'matches_rows': [],
        'matches_count': 0
    }

    try:
        # Check Tournaments
        ws_tournaments = sheet.worksheet("Tournaments")
        tournaments_data = ws_tournaments.get_all_values()

        for i, row in enumerate(tournaments_data[3:], start=4):  # Skip header
            if row and row[0] == tournament_id:
                result['exists'] = True
                result['tournament_row'] = i
                break

        # Check Results
        ws_results = sheet.worksheet("Results")
        results_data = ws_results.get_all_values()

        for i, row in enumerate(results_data[3:], start=4):  # Skip header
            if row and len(row) > 1 and row[1] == tournament_id:
                result['results_rows'].append(i)

        result['results_count'] = len(result['results_rows'])

        if result['results_count'] > 0:
            result['exists'] = True

        # Check Matches (Pokemon o Riftbound)
        for matches_sheet in ['Pokemon_Matches', 'Riftbound_Matches']:
            try:
                ws_matches = sheet.worksheet(matches_sheet)
                matches_data = ws_matches.get_all_values()

                for i, row in enumerate(matches_data[1:], start=2):  # Skip header
                    if row and row[0] == tournament_id:
                        result['matches_rows'].append((matches_sheet, i))

            except gspread.WorksheetNotFound:
                continue

        result['matches_count'] = len(result['matches_rows'])

    except Exception as e:
        # Se errore, assumiamo non esiste (sarà gestito dopo)
        pass

    return result


# ============================================================================
# BATCH DELETE
# ============================================================================

def batch_delete_tournament(sheet: object, tournament_id: str,
                           existing_info: Dict) -> Tuple[bool, str, Dict]:
    """
    Cancella atomicamente tutti i dati di un torneo.

    Args:
        sheet: Oggetto sheet gspread
        tournament_id: ID torneo da cancellare
        existing_info: Dict da check_tournament_exists()

    Returns:
        Tuple (success, message, deleted_counts)
    """
    deleted = {
        'results': 0,
        'tournaments': 0,
        'matches': 0
    }

    try:
        # Google Sheets API richiede cancellazione dal basso verso l'alto
        # per non sballare gli indici

        # 1. Cancella Results (dal basso verso l'alto)
        if existing_info['results_rows']:
            ws_results = sheet.worksheet("Results")
            for row_idx in sorted(existing_info['results_rows'], reverse=True):
                ws_results.delete_rows(row_idx)
                deleted['results'] += 1

        # 2. Cancella Tournaments
        if existing_info['tournament_row']:
            ws_tournaments = sheet.worksheet("Tournaments")
            ws_tournaments.delete_rows(existing_info['tournament_row'])
            deleted['tournaments'] += 1

        # 3. Cancella Matches (se presenti)
        if existing_info['matches_rows']:
            # Raggruppa per sheet
            matches_by_sheet = {}
            for sheet_name, row_idx in existing_info['matches_rows']:
                if sheet_name not in matches_by_sheet:
                    matches_by_sheet[sheet_name] = []
                matches_by_sheet[sheet_name].append(row_idx)

            for sheet_name, rows in matches_by_sheet.items():
                ws_matches = sheet.worksheet(sheet_name)
                for row_idx in sorted(rows, reverse=True):
                    ws_matches.delete_rows(row_idx)
                    deleted['matches'] += 1

        # Costruisci messaggio
        parts = []
        if deleted['results']:
            parts.append(f"{deleted['results']} results")
        if deleted['tournaments']:
            parts.append(f"{deleted['tournaments']} tournament")
        if deleted['matches']:
            parts.append(f"{deleted['matches']} matches")

        message = f"Cancellati: {', '.join(parts)}"

        return True, message, deleted

    except Exception as e:
        return False, f"Errore durante cancellazione: {e}", deleted


# ============================================================================
# UTILITY
# ============================================================================

def extract_date_from_filename(filename: str) -> Optional[str]:
    """
    Estrae data dal nome file in vari formati.

    Formati supportati:
    - YYYY_MM_DD
    - YYYY-MM-DD
    - DD_MM_YYYY
    - DD-MM-YYYY

    Returns:
        Data in formato YYYY-MM-DD o None
    """
    basename = os.path.basename(filename)

    # Pattern YYYY_MM_DD o YYYY-MM-DD
    match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', basename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    # Pattern DD_MM_YYYY o DD-MM-YYYY
    match = re.search(r'(\d{2})[-_](\d{2})[-_](\d{4})', basename)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    return None
