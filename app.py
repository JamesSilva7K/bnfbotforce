"""
Painel Super-Admin e Servidor Web Flask
Interface moderna, responsiva, com métricas em tempo real, gestão de administradores,
auditoria de documentos e download seguro.
"""

import os
import sys
import types
import hashlib
import functools
from datetime import datetime

# Polyfill de compatibilidade urllib3.contrib.appengine para python-telegram-bot v13 na Vercel
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
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    send_file,
    send_from_directory,
    abort,
    Response
)

from config import (
    SECRET_KEY,
    STORAGE_DIR,
    GENERATED_PDFS_DIR,
    PREVIEWS_DIR,
    WEB_HOST,
    WEB_PORT,
    DEBUG,
    DEFAULT_ADMIN_USER,
    DEFAULT_ADMIN_PASS
)
import database
from pdf_engine import PDFEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
app.secret_key = SECRET_KEY

@app.route('/static/<path:filename>')
def serve_custom_static(filename):
    """Garante entrega de arquivos estáticos em ambientes Serverless como Vercel"""
    return send_from_directory(STATIC_DIR, filename)

pdf_engine = PDFEngine()

@app.context_processor
def inject_global_admin():
    """Injeta a conta mestre oficial sincronizada para renderização em todos os templates"""
    admin = database.get_admin_by_telegram_id(8932547795)
    if not admin:
        admins = database.list_all_admins()
        admin = admins[0] if admins else {
            "telegram_id": 8932547795,
            "full_name": "NG7Kz",
            "username": "NG7Ks",
            "role": "super_admin"
        }
    return dict(master_admin=admin)

# --- Decorador de Autenticação do Super-Admin ---

def super_admin_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view

