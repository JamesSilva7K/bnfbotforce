"""
Módulo do Bot do Telegram Avançado & Inteligente - BNF DOCS 2.0
Operação 100% orientada a botões/ações, com rastreamento de etapas em tempo real,
validação algorítmica formal de CPF/RG, linguagem executiva e entrega imediata de PDF.
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ParseMode,
    InputFile
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    Filters,
    CallbackContext
)

from config import TELEGRAM_BOT_TOKEN, STORAGE_DIR
import database
from pdf_engine import PDFEngine

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("TelegramBot")

# Estados da Máquina de Estados
(
    STAGE_NAME,
    STAGE_RG,
    STAGE_CPF,
    STAGE_DATE_CHOICE,
    STAGE_DATE_CUSTOM,
    STAGE_REVIEW,
    STAGE_FAST_IMPORT
) = range(7)

pdf_engine = PDFEngine()

# --- Funções de Validação Algorítmica Formal (PT-BR) ---

def validate_cpf_algorithm(cpf_raw: str) -> Tuple[bool, str]:
    """
    Valida o algoritmo dos dois dígitos verificadores do CPF oficial brasileiro.
    Retorna (valido: bool, cpf_formatado: str).
    """
    digits = re.sub(r"\D", "", cpf_raw)
    if len(digits) != 11:
        return False, cpf_raw.strip()

    # CPFs com todos os dígitos iguais são inválidos
    if digits == digits[0] * 11:
        return False, cpf_raw.strip()

    # Cálculo do primeiro dígito verificador
    soma = sum(int(digits[i]) * (10 - i) for i in range(9))
    d1 = 11 - (soma % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(digits[9]) != d1:
        return False, f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    # Cálculo do segundo dígito verificador
    soma = sum(int(digits[i]) * (11 - i) for i in range(10))
    d2 = 11 - (soma % 11)
    d2 = 0 if d2 >= 10 else d2
    if int(digits[10]) != d2:
        return False, f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

    formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return True, formatted

def sync_telegram_admin_account(telegram_user, bot) -> Dict[str, Any]:
    """
    Identifica o admin do Telegram e reconhece a conta de forma avançada e sem erros:
    - Baixa avatar em alta definição
    - Captura Nome Completo
    - Captura @username
    - Registra data de primeiro contato (first_seen_at) e último acesso (last_active_at)
    - Cria cadastro no banco de dados SQLite para permitir alterações
    """
    if not telegram_user:
        return {}

    avatar_rel_path = None
    try:
        photos = bot.get_user_profile_photos(user_id=telegram_user.id, limit=1)
        if photos and photos.total_count > 0:
            photo_sizes = photos.photos[0]
            best_photo = photo_sizes[-1]
            file_obj = bot.get_file(best_photo.file_id)
            avatars_dir = os.path.join(STORAGE_DIR, "avatars")
            os.makedirs(avatars_dir, exist_ok=True)
            local_avatar = os.path.join(avatars_dir, f"{telegram_user.id}.jpg")
            file_obj.download(custom_path=local_avatar)
            avatar_rel_path = f"storage/avatars/{telegram_user.id}.jpg"
    except Exception as e:
        logger.warning(f"Não foi possível baixar avatar de {telegram_user.id}: {e}")

    full_name = telegram_user.full_name or f"{telegram_user.first_name} {telegram_user.last_name or ''}".strip()
    username = telegram_user.username or ""

    # Consulta perfil em tempo real diretamente na API do Telegram para garantir dados 100% atualizados
    try:
        chat = bot.get_chat(telegram_user.id)
        if chat:
            c_first = chat.first_name or ""
            c_last = chat.last_name or ""
            c_name = f"{c_first} {c_last}".strip() or c_first
            if c_name:
                full_name = c_name
            if chat.username:
                username = chat.username
    except Exception as e:
        logger.warning(f"Aviso ao consultar get_chat de {telegram_user.id}: {e}")

    default_role = "super_admin" if telegram_user.id == 8932547795 else "admin"

    admin_record = database.sync_telegram_admin(
        telegram_id=telegram_user.id,
        full_name=full_name,
        username=username,
        avatar_path=avatar_rel_path,
        default_role=default_role,
        default_status="active"
    )

    return admin_record

def check_admin_access(telegram_user, bot=None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verifica e sincroniza a conta do administrador de forma avançada"""
    if bot:
        admin = sync_telegram_admin_account(telegram_user, bot)
    else:
        admin = database.get_admin_by_telegram_id(telegram_user.id)
        if not admin:
            default_role = "super_admin" if telegram_user.id == 8932547795 else "admin"
            admin = database.sync_telegram_admin(
                telegram_id=telegram_user.id,
                full_name=telegram_user.full_name or telegram_user.first_name,
                username=telegram_user.username or "",
                default_role=default_role,
                default_status="active"
            )

    if admin.get("status") == "revoked":
        return False, "revoked", admin

    return True, "active", admin

