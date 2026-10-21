import sys
import os
import types

# Polyfill de compatibilidade para python-telegram-bot v13 com urllib3 moderno em runtime Vercel
try:
    import urllib3.contrib.appengine
except ModuleNotFoundError:
    try:
        import urllib3.contrib
        appengine_mock = types.ModuleType("appengine")
        appengine_mock.is_appengine_sandbox = lambda: False
        appengine_mock.is_local_development_server = lambda: False
        appengine_mock.AppEnginePlatformWarning = type("AppEnginePlatformWarning", (Warning,), {})
        urllib3.contrib.appengine = appengine_mock
        sys.modules["urllib3.contrib.appengine"] = appengine_mock
    except Exception:
        pass

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
