import os
# -*- coding: utf-8 -*-
"""
TanaLeague - Configuration Template
====================================
ISTRUZIONI:
1. Copia questo file come "config.py" nella stessa cartella
2. Modifica i valori con le tue credenziali reali
3. NON caricare mai config.py su GitHub!
"""

# ==================
# GOOGLE SHEETS
# ==================
# ID del tuo Google Sheet (lo trovi nell'URL)
# Esempio URL: https://docs.google.com/spreadsheets/d/ABC123.../edit
# L'ID è la parte ABC123...
SHEET_ID = "IL_TUO_GOOGLE_SHEET_ID_QUI"

# Percorso al file JSON delle credenziali del service account
# Su PythonAnywhere: usa path assoluto tipo "/home/tuousername/tanaleague/secrets/service_account.json"
# In locale: "secrets/service_account.json" va bene
CREDENTIALS_FILE = os.getenv("PULCI_SA_CREDENTIALS") or (
    "secrets/service_account.json" if os.path.exists("secrets/service_account.json") else "service_account_credentials.json"
)

# ==================
# ADMIN LOGIN
# ==================
# Credenziali per accesso admin (se implementato)
# IMPORTANTE: Usa una password FORTE e UNICA!
ADMIN_USER = "tuo_username"
ADMIN_PASS = "cambia_questa_password_con_una_sicura"

# ==================
# CACHE SETTINGS
# ==================
# Ogni quanti minuti refreshare la cache dal Google Sheet
CACHE_REFRESH_MINUTES = 5

# Nome del file di cache locale
CACHE_FILE = "cache_data.json"

# ==================
# APP SETTINGS
# ==================
# Chiave segreta per Flask sessions
# IMPORTANTE: Genera una chiave casuale!
# Puoi usare: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = "genera-una-chiave-casuale-qui"

# Debug mode (metti False in produzione su PythonAnywhere!)
DEBUG = False