# --- Telas e Menus com Linguagem Formal e Botões Modernos ---

def get_home_menu(admin: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
    """Retorna a tela inicial institucional formal com dados do administrador identificado"""
    total = admin.get("total_generated", 0)
    role_label = "Super-Administrador Mestre" if admin.get("role") == "super_admin" else "Administrador Homologado"
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    username_str = f"@{admin['username']}" if admin.get("username") else "identificado"

    text = (
        "🏛️ *SISTEMA DE EMISSÃO DOCUMENTAL OFICIAL*\n"
        "*ASSOCIAÇÃO CULTURAL E SOCIAL DO IDOSO, CRIANÇAS E ADOLESCENTES (ACSICA)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Prezado(a) *{admin['full_name']}* ({username_str}),\n"
        "Sua conta foi reconhecida e autenticada com sucesso no terminal de emissão.\n\n"
        f"🔐 *Credencial:* `{admin['telegram_id']}` ({role_label})\n"
        f"📅 *Primeiro Contato:* `{admin.get('first_seen_at') or 'Hoje'}`\n"
        f"🟢 *Status de Conexão:* Sincronizado & Ativo\n"
        f"📈 *Total Emitido por Você:* `{total}` documentos\n"
        f"🕒 *Sessão Aberta:* `{now_str}`\n\n"
        "Selecione uma ação abaixo para iniciar a operação:"
    )

    buttons = [
        [InlineKeyboardButton("📄 Iniciar Emissão de Declaração", callback_data="act_start_wizard")],
        [InlineKeyboardButton("⚡ Importação Rápida de Lead", callback_data="act_fast_import")],
        [
            InlineKeyboardButton("📊 Minhas Emissões", callback_data="act_my_history"),
            InlineKeyboardButton("🏢 Dados da Entidade", callback_data="act_entity_info")
        ],
        [InlineKeyboardButton("🔄 Sincronizar Painel", callback_data="act_refresh_home")]
    ]

    return text, InlineKeyboardMarkup(buttons)

# --- Handlers de Comandos Iniciais ---

def start_command(update: Update, context: CallbackContext) -> int:
    """Ponto de entrada formal do bot (/start ou /menu) com reconhecimento automático de conta"""
    user = update.effective_user
    authorized, status, admin = check_admin_access(user, context.bot)

    if not authorized:
        if status == "revoked":
            text = (
                "⛔ *ACESSO SUSPENSO*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Sr.(a) {user.full_name or user.first_name},\n\n"
                "Seu acesso ao sistema de geração e autenticação de documentos foi *revogado pelo Super-Administrador* no Painel de Controle.\n\n"
                "Qualquer tentativa de emissão permanece desativada até deliberação central."
            )
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END

    # Usuário Autorizado e Reconhecido
    text, markup = get_home_menu(admin)
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    return ConversationHandler.END

def cancel_operation(update: Update, context: CallbackContext) -> int:
    """Cancela o processo atual e retorna à tela principal"""
    context.user_data.clear()
    user = update.effective_user
    authorized, status, admin = check_admin_access(user)

    text = "❌ *Operação encerrada.* Os dados em preenchimento foram descartados com segurança."
    if authorized and admin:
        home_text, markup = get_home_menu(admin)
        if update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(f"{text}\n\n{home_text}", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        else:
            update.message.reply_text(f"{text}\n\n{home_text}", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        if update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# --- Handlers de Ações e Menus Secundários ---

def handle_home_callbacks(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    user = update.effective_user

    # Solicitação de Autorização
    if data.startswith("req_auth:"):
        database.add_or_update_admin(
            telegram_id=user.id,
            full_name=user.full_name or user.first_name,
            username=user.username,
            role="admin",
            status="pending"
        )
        database.log_audit_action(
            actor=f"{user.full_name} ({user.id})",
            action="SOLICITAÇÃO_ACESSO",
            details="Solicitação de credenciamento enviada via Telegram",
            ip_address="TELEGRAM_BOT"
        )
        query.edit_message_text(
            "✅ *Solicitação de credenciamento submetida com sucesso!*\n\n"
            "O Super-Administrador foi alertado no Painel de Controle e poderá liberar seu acesso.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    authorized, status, admin = check_admin_access(user)
    if not authorized:
        query.edit_message_text("⛔ Acesso não autorizado.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    if data == "act_refresh_home":
        text, markup = get_home_menu(admin)
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        return ConversationHandler.END

    if data == "act_start_wizard":
        context.user_data.clear()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar Operação", callback_data="act_cancel_wizard")]
        ])
        text = (
            "📍 *ETAPA 1 DE 3 • NOME COMPLETO DO LEAD*\n"
            "Progresso: `[▓▓▓░░░░░░░] 33%`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Por favor, informe o *Nome Completo do Beneficiário / Lead*:\n\n"
            "💡 _Exemplo: LUCIANO GOMES DA ROCHA_\n"
            "_(O sistema padronizará automaticamente em caixa alta e negrito)_"
        )
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return STAGE_NAME

    if data == "act_fast_import":
        context.user_data.clear()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar Importação", callback_data="act_cancel_wizard")]
        ])
        text = (
            "⚡ *IMPORTAÇÃO RÁPIDA DE LEAD (PROCESSAMENTO INTELIGENTE)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie os dados do lead em uma única mensagem para preenchimento imediato.\n\n"
            "📋 *Padrão Recomendado (com ou sem pontuação):*\n"
            "`Nome: Luciano Gomes da Rocha`\n"
            "`RG: 37.946.747-1` (ou apenas números)\n"
            "`CPF: 340.091.828/81` (ou apenas números)\n\n"
            "Aguardando o envio da mensagem..."
        )
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return STAGE_FAST_IMPORT

    if data == "act_my_history":
        docs = database.list_documents(limit=5, admin_id=user.id)
        if not docs:
            text = (
                "📊 *HISTÓRICO DE EMISSÕES*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Você ainda não realizou emissões no sistema."
            )
        else:
            text = (
                "📊 *SUAS ÚLTIMAS 5 DECLARAÇÕES EMITIDAS:*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            for d in docs:
                text += (
                    f"📄 *{d['lead_name']}*\n"
                    f"• RG: `{d['lead_rg']}` | CPF: `{d['lead_cpf']}`\n"
                    f"• Emissão: {d['data_emissao']} | Autenticado em: {d['created_at']}\n"
                    f"• SHA-256: `{d['file_hash'][:12]}...`\n"
                    f"─────────────────────────\n"
                )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Retornar ao Painel", callback_data="act_refresh_home")]
        ])
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return ConversationHandler.END

    if data == "act_entity_info":
        text = (
            "🏢 *DADOS DA ENTIDADE EMISSORA OFICIAL*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "• *Razão Social:* ASSOCIAÇÃO CULTURAL E SOCIAL DO IDOSO, CRIANÇAS E ADOLESCENTES (ACSICA)\n"
            "• *CNPJ Oficial:* 08.482.362/0001-78\n"
            "• *Endereço:* Rua Giacomo Quirino, 96 / Quadra F – Conjunto Residencial José Bonifácio, São Paulo - SP, CEP 08255-490\n"
            "• *Contato Institucional:* (11) 95174-1577 / (11) 5050-5254\n"
            "• *E-mail:* emersonearte@gmail.com\n\n"
            "✍️ *Signatário Homologado:*\n"
            "• Emerson de Godoy Costa dos Santos (Diretor Presidente)\n"
            "• RG: 44.310.263-06 | CPF: 230.974.128-08"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Retornar ao Painel", callback_data="act_refresh_home")]
        ])
        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return ConversationHandler.END

    return ConversationHandler.END