# --- Rotas de Autenticação ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        stored_user = database.get_system_setting("super_admin_user", DEFAULT_ADMIN_USER)
        stored_pass_hash = database.get_system_setting("super_admin_pass", "")

        env_user = os.getenv("SUPER_ADMIN_USER", DEFAULT_ADMIN_USER).strip()
        env_pass = os.getenv("SUPER_ADMIN_PASS", DEFAULT_ADMIN_PASS).strip()

        input_hash = hashlib.sha256(password.encode()).hexdigest()

        # Aceita autenticação tanto pelas variáveis de ambiente configuradas na Vercel quanto pela base local
        is_env_match = (username.lower() == env_user.lower() and password == env_pass)
        is_db_match = (username.lower() == stored_user.lower() and input_hash == stored_pass_hash)

        if is_env_match or is_db_match:
            session["logged_in"] = True
            session["admin_user"] = username
            session["login_time"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            database.log_audit_action(
                actor=f"Super-Admin ({username})",
                action="LOGIN_PAINEL",
                details="Acesso efetuado com sucesso ao painel web",
                ip_address=request.remote_addr or "127.0.0.1"
            )

            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        else:
            database.log_audit_action(
                actor=f"Tentativa ({username})",
                action="LOGIN_FALHA",
                details="Credenciais incorretas informadas",
                ip_address=request.remote_addr or "127.0.0.1"
            )
            flash("Usuário ou senha incorretos.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    user = session.get("admin_user", "Super-Admin")
    database.log_audit_action(
        actor=user,
        action="LOGOUT",
        details="Sessão encerrada voluntariamente",
        ip_address=request.remote_addr or "127.0.0.1"
    )
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for("login"))

# --- Rotas Principais do Painel ---

@app.route("/")
@super_admin_required
def dashboard():
    metrics = database.get_dashboard_metrics()
    recent_docs = database.list_documents(limit=10)
    recent_logs = database.list_recent_audit_logs(limit=8)
    admins = database.list_all_admins()
    
    return render_template(
        "dashboard.html",
        metrics=metrics,
        recent_docs=recent_docs,
        recent_logs=recent_logs,
        admins=admins
    )

@app.route("/admins")
@super_admin_required
def admins_page():
    admins = database.list_all_admins()
    return render_template("admins.html", admins=admins)

@app.route("/documents")
@super_admin_required
def documents_page():
    search = request.args.get("q", "").strip()
    admin_id_arg = request.args.get("admin_id", "").strip()
    admin_id = int(admin_id_arg) if admin_id_arg.isdigit() else None
    
    page = int(request.args.get("p", 1))
    per_page = 20
    offset = (page - 1) * per_page

    total_count = database.get_documents_count(search=search if search else None, admin_id=admin_id)
    docs = database.list_documents(limit=per_page, offset=offset, search=search if search else None, admin_id=admin_id)
    admins = database.list_all_admins()

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return render_template(
        "documents.html",
        documents=docs,
        total_count=total_count,
        current_page=page,
        total_pages=total_pages,
        search=search,
        selected_admin=admin_id,
        admins=admins
    )

@app.route("/generate", methods=["GET", "POST"])
@super_admin_required
def web_generate():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        rg = request.form.get("rg", "").strip()
        cpf = request.form.get("cpf", "").strip()

        if not nome or not cpf or not rg:
            flash("Preencha todos os campos obrigatórios (Nome, RG e CPF).", "warning")
            return render_template("generate.html", nome=nome, rg=rg, cpf=cpf)

        try:
            # Formata RG e CPF com inteligência algorítmica
            rg_formatted = PDFEngine.format_rg(rg)
            cpf_formatted = PDFEngine.format_cpf(cpf)

            # Gera a declaração alterando estritamente Nome, RG e CPF
            pdf_path, preview_path = pdf_engine.generate_declaration(
                nome=nome,
                rg=rg_formatted,
                cpf=cpf_formatted
            )

            filename = os.path.basename(pdf_path)

            doc_record = database.register_document(
                admin_telegram_id=None,
                admin_name="Super-Admin (Painel Web)",
                lead_name=nome.upper(),
                lead_rg=rg_formatted,
                lead_cpf=cpf_formatted,
                data_emissao=datetime.now().strftime("%d/%m/%Y"),
                pdf_filename=filename,
                pdf_path=pdf_path,
                preview_path=preview_path
            )

            flash(f"Declaração emitida com sucesso para {nome.upper()}!", "success")
            return redirect(url_for("view_document_detail", doc_uuid=doc_record["doc_uuid"]))

        except Exception as e:
            flash(f"Erro ao processar o documento: {e}", "danger")

    return render_template("generate.html")

@app.route("/document/<doc_uuid>")
@super_admin_required
def view_document_detail(doc_uuid):
    doc = database.get_document_by_uuid(doc_uuid)
    if not doc:
        abort(404)
    return render_template("document_detail.html", doc=doc)

@app.route("/settings", methods=["GET", "POST"])
@super_admin_required
def settings_page():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_bot_token":
            bot_token = request.form.get("bot_token", "").strip()
            database.set_system_setting("telegram_bot_token", bot_token)
            database.log_audit_action(
                actor=session.get("admin_user", "Super-Admin"),
                action="CONFIG_BOT_TOKEN",
                details="Token do Telegram Bot atualizado pelo Super-Admin",
                ip_address=request.remote_addr or "127.0.0.1"
            )
            flash("Token do Telegram Bot salvo com sucesso!", "success")

        elif action == "change_password":
            current_pass = request.form.get("current_pass", "").strip()
            new_pass = request.form.get("new_pass", "").strip()
            confirm_pass = request.form.get("confirm_pass", "").strip()

            stored_hash = database.get_system_setting("super_admin_pass")
            input_curr_hash = hashlib.sha256(current_pass.encode()).hexdigest()

            if input_curr_hash != stored_hash:
                flash("Senha atual incorreta.", "danger")
            elif len(new_pass) < 6:
                flash("A nova senha deve possuir no mínimo 6 caracteres.", "warning")
            elif new_pass != confirm_pass:
                flash("A confirmação de senha não confere.", "warning")
            else:
                new_hash = hashlib.sha256(new_pass.encode()).hexdigest()
                database.set_system_setting("super_admin_pass", new_hash)
                database.log_audit_action(
                    actor=session.get("admin_user", "Super-Admin"),
                    action="ALTERAÇÃO_SENHA",
                    details="Senha do Super-Admin alterada com sucesso",
                    ip_address=request.remote_addr or "127.0.0.1"
                )
                flash("Senha do Super-Admin alterada com sucesso!", "success")

        return redirect(url_for("settings_page"))

    current_token = database.get_system_setting("telegram_bot_token", "")
    recent_logs = database.list_recent_audit_logs(limit=50)

    return render_template(
        "settings.html",
        current_token=current_token,
        recent_logs=recent_logs
    )

# --- Ações de API / AJAX ---

@app.route("/api/admins/add", methods=["POST"])
@super_admin_required
def api_add_admin():
    data = request.form
    telegram_id_raw = data.get("telegram_id", "").strip()
    full_name = data.get("full_name", "").strip()
    username = data.get("username", "").strip()
    role = data.get("role", "admin")

    if not telegram_id_raw.isdigit() or not full_name:
        flash("ID do Telegram e Nome Completo são obrigatórios.", "danger")
        return redirect(url_for("admins_page"))

    telegram_id = int(telegram_id_raw)
    database.add_or_update_admin(
        telegram_id=telegram_id,
        full_name=full_name,
        username=username if username else None,
        role=role,
        status="active"
    )

    database.log_audit_action(
        actor=session.get("admin_user", "Super-Admin"),
        action="ADMIN_ADICIONADO",
        details=f"Administrador {full_name} (ID: {telegram_id}) adicionado manualmente",
        ip_address=request.remote_addr or "127.0.0.1"
    )

    flash(f"Administrador {full_name} cadastrado com sucesso!", "success")
    return redirect(url_for("admins_page"))

@app.route("/api/admins/<int:telegram_id>/status", methods=["POST"])
@super_admin_required
def api_change_admin_status(telegram_id):
    new_status = request.form.get("status")
    if new_status not in ("active", "revoked", "pending"):
        return jsonify({"success": False, "error": "Status inválido"}), 400

    admin = database.get_admin_by_telegram_id(telegram_id)
    if not admin:
        return jsonify({"success": False, "error": "Administrador não encontrado"}), 404

    database.set_admin_status(telegram_id, new_status)

    action_label = "REVOGAÇÃO_ACESSO" if new_status == "revoked" else "ATIVAÇÃO_ACESSO"
    database.log_audit_action(
        actor=session.get("admin_user", "Super-Admin"),
        action=action_label,
        details=f"Status do admin {admin['full_name']} (ID: {telegram_id}) alterado para: {new_status.upper()}",
        ip_address=request.remote_addr or "127.0.0.1"
    )

    flash(f"Status do administrador {admin['full_name']} atualizado para: {new_status.upper()}.", "success")
    return redirect(url_for("admins_page"))

@app.route("/api/admins/<int:telegram_id>/delete", methods=["POST"])
@super_admin_required
def api_delete_admin(telegram_id):
    admin = database.get_admin_by_telegram_id(telegram_id)
    if admin:
        database.delete_admin(telegram_id)
        database.log_audit_action(
            actor=session.get("admin_user", "Super-Admin"),
            action="EXCLUSÃO_ADMIN",
            details=f"Administrador {admin['full_name']} (ID: {telegram_id}) excluído do sistema",
            ip_address=request.remote_addr or "127.0.0.1"
        )
        flash(f"Administrador {admin['full_name']} excluído.", "info")

    return redirect(url_for("admins_page"))

# --- Download e Visualização Segura de Arquivos ---

@app.route("/download/<token>")
def secure_download(token):
    doc = database.get_document_by_token(token)
    if not doc:
        abort(404)

    pdf_path = doc["pdf_path"]
    if not os.path.exists(pdf_path):
        abort(404)

    database.log_audit_action(
        actor=session.get("admin_user", "Download Público/Admin"),
        action="DOWNLOAD_PDF",
        details=f"Download realizado para o documento de {doc['lead_name']} (ID: {doc['id']})",
        ip_address=request.remote_addr or "127.0.0.1"
    )

    safe_filename = f"Declaracao_{doc['lead_name'].replace(' ', '_')}.pdf"
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=safe_filename
    )

