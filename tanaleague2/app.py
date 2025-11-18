# -*- coding: utf-8 -*-
"""
=================================================================================
TanaLeague v2.0 - Flask Web Application
=================================================================================

Webapp per gestione league TCG multi-gioco (One Piece, Pokemon, Riftbound).

Funzionalità principali:
- Homepage con link ai 3 TCG
- Classifiche stagionali con dropdown selector
- Profili giocatori con storico risultati e achievement sbloccati
- Pagina achievement con catalogo completo e unlock percentages
- Statistiche avanzate (Spotlights, Pulse, Tales, Hall of Fame)
- Sistema cache 5-min per performance Google Sheets API

Architettura:
- Flask routes servono templates Jinja2
- cache.py gestisce connessione Google Sheets + file-based cache
- stats_builder.py calcola statistiche avanzate
- achievements.py gestisce unlock automatico durante import tornei

Note:
- Support BOTH /classifica/<season_id> and /classifica?season=OP12
  per retrocompatibilità con vecchi template
=================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
from flask import Flask, render_template, redirect, url_for, jsonify, request
from cache import cache
from config import SECRET_KEY, DEBUG
from stats_builder import build_stats


# ============================================================================
# FLASK APP CONFIGURATION
# ============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

@app.context_processor
def inject_defaults():
    """
    Inietta variabili default nel contesto di tutti i template Jinja2.
    Previene crash se un template usa variabile non definita (es. default_stats_scope).
    """
    return {"default_stats_scope": "OP12"}


# ============================================================================
# HELPER FUNCTIONS - Utility generiche
# ============================================================================

# --- Conversione sicura valori da Google Sheets ---
def safe_int(value, default=0):
    """
    Converte valore in int gestendo errori.

    Previene crash quando Google Sheets restituisce valori non numerici
    (es. stringhe, date, celle vuote).

    Args:
        value: Valore da convertire
        default: Valore di ritorno se conversione fallisce (default: 0)

    Returns:
        int: Valore convertito o default

    Esempio:
        safe_int("123") → 123
        safe_int("abc") → 0
        safe_int("2025-11-13") → 0
        safe_int(None) → 0
    """
    try:
        return int(value) if value and str(value).strip() else default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """
    Converte valore in float gestendo errori.
    Analogo a safe_int() ma per numeri decimali.

    Args:
        value: Valore da convertire
        default: Valore di ritorno se conversione fallisce (default: 0.0)

    Returns:
        float: Valore convertito o default
    """
    try:
        return float(value) if value and str(value).strip() else default
    except (ValueError, TypeError):
        return default


# --- Jinja2 Filters Custom ---
@app.template_filter('format_player_name')
def format_player_name(name, tcg, membership=''):
    """
    Filtro Jinja2 per formattare nomi giocatori in base al TCG.

    Ogni TCG ha una convenzione di visualizzazione diversa:
    - **One Piece (OP)**: Nome completo "Mario Rossi"
    - **Pokemon (PKM)**: Nome + iniziale cognome "Mario R."
    - **Riftbound (RFB)**: Membership number (nickname)

    Questo filtro viene applicato automaticamente in tutti i template quando
    si usa: {{ player.name | format_player_name(player.tcg, player.membership) }}

    Args:
        name (str): Nome completo giocatore dal Google Sheet
        tcg (str): Codice TCG (OP, PKM, RFB)
        membership (str): Membership number / nickname (per RFB)

    Returns:
        str: Nome formattato secondo convenzione TCG

    Esempi:
        format_player_name("Rossi, Mario", "PKM", "") → "Mario R."
        format_player_name("Rossi Mario", "RFB", "HotelMotel") → "HotelMotel"
        format_player_name("Rossi Mario", "OP", "") → "Rossi Mario"
    """
    if not name:
        return membership or 'N/A'

    tcg_upper = (tcg or '').upper()

    if tcg_upper == 'PKM':
        # Pokemon: "Nome I." - first name + last initial
        parts = name.split()
        if len(parts) >= 2:
            # Assume format "Cognome, Nome" or "Nome Cognome"
            if ',' in name:
                # Format: "Cognome, Nome" -> "Nome C."
                surname, firstname = name.split(',', 1)
                firstname = firstname.strip()
                surname = surname.strip()
                if surname:
                    return f"{firstname} {surname[0]}."
                return firstname
            else:
                # Format: "Nome Cognome" -> "Nome C."
                firstname = parts[0]
                lastname = parts[-1]
                if lastname:
                    return f"{firstname} {lastname[0]}."
                return firstname
        return name

    elif tcg_upper == 'RFB':
        # Riftbound: Mostra il membership number (nickname)
        return membership if membership else name

    else:
        # One Piece e altri: nome completo
        return name

# ---- Safety net + endpoint di test -----------------------------------------
@app.context_processor
def inject_defaults():
    # già presente sopra: lo lascio qui identico per evitare il crash del menu
    return {"default_stats_scope": "OP12"}

@app.get("/ping")
def ping():
    return "pong", 200
# ---------------------------------------------------------------------------


# ---------------------- REFRESH ROBUSTO CACHE/STATS ------------------------
def _normalize_builder_result(res, scope):
    """
    Normalizza l'output del build_stats:
    - se res è un dict con dentro {scope: {...}} ritorna res[scope]
    - se è già "flat" lo lascia così
    - riempie i pezzi mancanti con default sicuri (così Jinja non esplode)
    """
    # estrazione del payload della stagione
    if isinstance(res, dict) and scope in res:
        payload = res[scope]
    else:
        payload = res

    if not isinstance(payload, dict):
        payload = {}

    def ensure(path_keys, default_value):
        d = payload
        for k in path_keys[:-1]:
            if k not in d or not isinstance(d.get(k), dict):
                d[k] = {}
            d = d[k]
        d.setdefault(path_keys[-1], default_value)

    # default per spotlights
    ensure(["spotlights"], {})
    for k in ["mvp", "sharpshooter", "metronome", "phoenix", "big_stage", "closer"]:
        payload["spotlights"].setdefault(k, [])

    # narrative cards
    ensure(["spot_narrative"], [])

    # pulse.kpi
    ensure(["pulse"], {})
    ensure(["pulse", "kpi"], {})
    kpi = payload["pulse"]["kpi"]
    kpi.setdefault("events_total", 0)
    kpi.setdefault("unique_players", 0)         # o "participants_unique" se preferisci
    kpi.setdefault("entries_total", 0)
    kpi.setdefault("avg_participants", 0.0)
    kpi.setdefault("top8_rate", 0.0)
    kpi.setdefault("avg_omw", 0.0)

    # pulse.series
    ensure(["pulse", "series"], {})
    payload["pulse"]["series"].setdefault("entries_per_event", [])
    payload["pulse"]["series"].setdefault("avg_points_per_event", [])

    # tales
    ensure(["tales"], {})
    for k in ["companions", "podium_rivals", "top8_mixture"]:
        payload["tales"].setdefault(k, [])

    # hall of fame
    ensure(["hof"], {})
    for k in ["highest_single_score", "biggest_crowd", "most_balanced", "most_dominated", "fastest_riser"]:
        payload["hof"].setdefault(k, None)

    return payload


def _do_refresh(scope):
    try:
        # il tuo import in alto: from stats_builder import build_stats
        # Provo prima con lista (alcune versioni vogliono ['OP12']), poi con stringa.
        try:
            raw = build_stats([scope])
        except Exception:
            raw = build_stats(scope)

        payload = _normalize_builder_result(raw, scope)

        # Se la V2 è presente, salvo in cache; se non c'è, pazienza.
        try:
            from tanaleague_v2.services.stats_service import write_stats
            write_stats(scope, payload)
        except Exception:
            pass

        return jsonify({"status": "ok", "scope": scope, "keys": list(payload.keys())})
    except Exception as e:
        # NON facciamo più saltare la WSGI: rispondiamo con JSON d'errore
        return jsonify({"status": "error", "message": str(e)}), 500


@app.get("/api/refresh")
def api_refresh_default():
    # refresh di cortesia sulla stagione standard
    return _do_refresh("OP12")


@app.get("/api/stats/refresh/<scope>")
def api_refresh_scope(scope):
    return _do_refresh(scope.strip().upper())
# ---------------------------------------------------------------------------



# ---------- Helpers (used only inside /stats for the dropdown) ----------
def _tcg_code(sid: str) -> str:
    prefix = ''.join(ch for ch in str(sid) if ch.isalpha())
    return prefix.upper()

def _is_valid_season_id(sid: str) -> bool:
    """Allow only real seasons (letters+digits, e.g. OP12) and ALL-<TCG> (e.g. ALL-OP)."""
    import re
    if not isinstance(sid, str):
        return False
    sid = sid.strip().upper()
    return bool(re.match(r'^[A-Z]{2,}\d{1,3}$', sid) or re.match(r'^ALL-[A-Z]+$', sid))

def _season_key_desc(sid: str):
    """Sort by TCG prefix then by numeric part DESC (OP12 > OP11 > OP2)."""
    if not isinstance(sid, str):
        return ('', 0)
    prefix = ''.join(ch for ch in sid if ch.isalpha()).upper()
    num_str = ''.join(ch for ch in sid if ch.isdigit())
    try:
        num = int(num_str) if num_str else 0
    except Exception:
        num = 0
    # negative for DESC
    return (prefix, -num)

# ---------- Globals for templates (KEEP original behavior for classifica) ----------
@app.context_processor
def inject_globals():
    data, err, meta = cache.get_data()
    seasons = data.get('seasons', []) if data else []
    # original logic: pick ACTIVE else first
    active = [s for s in seasons if s.get('status','').upper() == 'ACTIVE']
    default_season = (active[0]['id'] if active else (seasons[0]['id'] if seasons else 'OP12'))

    # Provide also default_all_scope to avoid template expectations
    tcg = _tcg_code(default_season) if default_season else 'OP'
    default_all_scope = f"ALL-{tcg}"

    # default stats scope = current season by default
    return dict(
        default_season=default_season,
        default_stats_scope=default_season,
        default_all_scope=default_all_scope
    )

# ============================================================================
# ROUTES - HOMEPAGE
# ============================================================================

@app.route('/')
def index():
    """
    Homepage principale con cards per i 3 TCG.

    Mostra 3 card cliccabili:
    - One Piece: Link alla stagione attiva o fallback alla prima disponibile
    - Pokemon: Link alla stagione attiva o fallback
    - Riftbound: Link alla stagione attiva o fallback

    Ogni card punta a /classifica/<season_id> della rispettiva stagione attiva.
    Le stagioni con status=ARCHIVED vengono nascoste.

    Returns:
        Template: landing.html con liste stagioni filtrate per TCG
    """
    data, err, meta = cache.get_data()
    if not data:
        return render_template('error.html', error=err or 'Cache non disponibile'), 500

    seasons = data.get('seasons', [])
    standings_by_season = data.get('standings_by_season', {})

    # Filter OP, PKM, RFB seasons (exclude ARCHIVED)
    op_seasons = [s for s in seasons if s.get('id','').startswith('OP') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']
    pkm_seasons = [s for s in seasons if s.get('id','').startswith('PKM') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']
    rfb_seasons = [s for s in seasons if s.get('id','').startswith('RFB') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']

    # Sort by season number DESC (OP12 > OP11)
    def season_num(s):
        sid = s.get('id', '')
        num = ''.join(ch for ch in sid if ch.isdigit())
        return int(num) if num else 0

    op_seasons_sorted = sorted(op_seasons, key=season_num, reverse=True)
    pkm_seasons_sorted = sorted(pkm_seasons, key=season_num, reverse=True)
    rfb_seasons_sorted = sorted(rfb_seasons, key=season_num, reverse=True)

    # Podio: ultima CLOSED
    closed_seasons = [s for s in op_seasons_sorted if s.get('status','').upper() == 'CLOSED']
    podio_season_id = closed_seasons[0]['id'] if closed_seasons else (op_seasons_sorted[0]['id'] if op_seasons_sorted else 'OP12')

    # Stats/Highlights: ultima ACTIVE, oppure ultima CLOSED
    active_seasons = [s for s in op_seasons_sorted if s.get('status','').upper() == 'ACTIVE']
    stats_season_id = active_seasons[0]['id'] if active_seasons else podio_season_id

    # Active seasons for each TCG (for homepage buttons)
    pkm_active_season_id = None
    if pkm_seasons_sorted:
        pkm_active = [s for s in pkm_seasons_sorted if s.get('status','').upper() == 'ACTIVE']
        pkm_active_season_id = pkm_active[0]['id'] if pkm_active else pkm_seasons_sorted[0]['id']

    rfb_active_season_id = None
    if rfb_seasons_sorted:
        rfb_active = [s for s in rfb_seasons_sorted if s.get('status','').upper() == 'ACTIVE']
        rfb_active_season_id = rfb_active[0]['id'] if rfb_active else rfb_seasons_sorted[0]['id']

    # Top 3 standings (from podio season)
    standings = standings_by_season.get(podio_season_id, [])[:3]

    # Stats highlights (from stats season)
    from stats_cache import get_cached
    stats_obj = get_cached(stats_season_id, 900)
    if not stats_obj:
        try:
            stats_map = build_stats([stats_season_id])
            stats_obj = stats_map.get(stats_season_id, {})
        except:
            stats_obj = {}

    # Next tournament (from stats season)
    next_tournament = None
    stats_season_meta = next((s for s in seasons if s.get('id') == stats_season_id), None)
    if stats_season_meta:
        next_tournament = stats_season_meta.get('next_tournament')

    # Season names for display
    podio_season_name = next((s.get('name','') for s in seasons if s.get('id') == podio_season_id), podio_season_id)
    stats_season_name = next((s.get('name','') for s in seasons if s.get('id') == stats_season_id), stats_season_id)
    
    return render_template(
        'landing.html',
        standings=standings,
        stats=stats_obj,
        next_tournament=next_tournament,
        podio_season_id=podio_season_id,
        stats_season_id=stats_season_id,
        podio_season_name=podio_season_name,
        stats_season_name=stats_season_name,
        pkm_active_season_id=pkm_active_season_id,
        rfb_active_season_id=rfb_active_season_id
    )


# ============================================================================
# ROUTES - PAGINA CLASSIFICHE (Lista Stagioni)
# ============================================================================

@app.route('/classifiche')
def classifiche_page():
    """
    Pagina dedicata alle classifiche - lista tutte le stagioni disponibili per TCG.

    Mostra 3 sezioni (One Piece, Pokemon, Riftbound), ognuna con cards
    per tutte le stagioni non-ARCHIVED ordinate per numero DESC.

    Ogni card linka a /classifica/<season_id> per vedere la classifica
    dettagliata della stagione.

    Le stagioni ARCHIVED sono nascoste (doppio filtro: route + template).

    Returns:
        Template: classifiche_page.html con liste stagioni per TCG
    """
    data, err, meta = cache.get_data()
    if not data:
        return render_template('error.html', error=err or 'Cache non disponibile'), 500

    seasons = data.get('seasons', [])

    # Filtra stagioni per TCG (escludi ARCHIVED)
    op_seasons = [s for s in seasons if s.get('id','').startswith('OP') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']
    pkm_seasons = [s for s in seasons if s.get('id','').startswith('PKM') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']
    rfb_seasons = [s for s in seasons if s.get('id','').startswith('RFB') and _is_valid_season_id(s.get('id')) and s.get('status','').upper() != 'ARCHIVED']

    # Sort by season number DESC
    def season_num(s):
        sid = s.get('id', '')
        num = ''.join(ch for ch in sid if ch.isdigit())
        return int(num) if num else 0

    op_seasons_sorted = sorted(op_seasons, key=season_num, reverse=True)
    pkm_seasons_sorted = sorted(pkm_seasons, key=season_num, reverse=True)
    rfb_seasons_sorted = sorted(rfb_seasons, key=season_num, reverse=True)

    return render_template(
        'classifiche_page.html',
        op_seasons=op_seasons_sorted,
        pkm_seasons=pkm_seasons_sorted,
        rfb_seasons=rfb_seasons_sorted
    )


# ============================================================================
# ROUTES - CLASSIFICA STAGIONE (Standings)
# ============================================================================

# Support BOTH /classifica and /classifica/<season_id>
@app.route('/classifica')
@app.route('/classifica/<season_id>')
def classifica(season_id=None):
    """
    Classifica dettagliata di una singola stagione.

    Mostra:
    - Info card stagione (nome, status, date tornei, vincitore ultimo torneo)
    - Tabella standings con rank, giocatore, tornei giocati, punti totali
    - Dettaglio tornei della stagione (espandibile)

    Supporta sia /classifica/<season_id> che /classifica?season=<season_id>
    per retrocompatibilità con vecchi template.

    Le stagioni ARCHIVED sono accessibili direttamente tramite URL ma non
    compaiono in dropdown/liste.

    Args:
        season_id (str, optional): ID stagione (es. OP12).
                                   Se None, usa query param ?season=

    Returns:
        Template: classifica.html con standings e info stagione
    """
    # Accept legacy query param ?season=OP12 (from old templates)
    q_season = request.args.get('season')
    if season_id is None and q_season:
        season_id = q_season

    data, err, meta = cache.get_data()
    if not data:
        return render_template('error.html', error=err or 'Cache non disponibile'), 500

    seasons = data.get('seasons', [])
    standings_by_season = data.get('standings_by_season', {})
    tournaments_by_season = data.get('tournaments_by_season', {})

    # Compute last_tournament (date + winner) for info card
    last_tournament_ctx = None
    _tlist = tournaments_by_season.get(season_id, []) if season_id else []
    def _parse_dt(s):
        from datetime import datetime
        for fmt in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d'):
            try:
                return datetime.strptime(str(s), fmt)
            except Exception:
                pass
        return None
    _best = None; _best_dt = None
    for _t in _tlist:
        _dt = _parse_dt(_t.get('date'))
        if _dt is None:
            continue
        if _best_dt is None or _dt > _best_dt:
            _best, _best_dt = _t, _dt
    if _best is None and _tlist:
        _best = _tlist[-1]
    if _best:
        last_tournament_ctx = {
            'date': _best.get('date') or '',
            'winner': _best.get('winner') or ''
        }


    # If still None, select default and redirect to canonical URL
    if season_id is None:
        active = [s for s in seasons if s.get('status','').upper() == 'ACTIVE']
        season_id = (active[0]['id'] if active else (seasons[0]['id'] if seasons else None))
        if season_id is None:
            return render_template('error.html', error='Nessuna stagione disponibile'), 500
        return redirect(url_for('classifica', season_id=season_id))

    standings = standings_by_season.get(season_id, []) or []

    # Self-healing: if standings empty, try one fetch_data() and retry once
    if len(standings) == 0:
        success, error = cache.fetch_data()
        if success:
            data, err, meta = cache.get_data()
            standings_by_season = data.get('standings_by_season', {})
            tournaments_by_season = data.get('tournaments_by_season', {})
            standings = standings_by_season.get(season_id, []) or []

    season_meta = next((s for s in seasons if s.get('id') == season_id), None)
    if not season_meta:
        return render_template('error.html', error='Stagione non trovata'), 404

    # Provide alias 'all_seasons' for template backward-compatibility
    all_seasons = seasons

    return render_template(
        'classifica.html',
        season=season_meta,
        standings=standings,
        tournaments=tournaments_by_season.get(season_id, []),
        seasons=seasons,
        all_seasons=all_seasons,
        is_stale=(meta[0] if meta else False),
        cache_age=(meta[1] if meta else None),
        last_tournament=last_tournament_ctx  # optional for template
    )


# ============================================================================
# ROUTES - STATISTICHE AVANZATE (Stats)
# ============================================================================

@app.route('/stats/<scope>')
def stats(scope):
    """
    Statistiche avanzate per stagione o all-time TCG.

    Mostra 4 categorie di statistiche:
    - **Spotlights**: Record individuali (max wins, max points, streak, etc.)
    - **Pulse**: Medie, mediane, varianza (analisi statistica)
    - **Tales**: Pattern interessanti (comeback, consistency, volatility)
    - **Hall of Fame**: Top 10 lifetime per vari indicatori

    Scope può essere:
    - Singola stagione (es. OP12) → stats solo per quella stagione
    - All-time TCG (es. ALL-OP) → stats aggregate per tutti i tornei One Piece

    Usa cache file-based (stats_cache.py) per performance.
    Cache TTL: 900s (15 min).

    Args:
        scope (str): Season ID (es. OP12) o ALL-<TCG> (es. ALL-OP)

    Returns:
        Template: stats.html con 4 categorie di statistiche
    """
    from stats_cache import get_cached, set_cached

    data, err, meta = cache.get_data()
    if not data:
        return render_template('error.html', error=err or 'Cache non disponibile'), 500

    seasons = data.get('seasons', [])

    # only "real seasons" for the dropdown
    real_seasons = [s for s in seasons if _is_valid_season_id(s.get('id'))]

    # default season for the "Classifica" button
    active = [s for s in real_seasons if s.get('status','').upper() == 'ACTIVE']
    default_season = (active[0]['id'] if active else (real_seasons[0]['id'] if real_seasons else 'OP12'))

    # Build ordered dropdown:
    season_ids = [s['id'] for s in real_seasons]
    active_id = active[0]['id'] if active else None
    others = [sid for sid in season_ids if sid != active_id]
    others_sorted = sorted(others, key=_season_key_desc)  # already DESC by numeric

    tcgs = sorted({_tcg_code(sid) for sid in season_ids})
    all_time = [f'ALL-{t}' for t in tcgs]

    if active_id:
        available_scopes = [active_id] + others_sorted + all_time
    else:
        available_scopes = others_sorted + all_time

    # File-based cache (15 min TTL)
    MAX_AGE = 900
    stats_obj = get_cached(scope, MAX_AGE)
    if stats_obj is None:
        stats_map = build_stats([scope])
        stats_obj = stats_map.get(scope)
        if not stats_obj:
            return render_template('error.html', error='Scope non valido o nessun dato'), 404
        set_cached(scope, stats_obj)

    return render_template(
        'stats.html',
        scope=scope,
        stats=stats_obj,
        default_season=default_season,
        available_scopes=available_scopes
    )

# ---------- APIs ----------
@app.route('/api/refresh')
def api_refresh():
    """Refresh della cache classifica (quella originale)."""
    success, error = cache.fetch_data()
    if success:
        return jsonify({'status': 'ok', 'message': 'Cache refreshed'})
    else:
        return jsonify({'status': 'error', 'message': error}), 500

@app.route('/api/stats/refresh/<scope>')
def api_stats_refresh(scope):
    """Invalidates and rebuilds stats cache for a scope."""
    from stats_cache import clear, set_cached
    try:
        cleared = clear(scope)
        stats_map = build_stats([scope])
        stats_obj = stats_map.get(scope)
        if not stats_obj:
            return jsonify({'status':'error','message':'Scope non valido o nessun dato'}), 404
        set_cached(scope, stats_obj)
        return jsonify({'status':'ok','cleared': cleared, 'scope': scope})
    except Exception as e:
        return jsonify({'status':'error','message': str(e)}), 500


# ============================================================================
# ROUTES - GIOCATORI (Profili e Lista)
# ============================================================================

@app.route('/players')
def players_list():
    """
    Lista tutti i giocatori registrati.

    Mostra tabella ordinata per punti totali lifetime con:
    - Membership number
    - Nome (formattato per TCG con filtro format_player_name)
    - TCG principale
    - Numero tornei giocati
    - Numero vittorie
    - Punti totali lifetime

    Ogni riga linka al profilo dettagliato /player/<membership>.

    Returns:
        Template: players.html con lista giocatori ordinata per punti DESC
    """
    from cache import cache
    try:
        sheet = cache.connect_sheet()
        ws_players = sheet.worksheet("Players")
        all_players = ws_players.get_all_values()[3:]
        
        players = []
        for row in all_players:
            if row and row[0]:
                players.append({
                    'membership': row[0],
                    'name': row[1],
                    'tcg': row[2] if len(row) > 2 else 'OP',
                    'tournaments': safe_int(row[4] if len(row) > 4 else None, 0),
                    'wins': safe_int(row[5] if len(row) > 5 else None, 0),
                    'points': safe_float(row[7] if len(row) > 7 else None, 0.0)
                })
        
        # Ordina per punti totali DESC
        players.sort(key=lambda x: x['points'], reverse=True)
        
        return render_template('players.html', players=players)
    except Exception as e:
        return render_template('error.html', error=f'Errore: {str(e)}'), 500

@app.route('/player/<membership>')
def player(membership):
    """
    Profilo dettagliato singolo giocatore.

    Mostra:
    - Card anagrafica (nome, TCG, membership, tornei/vittorie/punti lifetime)
    - Achievement sbloccati con emoji, rarity badges, punti totali
    - Storico risultati tornei (tabella con tutte le partecipazioni)
    - Grafici performance (se disponibili)

    Gli achievement vengono caricati da:
    - Achievement_Definitions (per info emoji, rarity, descrizione)
    - Player_Achievements (per achievement sbloccati da questo giocatore)

    Args:
        membership (str): Membership number giocatore (es. 0000012345)

    Returns:
        Template: player.html con profilo completo giocatore
        404: Se giocatore non trovato (no results in Results sheet)
    """
    from cache import cache
    data, err, meta = cache.get_data()
    if not data:
        return render_template('error.html', error='Cache non disponibile'), 500

    # Carica sheet per player data
    try:
        sheet = cache.connect_sheet()
        ws_results = sheet.worksheet("Results")
        all_results = ws_results.get_all_values()[3:]

        # Filtra per membership
        player_results = [r for r in all_results if r and len(r) >= 10 and r[2] == membership]

        if not player_results:
            return render_template('error.html', error='Giocatore non trovato'), 404

        # Leggi TCG dal foglio Players
        ws_players = sheet.worksheet("Players")
        players_data = ws_players.get_all_values()[3:]
        player_row = next((p for p in players_data if p and p[0] == membership), None)
        player_tcg = player_row[2] if player_row and len(player_row) > 2 else 'OP'

        # Dati base
        player_name = player_results[0][9] if player_results[0][9] else membership
        
        # Calcoli
        tournaments_played = len(player_results)
        tournament_wins = sum(1 for r in player_results if r[3] and int(r[3]) == 1)
        top8_count = sum(1 for r in player_results if r[3] and int(r[3]) <= 8)
        
        points = [float(r[8]) for r in player_results if r[8]]
        avg_points = sum(points) / len(points) if points else 0
        best_rank = min([int(r[3]) for r in player_results if r[3]], default=999)
        
        # Win Rate (assumendo 4 round medi)
        total_wins = sum([float(r[4])/3 for r in player_results if r[4]])
        win_rate = (total_wins / (tournaments_played * 4) * 100) if tournaments_played > 0 else 0
        
        # Top8 Rate
        top8_rate = (top8_count / tournaments_played * 100) if tournaments_played > 0 else 0
        
        # Trend (ultimi 2 vs precedenti)
        if len(points) >= 3:
            recent = sum(points[-2:]) / 2
            older = sum(points[:-2]) / len(points[:-2])
            trend = ((recent - older) / older * 100) if older > 0 else 0
        else:
            trend = 0
        
        # First seen
        dates = [r[1].split('_')[1] if '_' in r[1] else '' for r in player_results if r[1]]
        first_seen = min(dates) if dates else 'N/A'
        
        # Storico tornei (ultimi 10)
        history = []
        for r in player_results[-10:]:
            history.append({
                'date': r[1].split('_')[1] if '_' in r[1] else '',
                'season': r[1].split('_')[0] if '_' in r[1] else '',
                'rank': int(r[3]) if r[3] else 999,
                'points': float(r[8]) if r[8] else 0,
                'record': f"{int(float(r[4])/3) if r[4] else 0}-{int(float(r[3] or 0))}" if r[3] and r[4] else 'N/A'
            })
        history.reverse()
        
        # Chart data (ultimi 10)
        chart_labels = [h['date'] for h in history[::-1]]
        chart_data = [h['points'] for h in history[::-1]]

        # Achievement data
        achievements_unlocked = []
        achievement_points = 0
        try:
            ws_achievements = sheet.worksheet("Achievement_Definitions")
            achievement_defs = {}
            for row in ws_achievements.get_all_values()[4:]:
                if row and row[0]:
                    achievement_defs[row[0]] = {
                        'name': row[1],
                        'description': row[2],
                        'category': row[3],
                        'rarity': row[4],
                        'emoji': row[5],
                        'points': int(row[6]) if row[6] else 0
                    }

            ws_player_ach = sheet.worksheet("Player_Achievements")
            for row in ws_player_ach.get_all_values()[4:]:
                if row and row[0] == membership:
                    ach_id = row[1]
                    if ach_id in achievement_defs:
                        ach_info = achievement_defs[ach_id]
                        achievements_unlocked.append({
                            'id': ach_id,
                            'name': ach_info['name'],
                            'description': ach_info['description'],
                            'category': ach_info['category'],
                            'rarity': ach_info['rarity'],
                            'emoji': ach_info['emoji'],
                            'points': ach_info['points'],
                            'unlocked_date': row[2] if len(row) > 2 else ''
                        })
                        achievement_points += ach_info['points']
        except Exception as e:
            print(f"Achievement load error: {e}")
            # Se achievement non esistono ancora, continua senza

        player_data = {
            'membership': membership,
            'name': player_name,
            'tcg': player_tcg,
            'first_seen': first_seen,
            'tournaments_played': tournaments_played,
            'tournament_wins': tournament_wins,
            'top8_count': top8_count,
            'avg_points': round(avg_points, 1),
            'best_rank': best_rank,
            'win_rate': round(win_rate, 1),
            'top8_rate': round(top8_rate, 1),
            'trend': round(trend, 1),
            'history': history,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
            'achievements': achievements_unlocked,
            'achievement_points': achievement_points
        }
        
        return render_template('player.html', player=player_data)
        
    except Exception as e:
        return render_template('error.html', error=f'Errore caricamento dati: {str(e)}'), 500


# ============================================================================
# ROUTES - ACHIEVEMENT SYSTEM
# ============================================================================

@app.route('/achievements')
def achievements():
    """
    Pagina catalogo achievement completo.

    Mostra tutti i 40+ achievement disponibili organizzati per categoria:
    - Glory (vittorie e trionfi)
    - Giant Slayer (battere i migliori)
    - Consistency (serie positive)
    - Legacy (milestone lifetime)
    - Wildcards (achievement bizzarri)
    - Seasonal (performance stagionali)
    - Heartbreak (sfortune e quasi vittorie)

    Per ogni achievement visualizza:
    - Emoji + Nome
    - Descrizione unlock condition
    - Rarity badge (Common → Legendary)
    - Punti assegnati
    - Unlock percentage (quanti giocatori l'hanno sbloccato)
    - Progress bar visuale

    I dati vengono caricati da:
    - Achievement_Definitions (40 achievement con meta)
    - Player_Achievements (unlock count per calcolare %)

    Returns:
        Template: achievements.html con catalogo completo
    """
    from cache import cache
    try:
        sheet = cache.connect_sheet()

        # Carica achievement definitions
        ws_achievements = sheet.worksheet("Achievement_Definitions")
        achievement_rows = ws_achievements.get_all_values()[4:]

        achievements_by_category = {}
        total_achievements = 0
        total_points = 0

        for row in achievement_rows:
            if not row or not row[0]:
                continue

            category = row[3] if len(row) > 3 else 'Other'
            if category not in achievements_by_category:
                achievements_by_category[category] = []

            ach = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'category': category,
                'rarity': row[4] if len(row) > 4 else 'Common',
                'emoji': row[5] if len(row) > 5 else '🏆',
                'points': int(row[6]) if len(row) > 6 and row[6] else 0
            }

            achievements_by_category[category].append(ach)
            total_achievements += 1
            total_points += ach['points']

        # Calcola % di unlock per ogni achievement
        ws_player_ach = sheet.worksheet("Player_Achievements")
        player_ach_rows = ws_player_ach.get_all_values()[4:]

        unlock_counts = {}
        for row in player_ach_rows:
            if row and row[1]:
                ach_id = row[1]
                unlock_counts[ach_id] = unlock_counts.get(ach_id, 0) + 1

        # Conta giocatori totali
        ws_players = sheet.worksheet("Players")
        total_players = len([r for r in ws_players.get_all_values()[3:] if r and r[0]])

        # Aggiungi % unlock agli achievement
        for category in achievements_by_category:
            for ach in achievements_by_category[category]:
                unlocks = unlock_counts.get(ach['id'], 0)
                ach['unlock_count'] = unlocks
                ach['unlock_percentage'] = (unlocks / total_players * 100) if total_players > 0 else 0

        # Ordina categorie per priorità
        category_order = ['Glory', 'Giant Slayer', 'Consistency', 'Legacy', 'Wildcards', 'Seasonal', 'Heartbreak']
        ordered_categories = []
        for cat in category_order:
            if cat in achievements_by_category:
                ordered_categories.append((cat, achievements_by_category[cat]))
        # Aggiungi eventuali categorie rimanenti
        for cat, achs in achievements_by_category.items():
            if cat not in category_order:
                ordered_categories.append((cat, achs))

        return render_template('achievements.html',
                               achievements_by_category=ordered_categories,
                               total_achievements=total_achievements,
                               total_points=total_points,
                               total_players=total_players)

    except Exception as e:
        return render_template('error.html', error=f'Errore caricamento achievement: {str(e)}'), 500

# ---------- Errors ----------
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Pagina non trovata'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Errore del server'), 500

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)