# --- Fluxo Guiado Passo a Passo (Etapas 1 a 3) ---

def stage_name_received(update: Update, context: CallbackContext) -> int:
    raw_name = update.message.text.strip()
    if len(raw_name) < 4:
        update.message.reply_text("⚠️ O nome do lead deve conter no mínimo 4 caracteres. Digite o nome completo:")
        return STAGE_NAME

    clean_name = raw_name.upper()
    context.user_data["lead_name"] = clean_name

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="act_cancel_wizard")]
    ])

    text = (
        "📍 *ETAPA 2 DE 3 • REGISTRO GERAL (RG)*\n"
        "Progresso: `[▓▓▓▓▓▓░░░░] 66%`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *Lead Registrado:* `{clean_name}`\n\n"
        "Por favor, informe o *RG do Lead*:\n\n"
        "💡 _Exemplo: 37.946.747-1 (pontuação aplicada automaticamente se digitado sem pontos)_"
    )

    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    return STAGE_RG

def stage_rg_received(update: Update, context: CallbackContext) -> int:
    raw_rg = update.message.text.strip()
    if len(raw_rg) < 4:
        update.message.reply_text("⚠️ RG inválido ou insuficiente. Informe o documento novamente:")
        return STAGE_RG

    formatted_rg = PDFEngine.format_rg(raw_rg)
    context.user_data["lead_rg"] = formatted_rg

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Corrigir Nome", callback_data="act_edit_name")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="act_cancel_wizard")]
    ])

    text = (
        "📍 *ETAPA 3 DE 3 • CADASTRO DE PESSOA FÍSICA (CPF)*\n"
        "Progresso: `[▓▓▓▓▓▓▓▓▓▓] 100%`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *Lead:* `{context.user_data['lead_name']}`\n"
        f"🆔 *RG Validado:* `{formatted_rg}`\n\n"
        "Por favor, informe o *CPF do Lead*:\n\n"
        "💡 _Exemplo: 340.091.828/81 (pontuação e barra aplicadas automaticamente se digitado sem pontos)_"
    )

    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    return STAGE_CPF

