"""
Módulo de Banco de Dados SQLite com WAL mode e Criptografia
Gerencia Administradores, Registros de Documentos, Logs de Auditoria e Configurações
"""

import sqlite3
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DB_PATH, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Ativa WAL mode para suporte robusto a leituras e gravações concorrentes
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Inicializa as tabelas do sistema se não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabela de Administradores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS administrators (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'admin',  -- 'super_admin' ou 'admin'
        status TEXT DEFAULT 'active', -- 'active', 'revoked', 'pending'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active_at DATETIME,
        total_generated INTEGER DEFAULT 0
    );
    """)

    # 2. Tabela de Documentos Gerados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_uuid TEXT UNIQUE NOT NULL,
        admin_telegram_id INTEGER,
        admin_name TEXT NOT NULL,
        lead_name TEXT NOT NULL,
        lead_rg TEXT NOT NULL,
        lead_cpf TEXT NOT NULL,
        data_emissao TEXT NOT NULL,
        pdf_filename TEXT NOT NULL,
        pdf_path TEXT NOT NULL,
        preview_path TEXT,
        file_hash TEXT,
        download_token TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_telegram_id) REFERENCES administrators (telegram_id) ON DELETE SET NULL
    );
    """)

    # 3. Tabela de Auditoria (Logs de Atividade)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Tabela de Configurações do Sistema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrações seguras para tabelas existentes
    cursor.execute("PRAGMA table_info(administrators);")
    cols = [col[1] for col in cursor.fetchall()]
    if "avatar_path" not in cols:
        cursor.execute("ALTER TABLE administrators ADD COLUMN avatar_path TEXT;")
    if "first_seen_at" not in cols:
        cursor.execute("ALTER TABLE administrators ADD COLUMN first_seen_at DATETIME;")

    # Cria usuário Super-Admin padrão se não existir nas configurações
    cursor.execute("SELECT value FROM system_settings WHERE key = 'super_admin_pass'")
    if not cursor.fetchone():
        hashed_pass = hashlib.sha256(DEFAULT_ADMIN_PASS.encode()).hexdigest()
        cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)", ('super_admin_user', DEFAULT_ADMIN_USER))
        cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)", ('super_admin_pass', hashed_pass))

    # Cria índices para alta performance de busca
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_admin ON documents (admin_telegram_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_created ON documents (created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_lead_name ON documents (lead_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_admins_telegram ON administrators (telegram_id);")

    conn.commit()
    conn.close()

# --- Funções para Administradores ---

def get_admin_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM administrators WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_all_admins() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM administrators ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def sync_telegram_admin(
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
    avatar_path: Optional[str] = None,
    default_role: str = "admin",
    default_status: str = "active"
) -> Dict[str, Any]:
    """
    Sincroniza e cadastra automaticamente um administrador identificado via Telegram.
    Armazena avatar, nome completo, @username, data de primeiro contato e última atividade.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM administrators WHERE telegram_id = ?", (telegram_id,))
    existing = cursor.fetchone()

    if not existing:
        cursor.execute("""
        INSERT INTO administrators (
            telegram_id, username, full_name, role, status, avatar_path, first_seen_at, last_active_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            username or "",
            full_name,
            default_role,
            default_status,
            avatar_path,
            now,
            now,
            now
        ))
    else:
        if avatar_path:
            cursor.execute("""
            UPDATE administrators 
            SET username = ?, full_name = ?, avatar_path = ?, last_active_at = ?
            WHERE telegram_id = ?
            """, (username or "", full_name, avatar_path, now, telegram_id))
        else:
            cursor.execute("""
            UPDATE administrators 
            SET username = ?, full_name = ?, last_active_at = ?
            WHERE telegram_id = ?
            """, (username or "", full_name, now, telegram_id))

    conn.commit()

    cursor.execute("SELECT * FROM administrators WHERE telegram_id = ?", (telegram_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

def add_or_update_admin(
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
    role: str = "admin",
    status: str = "active",
    avatar_path: Optional[str] = None
) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO administrators (telegram_id, username, full_name, role, status, avatar_path, first_seen_at, created_at, last_active_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(telegram_id) DO UPDATE SET
        username = excluded.username,
        full_name = excluded.full_name,
        role = excluded.role,
        status = excluded.status,
        avatar_path = COALESCE(excluded.avatar_path, administrators.avatar_path),
        last_active_at = excluded.last_active_at
    """, (telegram_id, username or "", full_name, role, status, avatar_path, now, now, now))
    conn.commit()
    conn.close()
    return True

def set_admin_status(telegram_id: int, new_status: str) -> bool:
    """Altera o status do administrador ('active', 'revoked', 'pending')"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE administrators SET status = ? WHERE telegram_id = ?", (new_status, telegram_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def delete_admin(telegram_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM administrators WHERE telegram_id = ?", (telegram_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def update_admin_activity(telegram_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    UPDATE administrators 
    SET last_active_at = ?, total_generated = total_generated + 1 
    WHERE telegram_id = ?
    """, (now, telegram_id))
    conn.commit()
    conn.close()

# --- Funções para Documentos ---

def register_document(
    admin_telegram_id: Optional[int],
    admin_name: str,
    lead_name: str,
    lead_rg: str,
    lead_cpf: str,
    data_emissao: str,
    pdf_filename: str,
    pdf_path: str,
    preview_path: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    doc_uuid = str(uuid.uuid4())
    download_token = str(uuid.uuid4()).replace("-", "")
    
    # Gera hash SHA256 do arquivo para integridade
    file_hash = ""
    try:
        with open(pdf_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO documents (
        doc_uuid, admin_telegram_id, admin_name, lead_name, lead_rg, lead_cpf,
        data_emissao, pdf_filename, pdf_path, preview_path, file_hash, download_token, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_uuid, admin_telegram_id, admin_name, lead_name, lead_rg, lead_cpf,
        data_emissao, pdf_filename, pdf_path, preview_path or "", file_hash, download_token, now
    ))
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()

    if admin_telegram_id:
        update_admin_activity(admin_telegram_id)

    # Registra no log de auditoria
    log_audit_action(
        actor=admin_name,
        action="GERAÇÃO_PDF",
        details=f"Documento gerado para Lead: {lead_name} (CPF: {lead_cpf}, RG: {lead_rg})",
        ip_address="TELEGRAM_BOT" if admin_telegram_id else "DASHBOARD_WEB"
    )

    return {
        "id": doc_id,
        "doc_uuid": doc_uuid,
        "download_token": download_token,
        "file_hash": file_hash,
        "created_at": now
    }

def get_document_by_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE download_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_document_by_uuid(doc_uuid: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE doc_uuid = ?", (doc_uuid,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def list_documents(limit: int = 100, offset: int = 0, search: Optional[str] = None, admin_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM documents WHERE 1=1"
    params = []

    if admin_id:
        query += " AND admin_telegram_id = ?"
        params.append(admin_id)

    if search:
        query += " AND (lead_name LIKE ? OR lead_cpf LIKE ? OR lead_rg LIKE ? OR admin_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_documents_count(search: Optional[str] = None, admin_id: Optional[int] = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT COUNT(*) FROM documents WHERE 1=1"
    params = []

    if admin_id:
        query += " AND admin_telegram_id = ?"
        params.append(admin_id)

    if search:
        query += " AND (lead_name LIKE ? OR lead_cpf LIKE ? OR lead_rg LIKE ? OR admin_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    conn.close()
    return count

# --- Funções de Auditoria e Métricas ---

def log_audit_action(actor: str, action: str, details: str = "", ip_address: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs (actor, action, details, ip_address)
    VALUES (?, ?, ?, ?)
    """, (actor, action, details, ip_address))
    conn.commit()
    conn.close()

def list_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_metrics() -> Dict[str, Any]:
    """Retorna métricas consolidadas em tempo real para o Super-Admin"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total de PDFs
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_docs = cursor.fetchone()[0]

    # PDFs hoje
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM documents WHERE created_at LIKE ?", (f"{today_str}%",))
    docs_today = cursor.fetchone()[0]

    # Administradores Ativos
    cursor.execute("SELECT COUNT(*) FROM administrators WHERE status = 'active'")
    admins_active = cursor.fetchone()[0]

    # Administradores Revogados
    cursor.execute("SELECT COUNT(*) FROM administrators WHERE status = 'revoked'")
    admins_revoked = cursor.fetchone()[0]

    # Administradores Pendentes
    cursor.execute("SELECT COUNT(*) FROM administrators WHERE status = 'pending'")
    admins_pending = cursor.fetchone()[0]

    # Atividade por dia nos últimos 7 dias
    cursor.execute("""
    SELECT SUBSTR(created_at, 1, 10) as day, COUNT(*) as cnt
    FROM documents
    WHERE created_at >= date('now', '-7 days')
    GROUP BY day
    ORDER BY day ASC
    """)
    daily_stats = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_docs": total_docs,
        "docs_today": docs_today,
        "admins_active": admins_active,
        "admins_revoked": admins_revoked,
        "admins_pending": admins_pending,
        "daily_stats": daily_stats
    }

# --- Configurações do Sistema ---

def get_system_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_system_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO system_settings (key, value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, value, now))
    conn.commit()
    conn.close()

# Auto-inicialização na importação
init_db()
