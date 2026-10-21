import sys
import os
import types

# 1. Polyfill pkg_resources para APScheduler no Python 3.12 (Vercel)
try:
    import pkg_resources
except ModuleNotFoundError:
    try:
        class _MockDist:
            version = "3.10.4"
        pkg_mock = types.ModuleType("pkg_resources")
        pkg_mock.get_distribution = lambda name: _MockDist()
        pkg_mock.DistributionNotFound = type("DistributionNotFound", (Exception,), {})
        sys.modules["pkg_resources"] = pkg_mock
    except Exception:
        pass

# 2. Polyfill urllib3.contrib.appengine para python-telegram-bot v13 em runtime Vercel
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