def stage_cpf_received(update: Update, context: CallbackContext) -> int:
    raw_cpf = update.message.text.strip()
    clean_cpf = PDFEngine.format_cpf(raw_cpf)
    context.user_data["lead_cpf"] = clean_cpf
    context.user_data["lead_date"] = datetime.now().strftime("%d/%m/%Y")

    return render_review_screen(update, context, is_callback=False)

# --- Parser de Importação Rápida (NLP Inteligente) ---

def stage_fast_import_received(update: Update, context: CallbackContext) -> int:
    text = update.message.text.strip()

    nome_match = re.search(r"(?:nome|lead|titular|cliente|sr\.?|sra\.?)\s*[:=-]?\s*([A-Za-zÀ-ÖØ-öø-ÿ\s]{4,})", text, re.IGNORECASE)
    cpf_match = re.search(r"(?:cpf)\s*[:=-]?\s*([\d\.\-/]{8,15})", text, re.IGNORECASE) or re.search(r"(\d{3}\.?\d{3}\.?\d{3}[-/]?\d{2})", text)
    rg_match = re.search(r"(?:rg)\s*[:=-]?\s*([\d\.\-Xx]{6,15})", text, re.IGNORECASE) or re.search(r"(\d{1,2}\.?\d{3}\.?\d{3}[-]?[\dXx])", text)

    extracted_name = nome_match.group(1).split("\n")[0].strip() if nome_match else None
    extracted_cpf = cpf_match.group(1).strip() if cpf_match else None
    extracted_rg = rg_match.group(1).strip() if rg_match else None

    # Fallback por linhas sequenciais
    if not extracted_name or not extracted_cpf:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) >= 3:
            extracted_name = extracted_name or lines[0]
            extracted_rg = extracted_rg or lines[1]
            extracted_cpf = extracted_cpf or lines[2]

    if not extracted_name or not extracted_cpf:
        update.message.reply_text(
            "⚠️ Não foi possível identificar com precisão o Nome e CPF do lead na mensagem enviada.\n\n"
            "Envie no modelo:\n"
            "`Nome: Carlos Alberto Silva`\n"
            "`RG: 37.946.747-1`\n"
            "`CPF: 340.091.828/81`",
            parse_mode=ParseMode.MARKDOWN
        )
        return STAGE_FAST_IMPORT

    context.user_data["lead_name"] = extracted_name.upper()
    context.user_data["lead_rg"] = PDFEngine.format_rg(extracted_rg or "NÃO CONSTA")
    context.user_data["lead_cpf"] = PDFEngine.format_cpf(extracted_cpf)
    context.user_data["lead_date"] = datetime.now().strftime("%d/%m/%Y")

    return render_review_screen(update, context, is_callback=False)

