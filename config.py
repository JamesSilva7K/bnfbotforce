"""
Configurações Globais do Sistema de Emissão de Documentos e Bot Telegram
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Detecção de Ambiente Serverless (Vercel)
IS_VERCEL = bool(os.environ.get("VERCEL"))

if IS_VERCEL:
    STORAGE_DIR = Path("/tmp/storage")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copia o banco de dados inicial e avatares para /tmp se ainda não existirem
    src_db = BASE_DIR / "storage" / "system.db"
    dst_db = STORAGE_DIR / "system.db"
    if src_db.exists() and not dst_db.exists():
        import shutil
        shutil.copy2(src_db, dst_db)

    src_avatars = BASE_DIR / "storage" / "avatars"
    dst_avatars = STORAGE_DIR / "avatars"
    if src_avatars.exists() and not dst_avatars.exists():
        import shutil
        shutil.copytree(src_avatars, dst_avatars, dirs_exist_ok=True)
else:
    STORAGE_DIR = BASE_DIR / "storage"

# Diretórios de Armazenamento
GENERATED_PDFS_DIR = STORAGE_DIR / "generated_pdfs"
PREVIEWS_DIR = STORAGE_DIR / "previews"
ENCRYPTED_DIR = STORAGE_DIR / "encrypted"
AVATARS_DIR = STORAGE_DIR / "avatars"
DB_PATH = STORAGE_DIR / "system.db"
FONTS_DIR = BASE_DIR / "storage" / "fonts"

# Assegura que todos os diretórios existem
for d in [STORAGE_DIR, GENERATED_PDFS_DIR, PREVIEWS_DIR, ENCRYPTED_DIR, AVATARS_DIR, FONTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Template matriz oficial
TEMPLATE_PDF_PATH = BASE_DIR / "Documentos" / "declaração tuzinho.pdf"

# Configurações de Segurança e Dashboard
SECRET_KEY = os.getenv("SECRET_KEY", "bnf_super_admin_secret_key_2026_x89a!")
DEFAULT_ADMIN_USER = os.getenv("SUPER_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("SUPER_ADMIN_PASS", "admin1234")

# Token do Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8368660342:AAEaL2LjymcQsX-nn3yfj1WinaPdbk5Ocig")

# Configurações do Servidor Web
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")

