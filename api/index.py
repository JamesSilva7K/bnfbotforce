import sys
import os

# Garante que o diretório raiz do projeto esteja no sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
import database

# Garante a inicialização das tabelas em ambiente serverless
try:
    database.init_db()
except Exception:
    pass

# Exporta o WSGI app para o runtime Python da Vercel
app = app