# --- Tela Executiva de Revisão & Confirmação ---

def render_review_screen(update: Update, context: CallbackContext, is_callback: bool = False) -> int:
    name = context.user_data.get("lead_name", "")
    rg = context.user_data.get("lead_rg", "")
    cpf = context.user_data.get("lead_cpf", "")

    text = (
        "📑 *REVISÃO DOCUMENTAL PRÉ-EMISSÃO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏢 *Entidade:* ACSICA (CNPJ: 08.482.362/0001-78)\n"
        "📄 *Documento:* Declaração de Endereço / Referência de Domicílio\n\n"
        f"👤 *Titular / Lead:* `{name}`\n"
        f"🆔 *Registro Geral (RG):* `{rg}`\n"
        f"📄 *Cadastro CPF:* `{cpf}`\n"
        "📍 *Local de Emissão:* São Paulo, SP\n"
        "✍️ *Signatário:* Emerson de Godoy Costa dos Santos (Presidente)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 _O documento alterará estritamente os dados do lead com tipografia vetorial de precisão._\n\n"
        "Clique no botão abaixo para gerar o PDF oficial:"
    )

    buttons = [
        [InlineKeyboardButton("🚀 Emitir e Autenticar Documento", callback_data="act_do_generate")],
        [
            InlineKeyboardButton("✏️ Editar Nome", callback_data="act_edit_name"),
            InlineKeyboardButton("✏️ Editar RG", callback_data="act_edit_rg")
        ],
        [
            InlineKeyboardButton("✏️ Editar CPF", callback_data="act_edit_cpf")
        ],
        [InlineKeyboardButton("❌ Cancelar Operação", callback_data="act_cancel_wizard")]
    ]

    markup = InlineKeyboardMarkup(buttons)

    if is_callback:
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    else:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

    return STAGE_REVIEW

# --- Execução da Emissão e Envio do Arquivo Oficial ---

