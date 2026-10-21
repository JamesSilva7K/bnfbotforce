"""
Orquestrador Unificado do Sistema BNF
Inicia o Painel Web Super-Admin (Flask) e o Bot do Telegram concorrentemente.
"""

import sys
import os
import time
import threading
import logging
from datetime import datetime

# Força codificação UTF-8 para stdout/stderr no Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import WEB_HOST, WEB_PORT
import database
from app import app
from bot import create_bot_updater

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SystemRunner")

def run_web_dashboard():
    """Inicia o servidor web Flask"""
    logger.info(f"Iniciando Super-Admin Dashboard em http://{WEB_HOST}:{WEB_PORT}")
    try:
        app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Erro no servidor web: {e}")

def run_telegram_bot():
    """Inicia o bot do Telegram se o token estiver configurado"""
    token = database.get_system_setting("telegram_bot_token")
    if not token or token.strip() == "":
        logger.info("[AVISO] Token do Telegram Bot ainda nao configurado.")
        logger.info(f"[CONFIG] Acesse http://{WEB_HOST}:{WEB_PORT}/settings para cadastrar seu token do @BotFather.")
        return None

    try:
        logger.info("Conectando ao Telegram...")
        updater = create_bot_updater(token)
        if updater:
            updater.start_polling()
            logger.info("[BOT] Bot do Telegram ativo e ouvindo mensagens!")
            return updater
        else:
            logger.error("Falha ao inicializar o Bot do Telegram.")
            return None
    except Exception as e:
        logger.error(f"Erro ao iniciar o Bot do Telegram: {e}")
        return None

def main():
    print("=" * 65)
    print("[BNF DOCS 2.0] SISTEMA DE EMISSAO INTELIGENTE DE DECLARACOES")
    print("=" * 65)

    # 1. Inicializa Banco de Dados
    database.init_db()
    logger.info("Banco de Dados SQLite (WAL mode) inicializado.")

    # 2. Inicia o Servidor Web em uma thread dedicada
    web_thread = threading.Thread(target=run_web_dashboard, daemon=True)
    web_thread.start()

    # 3. Dá 1 segundo para o Flask inicializar
    time.sleep(1)
    print(f"\n[WEB] Painel Super-Admin disponivel em: http://{WEB_HOST}:{WEB_PORT}")
    print(f"[AUTH] Credenciais padrao: Usuario: 'admin' | Senha: 'admin1234'\n")

    # 4. Inicia o Bot do Telegram
    bot_updater = run_telegram_bot()

    # 5. Loop de supervisão
    try:
        while True:
            time.sleep(2)
            # Se o token não estava configurado mas foi configurado via painel web:
            if not bot_updater:
                token = database.get_system_setting("telegram_bot_token")
                if token and token.strip() != "":
                    logger.info("Novo Token do Telegram detectado no banco de dados! Iniciando bot...")
                    bot_updater = run_telegram_bot()
    except KeyboardInterrupt:
        print("\nEncerrando sistema...")
        if bot_updater:
            bot_updater.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