@app.route("/preview/<doc_uuid>")
@super_admin_required
def view_preview_image(doc_uuid):
    doc = database.get_document_by_uuid(doc_uuid)
    if not doc or not doc["preview_path"] or not os.path.exists(doc["preview_path"]):
        abort(404)

    return send_file(doc["preview_path"], mimetype="image/png")

@app.route("/avatar/<int:telegram_id>")
def get_admin_avatar(telegram_id):
    """Serve a foto de perfil do administrador baixada do Telegram ou gera fallback vetorial"""
    avatar_file = os.path.join(STORAGE_DIR, "avatars", f"{telegram_id}.jpg")
    if os.path.exists(avatar_file):
        return send_file(avatar_file, mimetype="image/jpeg")

    # Fallback elegante em vetor SVG caso não possua foto no Telegram
    svg_default = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
      <defs>
        <linearGradient id="avatarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#4f46e5"/>
          <stop offset="100%" stop-color="#7c3aed"/>
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="50" fill="url(#avatarGrad)"/>
      <circle cx="50" cy="38" r="18" fill="#ffffff" fill-opacity="0.9"/>
      <path d="M 22 84 C 22 66, 36 60, 50 60 C 64 60, 78 66, 78 84 Z" fill="#ffffff" fill-opacity="0.9"/>
    </svg>'''
    return Response(svg_default, mimetype="image/svg+xml")

@app.route("/api/metrics")
@super_admin_required
def api_get_metrics():
    """Retorna métricas em JSON para atualização em tempo real do frontend"""
    metrics = database.get_dashboard_metrics()
    return jsonify(metrics)

# --- Suporte a Webhook Serverless do Telegram para Vercel ---

bot_dispatcher_instance = None
bot_dispatcher_error = None

def get_serverless_dispatcher():
    global bot_dispatcher_instance, bot_dispatcher_error
    if bot_dispatcher_instance is None:
        try:
            from telegram import Bot
            from telegram.ext import Dispatcher
            from config import TELEGRAM_BOT_TOKEN
            import bot as telegram_bot_module

            token = database.get_system_setting("telegram_bot_token") or TELEGRAM_BOT_TOKEN
            if not token or not str(token).strip():
                bot_dispatcher_error = "Token do Telegram não encontrado"
                app.logger.warning(bot_dispatcher_error)
                return None

            bot_obj = Bot(token=str(token).strip())
            dispatcher = Dispatcher(bot_obj, None, workers=0, use_context=True)
            telegram_bot_module.setup_dispatcher_handlers(dispatcher)
            bot_dispatcher_instance = dispatcher
            app.logger.info("Dispatcher Serverless síncrono inicializado com sucesso.")
        except Exception as e:
            import traceback
            bot_dispatcher_error = f"{type(e).__name__}: {e} | {traceback.format_exc()}"
            app.logger.error(f"Erro ao instanciar Dispatcher Serverless: {bot_dispatcher_error}")
            return None
    return bot_dispatcher_instance

@app.route("/api/telegram-webhook", methods=["POST", "GET"])
def telegram_webhook():
    """Endpoint Serverless de resposta imediata para Webhook do Telegram na Vercel"""
    if request.method == "GET":
        dispatcher = get_serverless_dispatcher()
        if dispatcher:
            return jsonify({"status": "ok", "message": "Webhook serverless ativo e pronto para receber atualizações do Telegram."}), 200
        return jsonify({"status": "error", "message": f"Falha na inicialização do bot: {bot_dispatcher_error}"}), 500

    try:
        from telegram import Update
        dispatcher = get_serverless_dispatcher()
        if not dispatcher:
            return jsonify({"status": "error", "message": f"Bot não configurado: {bot_dispatcher_error}"}), 500

        data = request.get_json(force=True)
        if data:
            update = Update.de_json(data, dispatcher.bot)
            dispatcher.process_update(update)
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        app.logger.error(f"Erro no processamento do webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "no data"}), 400

@app.route("/api/telegram/set-webhook", methods=["POST", "GET"])
def set_telegram_webhook():
    """Ativa o Webhook do Telegram na Vercel de forma rápida e segura"""
    import requests
    from config import TELEGRAM_BOT_TOKEN
    
    custom_url = request.args.get("url") or request.form.get("url")
    if not custom_url:
        host_url = request.host_url.rstrip("/")
        # Se estiver em localhost mas a Vercel estiver informada, permite passar a url
        custom_url = f"{host_url}/api/telegram-webhook"

    token = database.get_system_setting("telegram_bot_token") or TELEGRAM_BOT_TOKEN
    if not token:
        if request.is_json or request.args.get("format") == "json":
            return jsonify({"status": "error", "message": "Token do bot não configurado."}), 400
        flash("Token do bot não configurado.", "danger")
        return redirect(url_for("settings_page") if session.get("logged_in") else url_for("login"))

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/setWebhook",
            params={"url": custom_url},
            timeout=10
        )
        res_data = resp.json()
        if res_data.get("ok"):
            database.set_system_setting("telegram_webhook_url", custom_url)
            database.log_audit_action(
                actor=session.get("admin_user", "Sistema"),
                action="WEBHOOK_ATIVADO",
                details=f"Webhook ativado para: {custom_url}",
                ip_address=request.remote_addr or "127.0.0.1"
            )
            msg = f"Webhook ativado com sucesso no Telegram: {custom_url}"
            if request.is_json or request.args.get("format") == "json":
                return jsonify({"status": "success", "message": msg, "telegram_response": res_data}), 200
            flash(msg, "success")
        else:
            err = res_data.get("description", "Erro desconhecido")
            if request.is_json or request.args.get("format") == "json":
                return jsonify({"status": "error", "message": err}), 400
            flash(f"Telegram retornou erro: {err}", "danger")
    except Exception as e:
        if request.is_json or request.args.get("format") == "json":
            return jsonify({"status": "error", "message": str(e)}), 500
        flash(f"Falha de conexão com a API do Telegram: {e}", "danger")

    return redirect(url_for("settings_page") if session.get("logged_in") else url_for("login"))

# --- Inicialização ---

if __name__ == "__main__":
    database.init_db()
    print(f"Iniciando Super-Admin Dashboard em http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG)