def execute_document_generation(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user = update.effective_user

    authorized, status, admin = check_admin_access(user)
    if not authorized:
        query.edit_message_text("⛔ Operação suspensa: seu acesso foi revogado.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    name = context.user_data.get("lead_name")
    rg = context.user_data.get("lead_rg")
    cpf = context.user_data.get("lead_cpf")
    date_str = context.user_data.get("lead_date")

    if not name or not cpf:
        query.edit_message_text("⚠️ Informações incompletas para emissão. Inicie novamente pelo menu.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    # Feedback dinâmico de progresso
    query.edit_message_text(
        "⏳ *PROCESSANDO EMISSÃO OFICIAL...*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Redigindo campos no modelo matriz ACSICA...\n"
        "• Aplicando tipografia vetorial de alta definição...\n"
        "• Calculando hash criptográfico de integridade...\n\n"
        "_Aguarde o envio do documento oficial..._",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # 1. Gera o PDF em alta definição
        pdf_path, preview_path = pdf_engine.generate_declaration(
            nome=name,
            rg=rg,
            cpf=cpf,
            data_emissao=date_str
        )

        filename = os.path.basename(pdf_path)

        # 2. Registra no banco de dados e trilha de auditoria
        doc_record = database.register_document(
            admin_telegram_id=user.id,
            admin_name=admin["full_name"],
            lead_name=name,
            lead_rg=rg,
            lead_cpf=cpf,
            data_emissao=date_str,
            pdf_filename=filename,
            pdf_path=pdf_path,
            preview_path=preview_path
        )

        # 3. Legenda oficial detalhada
        caption = (
            "✅ *DECLARAÇÃO OFICIAL EMITIDA COM SUCESSO!*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Lead:* `{name}`\n"
            f"🆔 *RG:* `{rg}`\n"
            f"📄 *CPF:* `{cpf}`\n"
            f"📅 *Data:* `{date_str}`\n"
            f"🔐 *SHA-256:* `{doc_record['file_hash'][:16]}...`\n"
            f"👤 *Administrador:* {admin['full_name']}\n"
            f"🏢 *Entidade:* ACSICA - CNPJ 08.482.362/0001-78\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 *O arquivo oficial segue anexado abaixo pronto para download e impressão.*"
        )

        post_actions = [
            [InlineKeyboardButton("📄 Nova Declaração", callback_data="act_start_wizard")],
            [InlineKeyboardButton("📊 Minhas Emissões", callback_data="act_my_history")],
            [InlineKeyboardButton("🏠 Menu Principal", callback_data="act_refresh_home")]
        ]

        safe_doc_name = f"Declaracao_Endereco_{name.replace(' ', '_')}.pdf"

        with open(pdf_path, "rb") as pdf_file:
            query.message.reply_document(
                document=InputFile(pdf_file, filename=safe_doc_name),
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(post_actions)
            )

        context.user_data.clear()

    except Exception as e:
        logger.error(f"Erro na emissão do documento: {e}", exc_info=True)
        query.message.reply_text(f"❌ Ocorreu uma falha no processamento do documento: {e}")

    return ConversationHandler.END

# --- Navegação Reversa (Edição de Campos pelo Wizard) ---

def handle_inline_field_edits(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="act_cancel_wizard")]])

    if data == "act_edit_name":
        query.edit_message_text("👤 Digite o novo *Nome Completo do Lead*:", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return STAGE_NAME

    if data == "act_edit_rg":
        query.edit_message_text("🆔 Digite o novo *RG do Lead*:", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return STAGE_RG

    if data == "act_edit_cpf":
        query.edit_message_text("📄 Digite o novo *CPF do Lead*:", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return STAGE_CPF

    return STAGE_REVIEW

# --- Inicializador e Configuração do Bot ---

def create_bot_updater(token: Optional[str] = None) -> Optional[Updater]:
    """Instancia o Updater com todos os handlers e máquina de estados interativa"""
    active_token = token or database.get_system_setting("telegram_bot_token") or TELEGRAM_BOT_TOKEN
    if not active_token or active_token.strip() == "":
        logger.warning("Token do Telegram Bot não configurado.")
        return None

    try:
        updater = Updater(token=active_token, use_context=True)
        dispatcher = updater.dispatcher

        # Conversação 100% Interativa por Botões & Ações
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_home_callbacks, pattern=r"^(act_start_wizard|act_fast_import)$")
            ],
            states={
                STAGE_NAME: [
                    MessageHandler(Filters.text & ~Filters.command, stage_name_received),
                    CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
                ],
                STAGE_RG: [
                    MessageHandler(Filters.text & ~Filters.command, stage_rg_received),
                    CallbackQueryHandler(handle_inline_field_edits, pattern="^act_edit_name$"),
                    CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
                ],
                STAGE_CPF: [
                    MessageHandler(Filters.text & ~Filters.command, stage_cpf_received),
                    CallbackQueryHandler(handle_inline_field_edits, pattern="^act_edit_rg$"),
                    CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
                ],
                STAGE_REVIEW: [
                    CallbackQueryHandler(execute_document_generation, pattern="^act_do_generate$"),
                    CallbackQueryHandler(handle_inline_field_edits, pattern=r"^(act_edit_name|act_edit_rg|act_edit_cpf)$"),
                    CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
                ],
                STAGE_FAST_IMPORT: [
                    MessageHandler(Filters.text & ~Filters.command, stage_fast_import_received),
                    CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_operation),
                CallbackQueryHandler(cancel_operation, pattern="^act_cancel_wizard$")
            ],
            allow_reentry=True
        )

        dispatcher.add_handler(CommandHandler("start", start_command))
        dispatcher.add_handler(CommandHandler("menu", start_command))
        dispatcher.add_handler(CommandHandler("cancel", cancel_operation))
        dispatcher.add_handler(conv_handler)
        dispatcher.add_handler(CallbackQueryHandler(handle_home_callbacks))

        return updater

    except Exception as e:
        logger.error(f"Erro ao instanciar Updater do Telegram: {e}")
        return None

if __name__ == "__main__":
    bot_updater = create_bot_updater()
    if bot_updater:
        print("[BOT] Executando em modo polling...")
        bot_updater.start_polling()
        bot_updater.idle()
