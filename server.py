# SGCA v0.10.0 — Servidor local: SQLite, autenticação, REST API, proxy CNPJ, e-mail SMTP, backup automático
import http.server
import socketserver
import os
import json
import sqlite3
import hashlib
import secrets
import ssl
import smtplib
import threading
import time
import subprocess
import sys
import urllib.request
import logging
import urllib.error
import uuid
import re
import base64

# Windows: console pode usar cp1252/cp850 em vez de UTF-8, quebrando prints
# com caracteres especiais (╔═╗, emojis). Força UTF-8 para evitar UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
import html as html_mod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qs

PORT          = 3002
_BASE         = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(_BASE, 'sgca.db')
UPLOADS_DIR   = os.path.join(_BASE, 'uploads')
BACKUP_DIR    = os.path.join(_BASE, 'backups')
PROFILE_DIR   = os.path.join(_BASE, 'browser-profile')
LOG_PATH      = os.path.join(_BASE, 'sgca_errors.log')
BACKUP_KEEP   = 7        # número de backups automáticos mantidos
SESSION_TTL   = 15   # 15s — renovado pelo ping a cada 5s; expira rápido se browser fechar

logging.basicConfig(
    filename=LOG_PATH, level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
_log = logging.getLogger('sgca')

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(UPLOADS_DIR, exist_ok=True)

_watchdog_paused  = False   # pausa o watchdog durante diálogos bloqueantes (ex: FolderBrowser)
_had_session      = False   # True após primeiro login; evita encerramento antes de qualquer usuário logar
_modo_servidor    = False   # True = modo servidor contínuo (sem encerramento automático)
_backup_pos_sess  = False   # True = backup pós-sessão já executado; aguarda nova sessão para resetar
FTS_AVAILABLE     = False   # True se o SQLite tem FTS5 compilado (setado em init_db)

# ── Banco de dados ────────────────────────────────────────────────────────────

class _ConnAutoClose(sqlite3.Connection):
    """sqlite3.Connection.__exit__ só faz commit/rollback da transação — não fecha
    a conexão. Sem isso, todo `with get_db() as conn:` (63 pontos no arquivo) vaza
    uma conexão aberta por chamada. Fecha a conexão junto, sem precisar alterar
    nenhum call site."""
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

def get_db():
    conn = sqlite3.connect(DB_PATH, factory=_ConnAutoClose)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    with get_db() as conn:
        # Migração: tabela 'users' (nome antigo) → 'usuarios' (padrão SGDP).
        # SQLite atualiza sozinho as FKs de sessions/contratos/atas que apontavam
        # para users(id); preserva cargo/matricula e todos os dados existentes.
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'users' in tables and 'usuarios' not in tables:
            conn.execute('ALTER TABLE users RENAME TO usuarios')
            conn.commit()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL UNIQUE COLLATE NOCASE,
                nome       TEXT NOT NULL,
                cargo      TEXT,
                matricula  TEXT,
                senha_hash TEXT NOT NULL,
                admin      INTEGER DEFAULT 0,
                ativo      INTEGER DEFAULT 1,
                criado_em  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token    TEXT PRIMARY KEY,
                user_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                expires  REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fornecedores (
                id           TEXT PRIMARY KEY,
                data         TEXT NOT NULL,
                cnpj         TEXT,
                razao_social TEXT,
                updated_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS contratos (
                id             TEXT PRIMARY KEY,
                data           TEXT NOT NULL,
                objeto         TEXT,
                status         TEXT DEFAULT 'vigente',
                fornecedor_id  TEXT,
                vigencia_final TEXT,
                valor_global   REAL,
                created_at     TEXT,
                updated_at     TEXT,
                created_by     INTEGER REFERENCES usuarios(id),
                deleted_at     TEXT
            );
            CREATE TABLE IF NOT EXISTS atas (
                id             TEXT PRIMARY KEY,
                data           TEXT NOT NULL,
                numero         TEXT,
                status         TEXT DEFAULT 'vigente',
                vigencia_final TEXT,
                created_at     TEXT,
                updated_at     TEXT,
                created_by     INTEGER REFERENCES usuarios(id),
                deleted_at     TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_global (
                id          TEXT PRIMARY KEY,
                ts          TEXT NOT NULL,
                user_id     INTEGER,
                user_nome   TEXT,
                type        TEXT,
                label       TEXT,
                detail      TEXT,
                process_id  TEXT,
                process_obj TEXT
            );
            CREATE TABLE IF NOT EXISTS sys_settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS tags (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE COLLATE NOCASE
            );
            CREATE TABLE IF NOT EXISTS contrato_tags (
                contrato_id TEXT NOT NULL REFERENCES contratos(id) ON DELETE CASCADE,
                tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (contrato_id, tag_id)
            );
            CREATE TABLE IF NOT EXISTS ata_tags (
                ata_id TEXT NOT NULL REFERENCES atas(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (ata_id, tag_id)
            );
            CREATE INDEX IF NOT EXISTS idx_forn_cnpj     ON fornecedores(cnpj);
            CREATE INDEX IF NOT EXISTS idx_contr_status  ON contratos(status);
            CREATE INDEX IF NOT EXISTS idx_contr_forn    ON contratos(fornecedor_id);
            CREATE INDEX IF NOT EXISTS idx_contr_vig     ON contratos(vigencia_final);
            CREATE INDEX IF NOT EXISTS idx_contr_deleted ON contratos(deleted_at);
            CREATE INDEX IF NOT EXISTS idx_ata_status    ON atas(status);
            CREATE INDEX IF NOT EXISTS idx_ata_vig       ON atas(vigencia_final);
            CREATE INDEX IF NOT EXISTS idx_ata_deleted   ON atas(deleted_at);
            CREATE INDEX IF NOT EXISTS idx_audit_ts      ON audit_global(ts);
            CREATE INDEX IF NOT EXISTS idx_contr_tags_tag ON contrato_tags(tag_id);
            CREATE INDEX IF NOT EXISTS idx_ata_tags_tag   ON ata_tags(tag_id);
        ''')
        global FTS_AVAILABLE
        try:
            conn.executescript('''
                CREATE VIRTUAL TABLE IF NOT EXISTS contratos_fts USING fts5(
                    objeto, content='contratos', content_rowid='rowid'
                );
                CREATE TRIGGER IF NOT EXISTS contratos_fts_ai AFTER INSERT ON contratos BEGIN
                    INSERT INTO contratos_fts(rowid, objeto) VALUES (new.rowid, new.objeto);
                END;
                CREATE TRIGGER IF NOT EXISTS contratos_fts_ad AFTER DELETE ON contratos BEGIN
                    INSERT INTO contratos_fts(contratos_fts, rowid, objeto) VALUES ('delete', old.rowid, old.objeto);
                END;
                CREATE TRIGGER IF NOT EXISTS contratos_fts_au AFTER UPDATE ON contratos BEGIN
                    INSERT INTO contratos_fts(contratos_fts, rowid, objeto) VALUES ('delete', old.rowid, old.objeto);
                    INSERT INTO contratos_fts(rowid, objeto) VALUES (new.rowid, new.objeto);
                END;
            ''')
            if conn.execute('SELECT COUNT(*) FROM contratos_fts').fetchone()[0] == 0:
                conn.execute("INSERT INTO contratos_fts(rowid, objeto) SELECT rowid, objeto FROM contratos")
            FTS_AVAILABLE = True
        except sqlite3.OperationalError as e:
            # ponytail: builds do SQLite sem FTS5 (raro) caem para busca com LIKE
            _log.error('FTS5 indisponível, busca usará LIKE: %s', e)
            FTS_AVAILABLE = False
        # Migração: coluna deleted_at para lixeira (soft-delete) — SQLite não suporta
        # ADD COLUMN IF NOT EXISTS, então tentamos e ignoramos se já existir
        try:
            conn.execute('ALTER TABLE fornecedores ADD COLUMN deleted_at TEXT')
        except sqlite3.OperationalError:
            pass
        conn.execute('CREATE INDEX IF NOT EXISTS idx_forn_deleted ON fornecedores(deleted_at)')
        # Sessões são descartadas a cada início do servidor (logout automático ao fechar janela)
        conn.execute('DELETE FROM sessions')
        # Cria admin padrão se não houver usuários
        if conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0:
            conn.execute(
                'INSERT INTO usuarios (username,nome,cargo,senha_hash,admin) VALUES (?,?,?,?,1)',
                ('admin', 'Administrador', 'Agente de Contratação', _hash_password('admin123'))
            )
            conn.commit()
            print('Usuário padrão criado: admin / admin123 — troque a senha nas Configurações.')

def _fts_match_query(text):
    """Converte texto livre em uma query FTS5 (AND de prefixos por palavra)."""
    tokens = re.findall(r'\w+', text, re.UNICODE)
    if not tokens: return None
    return ' '.join(f'"{t}"*' for t in tokens)

def _sync_tags(conn, join_table, id_col, item_id, tag_names):
    """Substitui as tags do registro pela lista informada (cria as que não existem)."""
    nomes = sorted({t.strip() for t in (tag_names or []) if t.strip()})
    conn.execute(f'DELETE FROM {join_table} WHERE {id_col}=?', (item_id,))
    for nome in nomes:
        conn.execute('INSERT OR IGNORE INTO tags (nome) VALUES (?)', (nome,))
        tag_id = conn.execute('SELECT id FROM tags WHERE nome=? COLLATE NOCASE', (nome,)).fetchone()['id']
        conn.execute(f'INSERT OR IGNORE INTO {join_table} ({id_col},tag_id) VALUES (?,?)', (item_id, tag_id))

def _tags_map(conn, join_table, id_col, item_ids):
    """Retorna {item_id: [nomes de tag]} para os ids informados."""
    if not item_ids: return {}
    qs = ','.join('?' * len(item_ids))
    rows = conn.execute(
        f'''SELECT j.{id_col} AS iid, t.nome FROM {join_table} j
            JOIN tags t ON j.tag_id=t.id WHERE j.{id_col} IN ({qs})
            ORDER BY t.nome''', item_ids
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r['iid'], []).append(r['nome'])
    return out

# ── Segurança ─────────────────────────────────────────────────────────────────

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return f'{salt}:{dk.hex()}'

def _verify_password(password, stored):
    try:
        salt, _ = stored.split(':', 1)
        return secrets.compare_digest(_hash_password(password, salt), stored)
    except Exception:
        return False

# ── Rate limit de login ─────────────────────────────────────────────────────
# ponytail: dict em memória, sem lock — pior caso é uma contagem levemente
# imprecisa sob concorrência, não uma falha; zera a cada reinício do servidor.
LOGIN_MAX_ATTEMPTS   = 5
LOGIN_LOCKOUT_WINDOW = 300   # 5 min — janela deslizante de tentativas falhas
_login_failures = {}   # username (lower) -> [timestamps de tentativas falhas]

def _login_rate_limited(username):
    key = (username or '').strip().lower()
    now = time.time()
    attempts = [t for t in _login_failures.get(key, []) if now - t < LOGIN_LOCKOUT_WINDOW]
    _login_failures[key] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS

def _record_login_failure(username):
    key = (username or '').strip().lower()
    _login_failures.setdefault(key, []).append(time.time())

def _clear_login_failures(username):
    _login_failures.pop((username or '').strip().lower(), None)

def create_session(user_id):
    token = secrets.token_urlsafe(32)
    expires = time.time() + SESSION_TTL
    with get_db() as conn:
        conn.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
        conn.execute('INSERT INTO sessions (token,user_id,expires) VALUES (?,?,?)',
                     (token, user_id, expires))
    return token

def get_session(token):
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            '''SELECT s.token, s.user_id, s.expires,
                      u.nome, u.username, u.cargo, u.matricula, u.admin, u.ativo
               FROM sessions s JOIN usuarios u ON u.id=s.user_id
               WHERE s.token=? AND s.expires>? AND u.ativo=1''',
            (token, time.time())
        ).fetchone()
    return dict(row) if row else None

def delete_session(token):
    with get_db() as conn:
        conn.execute('DELETE FROM sessions WHERE token=?', (token,))

def renew_session(token):
    with get_db() as conn:
        conn.execute('UPDATE sessions SET expires=? WHERE token=?',
                     (time.time() + SESSION_TTL, token))

def active_sessions():
    with get_db() as conn:
        return conn.execute('SELECT COUNT(*) FROM sessions WHERE expires>?', (time.time(),)).fetchone()[0]

def _check_shutdown():
    """Encerra o servidor quando não há mais sessões ativas (último logout).
    No modo servidor contínuo (_modo_servidor=True), apenas faz backup sem encerrar."""
    global _backup_pos_sess
    if _modo_servidor:
        # Modo servidor: backup uma única vez após última sessão encerrada
        if _had_session and active_sessions() == 0 and not _backup_pos_sess:
            _backup_pos_sess = True
            cfg = _get_backup_cfg()
            if cfg['enabled']:
                print('\nÚltima sessão encerrada. Executando backup automático...')
                _do_json_backup(cfg)
                _do_db_backup(cfg)
        return
    if not _had_session:
        return
    if active_sessions() > 0:
        return
    print('\nÚltima sessão encerrada. Executando backup e encerrando servidor...')
    cfg = _get_backup_cfg()
    if cfg['enabled']:
        _do_json_backup(cfg)
        _do_db_backup(cfg)
    os._exit(0)

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class SGCAHandler(http.server.SimpleHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def end_headers(self):
        # SGCA.html/JS mudam com frequência entre versões; sem isso o navegador
        # pode servir do cache sem revalidar com o servidor (heurística por Last-Modified).
        if self.command == 'GET' and urlparse(self.path).path.rstrip('/').endswith(('.html', '.js', '.css')):
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        p  = parsed.path.rstrip('/')
        qs = parse_qs(parsed.query)

        if p == '/health':
            self._json(200, {'ok': True, 'modo_servidor': _modo_servidor})
        elif p == '/api/public/org-info':
            try:
                with get_db() as conn:
                    rows = conn.execute(
                        "SELECT key,value FROM sys_settings WHERE key IN ('orgao','municipio','cnpj_orgao')"
                    ).fetchall()
                info = {r['key']: r['value'] for r in rows}
                self._json(200, info)
            except Exception:
                self._json(200, {})
        elif p == '/api/public/last-backup':
            try:
                with get_db() as conn:
                    row = conn.execute("SELECT value FROM sys_settings WHERE key='auto_backup_last'").fetchone()
                self._json(200, {'ts': row['value'] if row else None})
            except Exception:
                self._json(200, {'ts': None})
        elif p == '/api/auth/logout':
            # Aceita token via query string para suportar sendBeacon
            tok = qs.get('token', [None])[0] or self._token()
            delete_session(tok)
            self._json(200, {'ok': True})
            threading.Thread(target=_check_shutdown, daemon=True).start()
        elif p.startswith('/cnpj/'):
            self._proxy_cnpj(p[6:].strip('/'))
        elif p.startswith('/api/'):
            s = self._auth()
            if s: self._route_get(p, qs, s)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        p = parsed.path.rstrip('/')

        if p == '/api/auth/login':
            self._login(self._body())
            return

        # Logout via beacon (sem Authorization header — lê token do query string)
        if p == '/api/auth/logout':
            qs_tok = parse_qs(parsed.query).get('token', [None])[0]
            delete_session(qs_tok or self._token())
            self._json(200, {'ok': True})
            threading.Thread(target=_check_shutdown, daemon=True).start()
            return

        if p == '/send-email':
            if not get_session(self._token()):
                self._json(401, {'error': 'Não autenticado'}); return
            try:
                self._send_email(json.loads(self._body()))
                self._json(200, {'ok': True})
            except Exception as e:
                self._json(500, {'ok': False, 'error': str(e)})
            return

        s = self._auth()
        if not s: return
        # BUG (corrigido): _upload_file_direct/_create_signature_upload leem o corpo
        # de novo via self.rfile.read() para multipart — ler aqui também esvaziaria o
        # socket e travaria a segunda leitura (ConnectionResetError sob curl -F, e
        # potencialmente sob navegador também). Multipart é lido só pelo handler.
        ct = self.headers.get('Content-Type', '')
        body = b'' if 'multipart/form-data' in ct else self._body()
        self._route_post(p, body, s)

    def do_PUT(self):
        p = urlparse(self.path).path.rstrip('/')
        s = self._auth()
        if not s: return
        self._route_put(p, self._body(), s)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        p = parsed.path.rstrip('/')
        qs = parse_qs(parsed.query)
        s = self._auth()
        if not s: return
        self._route_delete(p, qs, s)

    # ── Roteamento ────────────────────────────────────────────────────────────

    def _route_get(self, p, qs, s):
        def qp(k, d=None): v = qs.get(k); return v[0] if v else d

        # Auth
        if p == '/api/auth/logout':
            tok = qs.get('token', [None])[0] or self._token()
            delete_session(tok)
            self._json(200, {'ok': True})
            threading.Thread(target=_check_shutdown, daemon=True).start()

        elif p == '/api/auth/ping':
            renew_session(self._token())
            self._json(200, {'ok': True})

        elif p == '/api/auth/me':
            self._json(200, self._user_dict(s))

        # Fornecedores
        elif p == '/api/fornecedores':
            self._list_fornecedores(qs)
        elif re.fullmatch(r'/api/fornecedores/[^/]+', p):
            self._get_fornecedor(p.split('/')[-1])

        # Contratos
        elif p == '/api/contratos':
            self._list_contratos(qs)
        elif re.fullmatch(r'/api/contratos/[^/]+', p):
            self._get_contrato(p.split('/')[-1])

        # Atas de Registro de Preços
        elif p == '/api/atas':
            self._list_atas(qs)
        elif re.fullmatch(r'/api/atas/[^/]+', p):
            self._get_ata(p.split('/')[-1])

        # Etiquetas
        elif p == '/api/tags':
            self._list_tags()

        # Auditoria
        # Sem restrição de admin: também usado pelo histórico de alterações por
        # campo, acessível a qualquer usuário logado. A tela "Auditoria" do menu
        # é que fica restrita a admin, só no frontend.
        elif p == '/api/audit':
            page = int(qp('page', 1)); per = min(int(qp('per', 50)), 2000)
            q         = (qp('q') or '').strip()
            tipo      = qp('tipo') or ''
            de        = qp('de') or ''
            ate       = qp('ate') or ''
            processId = qp('processId') or qp('process_id') or ''
            where, params = [], []
            if q:    where.append('(user_nome LIKE ? OR detail LIKE ?)'); params += [f'%{q}%', f'%{q}%']
            if tipo: where.append('type=?'); params.append(tipo)
            if de:   where.append('ts >= ?'); params.append(de)
            if ate:  where.append('ts <= ?'); params.append(ate + 'T23:59:59')
            if processId: where.append('process_id=?'); params.append(processId)
            w = ('WHERE ' + ' AND '.join(where)) if where else ''
            with get_db() as conn:
                total = conn.execute(f'SELECT COUNT(*) FROM audit_global {w}', params).fetchone()[0]
                rows  = conn.execute(
                    f'SELECT * FROM audit_global {w} ORDER BY ts DESC LIMIT ? OFFSET ?',
                    params + [per, (page-1)*per]
                ).fetchall()
            self._json(200, {'total': total, 'page': page, 'per': per, 'items': [dict(r) for r in rows]})

        # Configurações do sistema
        elif p == '/api/settings':
            # brasao_dataurl fica de fora: pode ter alguns MB (imagem em base64) e tem
            # endpoint dedicado (/api/settings/brasao) — incluí-lo aqui deixava essa
            # rota lenta o bastante para, sob a sessão de 15s, ocasionalmente 401ar
            # durante a rajada de requisições do login e derrubar a sincronização.
            with get_db() as conn:
                rows = conn.execute("SELECT key,value FROM sys_settings WHERE key != 'brasao_dataurl'").fetchall()
            result = {r['key']: r['value'] for r in rows}
            print(f"  [SETTINGS] GET /api/settings de {s.get('nome') or s.get('user_id')} — chaves retornadas: {sorted(result.keys())}", flush=True)
            self._json(200, result)

        elif p in ('/api/settings/brasao', '/api/settings/brasao/'):
            with get_db() as conn:
                row = conn.execute("SELECT value FROM sys_settings WHERE key='brasao_dataurl'").fetchone()
            self._json(200, {'brasao_dataurl': row['value'] if row else ''})

        # Usuários (admin)
        elif p == '/api/usuarios':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            with get_db() as conn:
                rows = conn.execute(
                    'SELECT id,username,nome,cargo,matricula,admin,ativo,criado_em FROM usuarios'
                ).fetchall()
            self._json(200, [dict(r) for r in rows])

        # Backup
        elif p == '/api/backup':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._export_backup()

        elif p == '/api/backup/db':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            import tempfile as _tf
            tmp = _tf.NamedTemporaryFile(suffix='.db', delete=False)
            tmp.close()
            try:
                with sqlite3.connect(DB_PATH) as src, sqlite3.connect(tmp.name) as bk:
                    src.backup(bk)
                with open(tmp.name, 'rb') as f:
                    data_bytes = f.read()
                name = time.strftime('DB_SGCA_BACKUP_%Y-%m-%d_%H-%M-%S.db')
                self.send_response(200); self._cors()
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(data_bytes)))
                self.send_header('Content-Disposition', f'attachment; filename="{name}"')
                self.end_headers()
                self.wfile.write(data_bytes)
            finally:
                try: os.remove(tmp.name)
                except: pass

        elif p == '/api/backups/cfg':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._json(200, _get_backup_cfg())

        elif p == '/api/dialog/folder':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            global _watchdog_paused
            _watchdog_paused = True
            try:
                import subprocess as _sp
                ps_cmd = (
                    'Add-Type -AssemblyName System.Windows.Forms;'
                    '$d=New-Object System.Windows.Forms.FolderBrowserDialog;'
                    '$d.Description="Selecione a pasta de backup do SGCA";'
                    '$d.ShowNewFolderButton=$true;'
                    'if($d.ShowDialog()-eq"OK"){Write-Output $d.SelectedPath}'
                )
                r = _sp.run(['powershell', '-Sta', '-WindowStyle', 'Hidden', '-Command', ps_cmd],
                            capture_output=True, text=True, timeout=120)
                path = r.stdout.strip()
                self._json(200, {'path': path or None})
            except Exception as e:
                self._json(500, {'error': str(e)})
            finally:
                _watchdog_paused = False

        elif p == '/api/backups/db':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            cfg = _get_backup_cfg()
            bdir = cfg['path']
            files = sorted(
                (f for f in os.listdir(bdir) if f.startswith('DB_SGCA_BACKUP_') and f.endswith('.db')),
                reverse=True
            ) if os.path.isdir(bdir) else []
            def _parse_ts(f):
                # DB_SGCA_BACKUP_2026-06-27_20-35-41.db → 2026-06-27T20:35:41
                d = f[15:25]; t = f[26:34].replace('-', ':')
                return f'{d}T{t}'
            items = [{'name': f, 'size': os.path.getsize(os.path.join(bdir, f)),
                      'ts': _parse_ts(f)} for f in files]
            with get_db() as conn:
                last_row = conn.execute("SELECT value FROM sys_settings WHERE key='auto_backup_last'").fetchone()
            last_backup = last_row['value'] if last_row else None
            self._json(200, {'items': items, 'path': bdir, 'cfg': cfg, 'last_backup': last_backup})

        elif p.startswith('/api/backups/db/download'):
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            name = parse_qs(parsed.query).get('name', [None])[0]
            if not name or not name.startswith('DB_SGCA_BACKUP_') or not name.endswith('.db') or '/' in name or '\\' in name:
                self._json(400, {'error': 'Nome inválido'}); return
            cfg = _get_backup_cfg()
            fp = os.path.join(cfg['path'], name)
            if not os.path.exists(fp): self._json(404, {'error': 'Arquivo não encontrado'}); return
            with open(fp, 'rb') as f: data_bytes = f.read()
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(data_bytes)))
            self.send_header('Content-Disposition', f'attachment; filename="{name}"')
            self.end_headers(); self.wfile.write(data_bytes)

        else:
            self._json(404, {'error': 'Rota não encontrada'})

    def _route_post(self, p, body, s):
        data = self._parse_json(body)

        if p == '/api/auth/logout':
            delete_session(self._token())
            self._json(200, {'ok': True})
            threading.Thread(target=_check_shutdown, daemon=True).start()

        elif p == '/api/fornecedores':
            self._create_fornecedor(data)

        elif p == '/api/contratos':
            self._create_contrato(data, s)

        elif re.fullmatch(r'/api/contratos/[^/]+/aditivos', p):
            self._add_aditivo(p.split('/')[3], data, s)

        elif p == '/api/atas':
            self._create_ata(data, s)

        elif re.fullmatch(r'/api/atas/[^/]+/itens', p):
            self._add_ata_item(p.split('/')[3], data, s)

        elif p == '/api/audit':
            self._add_audit(data, s)

        elif p == '/api/audit/bulk':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._add_audit_bulk(data)

        elif p in ('/api/settings', '/api/settings/'):
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._save_settings(data)

        elif p == '/api/usuarios':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._create_user(data)

        elif p == '/api/backups/db/now':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            name = _do_db_backup()
            self._json(200, {'ok': bool(name), 'name': name})

        elif p == '/api/backup/restore':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._restore_backup(data)

        elif p == '/api/backups/db/restore':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._restore_db_backup(body)

        else:
            self._json(404, {'error': 'Rota não encontrada'})

    def _route_put(self, p, body, s):
        data = self._parse_json(body)

        if re.fullmatch(r'/api/fornecedores/[^/]+/restore', p):
            self._restore_fornecedor(p.split('/')[-2])
        elif re.fullmatch(r'/api/contratos/[^/]+/restore', p):
            self._restore_contrato(p.split('/')[-2])
        elif re.fullmatch(r'/api/atas/[^/]+/restore', p):
            self._restore_ata(p.split('/')[-2])
        elif re.fullmatch(r'/api/fornecedores/[^/]+', p):
            self._update_fornecedor(p.split('/')[-1], data)
        elif re.fullmatch(r'/api/contratos/[^/]+', p):
            self._update_contrato(p.split('/')[-1], data, s)
        elif re.fullmatch(r'/api/atas/[^/]+', p):
            self._update_ata(p.split('/')[-1], data, s)
        elif re.fullmatch(r'/api/atas/[^/]+/itens/[^/]+', p):
            self._update_ata_item(p.split('/')[-3], p.split('/')[-1], data, s)
        elif p in ('/api/settings', '/api/settings/'):
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._save_settings(data)
        elif p in ('/api/settings/org', '/api/settings/org/'):
            # Dados de Organização: qualquer usuário autenticado pode salvar (não é config administrativa)
            allowed = {'orgao', 'municipio', 'aut_nome', 'aut_cargo', 'site_oficial',
                       'diario_url', 'cnpj_orgao', 'codigo_ibge', 'uf'}
            print(f"  [SETTINGS] PUT /api/settings/org recebido de {s.get('nome') or s.get('user_id')} (admin={s['admin']})", flush=True)
            self._save_settings({k: v for k, v in data.items() if k in allowed})
        elif p in ('/api/settings/brasao', '/api/settings/brasao/'):
            # Brasão customizado (data URL base64): qualquer usuário autenticado pode salvar.
            # Bypassa o "vazio nunca sobrescreve" de _save_settings() — aqui vazio É o
            # sinal explícito de "remover o brasão customizado", não um formulário em branco.
            dataurl = data.get('brasao_dataurl', '')
            with get_db() as conn:
                if dataurl:
                    conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', ('brasao_dataurl', dataurl))
                else:
                    conn.execute("DELETE FROM sys_settings WHERE key='brasao_dataurl'")
            print(f"  [SETTINGS] PUT /api/settings/brasao de {s.get('nome') or s.get('user_id')} — {'removido' if not dataurl else f'{len(dataurl)} bytes'}", flush=True)
            self._json(200, {'ok': True})
        elif p in ('/api/settings/smtp', '/api/settings/smtp/'):
            # Config SMTP: sensível (inclui senha), restrita a admin
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            allowed = {'smtp_host', 'smtp_port', 'smtp_secure', 'smtp_require_tls',
                       'smtp_ignore_ssl', 'smtp_user', 'smtp_pass', 'smtp_from_name', 'smtp_to'}
            # _save_settings() já ignora valores vazios, então smtp_pass em branco preserva a senha salva
            self._save_settings({k: v for k, v in data.items() if k in allowed})
        elif re.fullmatch(r'/api/usuarios/[^/]+', p):
            uid = int(p.split('/')[-1])
            if not s['admin']:
                if uid != s['user_id']:
                    self._json(403, {'error': 'Acesso restrito'}); return
                # ponytail: não-admin só pode trocar a própria senha
                data = {k: data[k] for k in ('password', 'old_password') if k in data}
            self._update_user(uid, data, s)
        else:
            self._json(404, {'error': 'Rota não encontrada'})

    def _route_delete(self, p, qs, s):
        purge = qs.get('purge', [None])[0] == '1'

        if re.fullmatch(r'/api/fornecedores/[^/]+', p):
            fid = p.split('/')[-1]
            if purge:
                if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
                with get_db() as conn:
                    conn.execute('DELETE FROM fornecedores WHERE id=?', (fid,))
            else:
                with get_db() as conn:
                    conn.execute('UPDATE fornecedores SET deleted_at=? WHERE id=?', (_now(), fid))
            self._json(200, {'ok': True})

        elif re.fullmatch(r'/api/contratos/[^/]+/aditivos/[^/]+', p):
            cid, aid = p.split('/')[3], p.split('/')[5]
            self._remove_aditivo(cid, aid, s)

        elif re.fullmatch(r'/api/contratos/[^/]+', p):
            cid = p.split('/')[-1]
            if purge:
                if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
                with get_db() as conn:
                    conn.execute('DELETE FROM contratos WHERE id=?', (cid,))
            else:
                with get_db() as conn:
                    conn.execute('UPDATE contratos SET deleted_at=? WHERE id=?', (_now(), cid))
            self._json(200, {'ok': True})

        elif re.fullmatch(r'/api/atas/[^/]+/itens/[^/]+', p):
            aid, iid = p.split('/')[3], p.split('/')[5]
            self._remove_ata_item(aid, iid, s)

        elif re.fullmatch(r'/api/atas/[^/]+', p):
            aid = p.split('/')[-1]
            if purge:
                if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
                with get_db() as conn:
                    conn.execute('DELETE FROM atas WHERE id=?', (aid,))
            else:
                with get_db() as conn:
                    conn.execute('UPDATE atas SET deleted_at=? WHERE id=?', (_now(), aid))
            self._json(200, {'ok': True})

        elif re.fullmatch(r'/api/usuarios/[^/]+', p):
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            uid = int(p.split('/')[-1])
            if uid == s['user_id']:
                self._json(400, {'error': 'Não é possível excluir o próprio usuário'}); return
            with get_db() as conn:
                conn.execute('DELETE FROM usuarios WHERE id=?', (uid,))
            self._json(200, {'ok': True})

        elif p == '/api/fornecedores/all':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            with get_db() as conn:
                conn.execute('DELETE FROM fornecedores')
            self._json(200, {'ok': True})

        elif p == '/api/audit/all':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            with get_db() as conn:
                conn.execute('DELETE FROM audit_global')
            self._json(200, {'ok': True})

        elif p == '/api/wipe':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            with get_db() as conn:
                conn.execute('DELETE FROM fornecedores')
                conn.execute('DELETE FROM contratos')
                conn.execute('DELETE FROM atas')
                conn.execute('DELETE FROM audit_global')
            self._json(200, {'ok': True})

        else:
            self._json(404, {'error': 'Rota não encontrada'})

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _token(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '): return auth[7:]
        qs_tok = parse_qs(urlparse(self.path).query).get('token', [None])[0]
        return qs_tok

    def _auth(self):
        s = get_session(self._token())
        if not s:
            self._json(401, {'error': 'Não autenticado'})
        return s

    def _user_dict(self, s):
        return {
            'id': s['user_id'], 'username': s['username'], 'nome': s['nome'],
            'cargo': s.get('cargo'), 'matricula': s.get('matricula'),
            'admin': bool(s['admin'])
        }

    def _login(self, body):
        try:
            data = json.loads(body)
            username = data.get('username', '').strip()
            password = data.get('password', '')
        except Exception:
            self._json(400, {'error': 'JSON inválido'}); return

        if _login_rate_limited(username):
            self._json(429, {'error': 'Muitas tentativas de login. Aguarde alguns minutos e tente novamente.'}); return

        with get_db() as conn:
            row = conn.execute(
                'SELECT * FROM usuarios WHERE username=? COLLATE NOCASE AND ativo=1', (username,)
            ).fetchone()

        if not row or not _verify_password(password, row['senha_hash']):
            _record_login_failure(username)
            self._json(401, {'error': 'Usuário ou senha incorretos'}); return

        _clear_login_failures(username)
        global _had_session, _backup_pos_sess
        _had_session = True
        _backup_pos_sess = False  # nova sessão — permite backup ao próximo logout
        token = create_session(row['id'])
        self._json(200, {
            'token': token,
            'user': {
                'id': row['id'], 'username': row['username'], 'nome': row['nome'],
                'cargo': row['cargo'], 'matricula': row['matricula'], 'admin': bool(row['admin'])
            }
        })

    # ── Fornecedores ──────────────────────────────────────────────────────────

    def _list_fornecedores(self, qs):
        def qp(k, d=None): v = qs.get(k); return v[0] if v else d
        q    = qp('q', '')
        page = int(qp('page', 1))
        per     = min(int(qp('per', 500)), 2000)
        trash   = qp('trash') == '1'

        where, params = [], []
        where.append('deleted_at IS NOT NULL' if trash else 'deleted_at IS NULL')
        if q:
            where.append('(razao_social LIKE ? OR cnpj LIKE ?)')
            params += [f'%{q}%', f'%{q}%']

        wc = ('WHERE ' + ' AND '.join(where)) if where else ''
        order = 'deleted_at DESC' if trash else 'razao_social ASC'
        with get_db() as conn:
            total = conn.execute(f'SELECT COUNT(*) FROM fornecedores {wc}', params).fetchone()[0]
            rows  = conn.execute(
                f'SELECT data,deleted_at FROM fornecedores {wc} ORDER BY {order} LIMIT ? OFFSET ?',
                params + [per, (page-1)*per]
            ).fetchall()
        items = []
        for r in rows:
            item = json.loads(r['data'])
            item['deletedAt'] = r['deleted_at']
            items.append(item)
        self._json(200, {'total': total, 'items': items})

    def _get_fornecedor(self, fid):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM fornecedores WHERE id=?', (fid,)).fetchone()
        if not row: self._json(404, {'error': 'Fornecedor não encontrado'}); return
        self._json(200, json.loads(row['data']))

    def _create_fornecedor(self, data):
        fid = data.get('id') or str(uuid.uuid4())
        data['id'] = fid
        data.setdefault('updatedAt', _now())
        with get_db() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO fornecedores (id,data,cnpj,razao_social,updated_at) VALUES (?,?,?,?,?)',
                (fid, json.dumps(data, ensure_ascii=False),
                 data.get('cnpj'), data.get('razao') or data.get('razao_social'), data['updatedAt'])
            )
        self._json(200, data)

    def _update_fornecedor(self, fid, data):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM fornecedores WHERE id=?', (fid,)).fetchone()
            if not row:
                self._create_fornecedor({**data, 'id': fid}); return
            existing = json.loads(row['data'])
            existing.update(data)
            existing['updatedAt'] = _now()
            conn.execute(
                'UPDATE fornecedores SET data=?,cnpj=?,razao_social=?,updated_at=? WHERE id=?',
                (json.dumps(existing, ensure_ascii=False),
                 existing.get('cnpj'), existing.get('razao') or existing.get('razao_social'),
                 existing['updatedAt'], fid)
            )
        self._json(200, existing)

    def _restore_fornecedor(self, fid):
        with get_db() as conn:
            conn.execute('UPDATE fornecedores SET deleted_at=NULL WHERE id=?', (fid,))
        self._json(200, {'ok': True})

    # ── Contratos ─────────────────────────────────────────────────────────────
    # Mesmo padrão de fornecedores: registro completo em JSON na coluna `data`,
    # com colunas soltas só para filtro/ordenação. Aditivos e apostilamentos
    # ficam embutidos como array `aditivos` dentro do próprio JSON do contrato —
    # não precisam de tabela própria.

    def _list_contratos(self, qs):
        def qp(k, d=None): v = qs.get(k); return v[0] if v else d
        q          = qp('q', '')
        status     = qp('status', '')
        fornecedor = qp('fornecedor', '')
        fiscal     = qp('fiscal', '')
        tag        = qp('tag', '')
        page   = int(qp('page', 1))
        per    = min(int(qp('per', 500)), 2000)
        trash  = qp('trash') == '1'

        where, params = [], []
        where.append('deleted_at IS NOT NULL' if trash else 'deleted_at IS NULL')
        if q:
            # 'numero' só existe dentro do JSON (data), não é coluna da tabela
            fts_q = _fts_match_query(q) if FTS_AVAILABLE else None
            if fts_q:
                where.append('''(rowid IN (SELECT rowid FROM contratos_fts WHERE contratos_fts MATCH ?)
                                  OR json_extract(data, '$.numero') LIKE ?)''')
                params += [fts_q, f'%{q}%']
            else:
                where.append("(objeto LIKE ? OR json_extract(data, '$.numero') LIKE ?)")
                params += [f'%{q}%', f'%{q}%']
        if status:
            where.append('status=?'); params.append(status)
        if fornecedor:
            where.append('fornecedor_id=?'); params.append(fornecedor)
        if fiscal:
            where.append("json_extract(data, '$.fiscalNome')=?"); params.append(fiscal)
        if tag:
            where.append('id IN (SELECT ct.contrato_id FROM contrato_tags ct JOIN tags t ON ct.tag_id=t.id WHERE t.nome=? COLLATE NOCASE)')
            params.append(tag)

        wc = ('WHERE ' + ' AND '.join(where)) if where else ''
        order = 'deleted_at DESC' if trash else 'vigencia_final ASC'
        with get_db() as conn:
            total = conn.execute(f'SELECT COUNT(*) FROM contratos {wc}', params).fetchone()[0]
            rows  = conn.execute(
                f'SELECT id,data,deleted_at FROM contratos {wc} ORDER BY {order} LIMIT ? OFFSET ?',
                params + [per, (page-1)*per]
            ).fetchall()
            tags_map = _tags_map(conn, 'contrato_tags', 'contrato_id', [r['id'] for r in rows])
        items = []
        for r in rows:
            item = json.loads(r['data'])
            item['deletedAt'] = r['deleted_at']
            item['tags'] = tags_map.get(r['id'], [])
            items.append(item)
        self._json(200, {'total': total, 'items': items})

    def _get_contrato(self, cid):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM contratos WHERE id=?', (cid,)).fetchone()
            if not row: self._json(404, {'error': 'Contrato não encontrado'}); return
            tags = _tags_map(conn, 'contrato_tags', 'contrato_id', [cid]).get(cid, [])
        item = json.loads(row['data']); item['tags'] = tags
        self._json(200, item)

    def _save_contrato_row(self, conn, data):
        conn.execute(
            '''INSERT OR REPLACE INTO contratos
               (id,data,objeto,status,fornecedor_id,vigencia_final,valor_global,
                created_at,updated_at,created_by,deleted_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,
                       (SELECT deleted_at FROM contratos WHERE id=?))''',
            (data['id'], json.dumps(data, ensure_ascii=False),
             data.get('objeto'), data.get('status', 'vigente'), data.get('fornecedorId'),
             data.get('vigenciaFinal'), _float(data.get('valorGlobal')),
             data.get('createdAt'), data['updatedAt'], data.get('_createdBy'), data['id'])
        )

    def _create_contrato(self, data, s):
        cid = data.get('id') or str(uuid.uuid4())
        data['id'] = cid
        now = _now()
        data.setdefault('createdAt', now)
        data['updatedAt'] = now
        data.setdefault('aditivos', [])
        data.setdefault('valorOriginal', data.get('valorGlobal'))
        data['_createdBy'] = s['user_id']
        with get_db() as conn:
            self._save_contrato_row(conn, data)
            if 'tags' in data: _sync_tags(conn, 'contrato_tags', 'contrato_id', cid, data['tags'])
        self._json(200, data)

    def _update_contrato(self, cid, data, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM contratos WHERE id=?', (cid,)).fetchone()
            if not row:
                self._create_contrato({**data, 'id': cid}, s); return
            existing = json.loads(row['data'])
            existing.update(data)
            existing['updatedAt'] = _now()
            self._save_contrato_row(conn, existing)
            if 'tags' in data: _sync_tags(conn, 'contrato_tags', 'contrato_id', cid, data['tags'])
        self._json(200, existing)

    def _restore_contrato(self, cid):
        with get_db() as conn:
            conn.execute('UPDATE contratos SET deleted_at=NULL WHERE id=?', (cid,))
        self._json(200, {'ok': True})

    def _add_aditivo(self, cid, data, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM contratos WHERE id=?', (cid,)).fetchone()
            if not row: self._json(404, {'error': 'Contrato não encontrado'}); return
            contrato = json.loads(row['data'])
            data['id'] = data.get('id') or str(uuid.uuid4())
            data.setdefault('createdAt', _now())
            contrato.setdefault('aditivos', []).append(data)
            # Recalcula vigência final e valor global a partir do histórico de aditivos
            if data.get('tipo') == 'prazo' and data.get('novaVigenciaFinal'):
                contrato['vigenciaFinal'] = data['novaVigenciaFinal']
            if data.get('valorVariacao'):
                valor_original = _float(contrato.get('valorOriginal')) or _float(contrato.get('valorGlobal'))
                contrato['valorGlobal'] = (_float(contrato.get('valorGlobal')) or 0) + _float(data['valorVariacao'])
                if valor_original:
                    acumulado = sum(_float(a.get('valorVariacao')) or 0 for a in contrato['aditivos'])
                    contrato['percentualAcumulado'] = round(abs(acumulado) / valor_original * 100, 2)
            contrato['updatedAt'] = _now()
            self._save_contrato_row(conn, contrato)
        self._json(200, contrato)

    def _remove_aditivo(self, cid, aid, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM contratos WHERE id=?', (cid,)).fetchone()
            if not row: self._json(404, {'error': 'Contrato não encontrado'}); return
            contrato = json.loads(row['data'])
            contrato['aditivos'] = [a for a in contrato.get('aditivos', []) if a.get('id') != aid]
            contrato['updatedAt'] = _now()
            self._save_contrato_row(conn, contrato)
        self._json(200, {'ok': True})

    # ── Atas de Registro de Preços ────────────────────────────────────────────
    # Mesmo padrão: itens da ata embutidos como array `itens` dentro do JSON.

    def _list_atas(self, qs):
        def qp(k, d=None): v = qs.get(k); return v[0] if v else d
        q      = qp('q', '')
        status = qp('status', '')
        tag    = qp('tag', '')
        page   = int(qp('page', 1))
        per    = min(int(qp('per', 500)), 2000)
        trash  = qp('trash') == '1'

        where, params = [], []
        where.append('deleted_at IS NOT NULL' if trash else 'deleted_at IS NULL')
        if q:
            where.append('numero LIKE ?'); params.append(f'%{q}%')
        if status:
            where.append('status=?'); params.append(status)
        if tag:
            where.append('id IN (SELECT at.ata_id FROM ata_tags at JOIN tags t ON at.tag_id=t.id WHERE t.nome=? COLLATE NOCASE)')
            params.append(tag)

        wc = ('WHERE ' + ' AND '.join(where)) if where else ''
        order = 'deleted_at DESC' if trash else 'vigencia_final ASC'
        with get_db() as conn:
            total = conn.execute(f'SELECT COUNT(*) FROM atas {wc}', params).fetchone()[0]
            rows  = conn.execute(
                f'SELECT id,data,deleted_at FROM atas {wc} ORDER BY {order} LIMIT ? OFFSET ?',
                params + [per, (page-1)*per]
            ).fetchall()
            tags_map = _tags_map(conn, 'ata_tags', 'ata_id', [r['id'] for r in rows])
        items = []
        for r in rows:
            item = json.loads(r['data'])
            item['deletedAt'] = r['deleted_at']
            item['tags'] = tags_map.get(r['id'], [])
            items.append(item)
        self._json(200, {'total': total, 'items': items})

    def _get_ata(self, aid):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM atas WHERE id=?', (aid,)).fetchone()
            if not row: self._json(404, {'error': 'Ata não encontrada'}); return
            tags = _tags_map(conn, 'ata_tags', 'ata_id', [aid]).get(aid, [])
        item = json.loads(row['data']); item['tags'] = tags
        self._json(200, item)

    def _save_ata_row(self, conn, data):
        conn.execute(
            '''INSERT OR REPLACE INTO atas
               (id,data,numero,status,vigencia_final,created_at,updated_at,created_by,deleted_at)
               VALUES (?,?,?,?,?,?,?,?,
                       (SELECT deleted_at FROM atas WHERE id=?))''',
            (data['id'], json.dumps(data, ensure_ascii=False),
             data.get('numero'), data.get('status', 'vigente'), data.get('vigenciaFinal'),
             data.get('createdAt'), data['updatedAt'], data.get('_createdBy'), data['id'])
        )

    def _create_ata(self, data, s):
        aid = data.get('id') or str(uuid.uuid4())
        data['id'] = aid
        now = _now()
        data.setdefault('createdAt', now)
        data['updatedAt'] = now
        data.setdefault('itens', [])
        data['_createdBy'] = s['user_id']
        with get_db() as conn:
            self._save_ata_row(conn, data)
            if 'tags' in data: _sync_tags(conn, 'ata_tags', 'ata_id', aid, data['tags'])
        self._json(200, data)

    def _update_ata(self, aid, data, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM atas WHERE id=?', (aid,)).fetchone()
            if not row:
                self._create_ata({**data, 'id': aid}, s); return
            existing = json.loads(row['data'])
            existing.update(data)
            existing['updatedAt'] = _now()
            self._save_ata_row(conn, existing)
            if 'tags' in data: _sync_tags(conn, 'ata_tags', 'ata_id', aid, data['tags'])
        self._json(200, existing)

    def _restore_ata(self, aid):
        with get_db() as conn:
            conn.execute('UPDATE atas SET deleted_at=NULL WHERE id=?', (aid,))
        self._json(200, {'ok': True})

    def _list_tags(self):
        with get_db() as conn:
            rows = conn.execute('SELECT nome FROM tags ORDER BY nome').fetchall()
        self._json(200, {'items': [r['nome'] for r in rows]})

    def _add_ata_item(self, aid, data, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM atas WHERE id=?', (aid,)).fetchone()
            if not row: self._json(404, {'error': 'Ata não encontrada'}); return
            ata = json.loads(row['data'])
            data['id'] = data.get('id') or str(uuid.uuid4())
            data.setdefault('quantidadeUtilizada', 0)
            ata.setdefault('itens', []).append(data)
            ata['updatedAt'] = _now()
            self._save_ata_row(conn, ata)
        self._json(200, ata)

    def _update_ata_item(self, aid, iid, data, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM atas WHERE id=?', (aid,)).fetchone()
            if not row: self._json(404, {'error': 'Ata não encontrada'}); return
            ata = json.loads(row['data'])
            for item in ata.get('itens', []):
                if item.get('id') == iid:
                    item.update(data)
                    break
            else:
                self._json(404, {'error': 'Item não encontrado'}); return
            ata['updatedAt'] = _now()
            self._save_ata_row(conn, ata)
        self._json(200, ata)

    def _remove_ata_item(self, aid, iid, s):
        with get_db() as conn:
            row = conn.execute('SELECT data FROM atas WHERE id=?', (aid,)).fetchone()
            if not row: self._json(404, {'error': 'Ata não encontrada'}); return
            ata = json.loads(row['data'])
            ata['itens'] = [i for i in ata.get('itens', []) if i.get('id') != iid]
            ata['updatedAt'] = _now()
            self._save_ata_row(conn, ata)
        self._json(200, {'ok': True})

    # ── Auditoria ─────────────────────────────────────────────────────────────

    def _add_audit(self, data, s=None):
        aid = data.get('id') or str(uuid.uuid4())
        # Compatibilidade com campos antigos do JS (at/ms, evento, usuario, detalhe)
        ts_raw = data.get('ts') or data.get('at')
        if isinstance(ts_raw, (int, float)):
            ts = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts_raw / 1000))
        else:
            ts = ts_raw or _now()
        tipo   = data.get('type')   or data.get('evento')
        detail = data.get('detail') or data.get('detalhe')
        label  = data.get('label')  or data.get('evento')
        # Sempre usa dados da sessão autenticada — ignora user_id/user_nome do body
        user_nome = s['nome']    if s else (data.get('userName') or data.get('user_nome') or data.get('usuario'))
        user_id   = s['user_id'] if s else (data.get('userId')   or data.get('user_id'))
        with get_db() as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO audit_global
                   (id,ts,user_id,user_nome,type,label,detail,process_id,process_obj)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (aid, ts, user_id, user_nome, tipo, label, detail,
                 data.get('processId') or data.get('process_id'),
                 json.dumps(data['processObj']) if data.get('processObj') else data.get('process_obj'))
            )
        self._json(200, {'ok': True})

    def _add_audit_bulk(self, data):
        """Importa uma lista de eventos de auditoria preservando o autor original
        (usado pela sincronização de backup entre agentes — ver _insert_audit_raw)."""
        eventos = data.get('items') if isinstance(data, dict) else data
        if not isinstance(eventos, list):
            self._json(400, {'error': 'Campo "items" deve ser uma lista'}); return
        with get_db() as conn:
            for a in eventos:
                if isinstance(a, dict):
                    _insert_audit_raw(conn, a)
        self._json(200, {'ok': True, 'inseridos': len(eventos)})

    # ── Configurações ─────────────────────────────────────────────────────────

    def _save_settings(self, data):
        # ponytail: string vazia nunca sobrescreve um valor já salvo — evita que um
        # formulário em branco (navegador que nunca carregou os dados) apague a
        # configuração real ao salvar. Para limpar um campo, edite o banco diretamente.
        gravadas, ignoradas = [], []
        with get_db() as conn:
            for key, value in data.items():
                v = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                if v == '':
                    ignoradas.append(key)
                    continue
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (key, v))
                gravadas.append(key)
        print(f'  [SETTINGS] gravadas={gravadas} ignoradas(vazias)={ignoradas}', flush=True)
        if 'auto_backup_keep' in data or 'backup_path' in data:
            _rotate_backups()
        self._json(200, {'ok': True})

    # ── Usuários ──────────────────────────────────────────────────────────────

    def _create_user(self, data):
        nome     = (data.get('nome') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not nome or not username or not password:
            self._json(400, {'error': 'Nome, usuário e senha são obrigatórios'}); return
        if len(password) < 6:
            self._json(400, {'error': 'Senha mínima: 6 caracteres'}); return
        try:
            with get_db() as conn:
                conn.execute(
                    'INSERT INTO usuarios (username,nome,cargo,matricula,senha_hash,admin) VALUES (?,?,?,?,?,?)',
                    (username, nome, data.get('cargo'), data.get('matricula'),
                     _hash_password(password), int(bool(data.get('admin'))))
                )
                uid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            self._json(200, {'id': uid, 'username': username, 'nome': nome})
        except sqlite3.IntegrityError:
            self._json(409, {'error': f'Usuário "{username}" já existe'})

    def _update_user(self, uid, data, s):
        with get_db() as conn:
            if not conn.execute('SELECT 1 FROM usuarios WHERE id=?', (uid,)).fetchone():
                self._json(404, {'error': 'Usuário não encontrado'}); return
            fields, params = [], []
            for col in ('nome', 'cargo', 'matricula'):
                if col in data: fields.append(f'{col}=?'); params.append(data[col])
            if 'admin' in data: fields.append('admin=?'); params.append(int(bool(data['admin'])))
            if 'ativo' in data: fields.append('ativo=?'); params.append(int(bool(data['ativo'])))
            if data.get('password'):
                if len(data['password']) < 6:
                    self._json(400, {'error': 'Senha mínima: 6 caracteres'}); return
                if 'old_password' in data:
                    row = conn.execute('SELECT senha_hash FROM usuarios WHERE id=?', (uid,)).fetchone()
                    if not row or not _verify_password(data['old_password'], row['senha_hash']):
                        self._json(403, {'error': 'Senha atual incorreta'}); return
                fields.append('senha_hash=?'); params.append(_hash_password(data['password']))
            if fields:
                conn.execute(f'UPDATE usuarios SET {",".join(fields)} WHERE id=?', params + [uid])
        self._json(200, {'ok': True})

    # ── Backup ────────────────────────────────────────────────────────────────

    def _export_backup(self):
        backup = _build_backup_payload()
        payload = json.dumps(backup, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Content-Disposition',
                         f'attachment; filename="SIS_SGCA_BACKUP_{time.strftime("%Y-%m-%d_%H-%M-%S")}.json"')
        self.end_headers()
        self.wfile.write(payload)

    def _restore_backup(self, data):
        if not data.get('_sgca'):
            self._json(400, {'error': 'Arquivo não é um backup SGCA válido'}); return
        _do_db_backup()  # backup do atual antes de substituir tudo
        with get_db() as conn:
            conn.execute('DELETE FROM audit_global')
            conn.execute('DELETE FROM fornecedores')
            conn.execute('DELETE FROM contratos')
            conn.execute('DELETE FROM atas')
            conn.commit()

            for f in data.get('fornecedores', []):
                fid = f.get('id') or str(uuid.uuid4())
                f['id'] = fid
                conn.execute(
                    'INSERT OR REPLACE INTO fornecedores (id,data,cnpj,razao_social,updated_at) VALUES (?,?,?,?,?)',
                    (fid, json.dumps(f, ensure_ascii=False),
                     f.get('cnpj'), f.get('razao') or f.get('razao_social'), f.get('updatedAt'))
                )

            for c in data.get('contratos', []):
                c['id'] = c.get('id') or str(uuid.uuid4())
                c.setdefault('updatedAt', c.get('updatedAt') or _now())
                self._save_contrato_row(conn, c)

            for a in data.get('atas', []):
                a['id'] = a.get('id') or str(uuid.uuid4())
                a.setdefault('updatedAt', a.get('updatedAt') or _now())
                self._save_ata_row(conn, a)

            for a in data.get('auditGlobal', []):
                _insert_audit_raw(conn, a)

            for key, value in (data.get('settings') or {}).items():
                v = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (key, v))

        self._json(200, {'ok': True})

    def _restore_db_backup(self, raw_bytes):
        # raw_bytes é o conteúdo bruto do arquivo .db enviado via multipart ou binário
        if len(raw_bytes) < 16 or raw_bytes[:16] != b'SQLite format 3\x00':
            self._json(400, {'error': 'Arquivo não é um banco SQLite válido'}); return
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        try:
            tmp.write(raw_bytes); tmp.close()
            # Valida que o arquivo tem as tabelas esperadas
            with sqlite3.connect(tmp.name) as test_conn:
                tables = {r[0] for r in test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            required = {'fornecedores', 'contratos', 'atas', 'sys_settings'}
            if not required.issubset(tables):
                self._json(400, {'error': 'Banco inválido: tabelas obrigatórias ausentes'}); return
            # Backup do atual antes de restaurar
            _do_db_backup()
            # Substitui o banco atual com o backup via API de backup SQLite (seguro)
            with sqlite3.connect(tmp.name) as src, get_db() as dst:
                src.backup(dst)
            self._json(200, {'ok': True})
        except Exception as e:
            _log.error('Erro ao restaurar banco: %s', e)
            self._json(500, {'error': str(e)})
        finally:
            try: os.remove(tmp.name)
            except: pass

    # ── CNPJ Proxy ────────────────────────────────────────────────────────────

    def _proxy_cnpj(self, digits):
        if not digits.isdigit() or len(digits) != 14:
            self._json(400, {'status': 'ERROR', 'message': 'CNPJ inválido'}); return
        url = f'https://receitaws.com.br/v1/cnpj/{digits}'
        req = urllib.request.Request(url, headers={'User-Agent': 'SGCA/2.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read()
                self.send_response(resp.status)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code); self._cors()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        except Exception as e:
            self._json(502, {'status': 'ERROR', 'message': str(e)})

    # ── E-mail ────────────────────────────────────────────────────────────────

    def _send_email(self, data):
        _send_email_raw(data['smtp'], data['from'], data['to'], data['subject'], data['html'], data.get('text', ''))

    # ── Helpers HTTP ──────────────────────────────────────────────────────────

    def _body(self):
        n = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(n) if n else b''

    def _parse_json(self, body):
        try: return json.loads(body) if body else {}
        except Exception: return {}

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')

    def _json(self, status, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_error(self, request, client_address):
        import traceback
        _log.error('Erro na requisição de %s:\n%s', client_address, traceback.format_exc())

    def log_message(self, fmt, *args): pass

# ── Utilitários ───────────────────────────────────────────────────────────────

def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%S')

def _insert_audit_raw(conn, a):
    """Insere um evento de auditoria preservando autor/id/data originais do payload
    (ao contrário de _add_audit, que sempre carimba o usuário da sessão atual —
    correto para lançar eventos ao vivo, errado para importar histórico de outra
    máquina via restauração/sincronização de backup)."""
    conn.execute(
        '''INSERT OR REPLACE INTO audit_global
           (id,ts,user_id,user_nome,type,label,detail,process_id,process_obj)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (a.get('id') or str(uuid.uuid4()), a.get('ts'),
         a.get('userId') or a.get('user_id'),
         a.get('userName') or a.get('user_nome'),
         a.get('type'), a.get('label'), a.get('detail'),
         a.get('processId') or a.get('process_id'),
         json.dumps(a['processObj']) if a.get('processObj') else a.get('process_obj'))
    )

def _float(v):
    if v is None: return None
    try: return float(str(v).replace(',', '.').replace('R$', '').strip())
    except: return None

def _find_browser():
    for c in [
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
    ]:
        if os.path.isfile(c): return c
    return None

def _send_email_raw(smtp, frm, to, subj, html, plain=''):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subj
    msg['From']    = f"{frm['name']} <{frm['email']}>"
    msg['To']      = to if isinstance(to, str) else ', '.join(to)
    if plain: msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    port = int(smtp.get('port', 587))
    host = smtp['host']
    user = smtp['auth']['user']
    pw   = smtp['auth']['pass']

    ctx = ssl.create_default_context()
    if smtp.get('ignoreSSL'):
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

    if smtp.get('secure'):
        with smtplib.SMTP_SSL(host, port, context=ctx) as s:
            s.login(user, pw); s.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as s:
            s.ehlo()
            if smtp.get('requireTLS', True): s.starttls(context=ctx)
            s.login(user, pw); s.send_message(msg)

def _send_daily_alerts():
    """Resumo diário por e-mail de contratos e atas vencendo.
    Só envia se SMTP estiver configurado no servidor e ainda não tiver enviado hoje."""
    with get_db() as conn:
        cfg = {r['key']: r['value'] for r in conn.execute(
            "SELECT key,value FROM sys_settings WHERE key LIKE 'smtp_%' OR key='alert_email_last_sent'"
        ).fetchall()}
    if not (cfg.get('smtp_host') and cfg.get('smtp_user') and cfg.get('smtp_pass')):
        return
    hoje = time.strftime('%Y-%m-%d')
    if cfg.get('alert_email_last_sent') == hoje:
        return

    agora = time.time()

    def _vencimentos(tabela, rotulo):
        with get_db() as conn:
            rows = conn.execute(f"SELECT data FROM {tabela} WHERE deleted_at IS NULL").fetchall()
        itens = []
        for row in rows:
            try:
                item = json.loads(row['data'])
            except Exception:
                continue
            if item.get('status') in ('encerrado', 'rescindido', 'cancelada'):
                continue
            vig = item.get('vigenciaFinal')
            if not vig:
                continue
            try:
                ts = time.mktime(time.strptime(vig[:10], '%Y-%m-%d'))
                dias = int((ts - agora) / 86400)
                if dias <= 30:
                    nome = item.get('numero') and f"{rotulo} {item['numero']}" or (item.get('objeto') or item.get('id'))
                    itens.append((nome, dias, item.get('fiscalEmail'), item.get('fiscalSubstitutoEmail')))
            except Exception:
                pass
        return itens

    contratos = _vencimentos('contratos', 'Contrato')
    atas      = _vencimentos('atas', 'Ata')

    if not contratos and not atas:
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO sys_settings (key,value) VALUES ('alert_email_last_sent',?)", (hoje,))
        return

    def _linhas(titulo, itens):
        if not itens:
            return ''
        partes = [f'<h3>{titulo}</h3><ul>'] if titulo else ['<ul>']
        for nome, dias, *_ in sorted(itens, key=lambda x: x[1]):
            txt = f'vencido há {-dias} dia(s)' if dias < 0 else ('vence hoje' if dias == 0 else f'vence em {dias} dia(s)')
            partes.append(f'<li><strong>{html_mod.escape(str(nome))}</strong> — {txt}</li>')
        partes.append('</ul>')
        return ''.join(partes)

    smtp_cfg = {
        'host': cfg['smtp_host'], 'port': cfg.get('smtp_port', 587),
        'secure': cfg.get('smtp_secure') == '1', 'requireTLS': cfg.get('smtp_require_tls') != '0',
        'ignoreSSL': cfg.get('smtp_ignore_ssl') == '1',
        'auth': {'user': cfg['smtp_user'], 'pass': cfg['smtp_pass']},
    }
    frm = {'name': cfg.get('smtp_from_name') or 'SGCA', 'email': cfg['smtp_user']}

    if cfg.get('smtp_to'):
        corpo = f"<p>Resumo automático do SGCA — {hoje}</p>" + _linhas('Contratos', contratos) + _linhas('Atas de Registro de Preços', atas)
        try:
            _send_email_raw(smtp_cfg, frm, cfg['smtp_to'], f'SGCA — Resumo de vencimentos ({hoje})', corpo)
            print(f'  [ALERTAS] E-mail de resumo enviado ({len(contratos)} contrato(s), {len(atas)} ata(s))', flush=True)
        except Exception as e:
            _log.error('Falha ao enviar e-mail de alertas: %s', e)

    # Notifica individualmente o fiscal (titular e substituto) de cada contrato vencendo
    por_fiscal = {}
    for nome, dias, email, email_substituto in contratos:
        if email:
            por_fiscal.setdefault(email, []).append((nome, dias))
        if email_substituto:
            por_fiscal.setdefault(email_substituto, []).append((nome, dias))
    for email, itens in por_fiscal.items():
        corpo_f = (f"<p>Resumo automático do SGCA — {hoje}</p>"
                   f"<p>Contrato(s) sob sua fiscalização com vigência vencendo:</p>" + _linhas('', itens))
        try:
            _send_email_raw(smtp_cfg, frm, email, f'SGCA — Contrato(s) sob sua fiscalização ({hoje})', corpo_f)
            print(f'  [ALERTAS] E-mail enviado ao fiscal {email} ({len(itens)} contrato(s))', flush=True)
        except Exception as e:
            _log.error('Falha ao enviar e-mail ao fiscal %s: %s', email, e)

    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO sys_settings (key,value) VALUES ('alert_email_last_sent',?)", (hoje,))

_last_trash_purge = 0

def _purge_old_trash():
    """Esvazia a lixeira: fornecedores/contratos/atas excluídos há mais de 30 dias."""
    global _last_trash_purge
    _last_trash_purge = time.time()
    limite_iso = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() - 30 * 86400))
    with get_db() as conn:
        for tbl in ('fornecedores', 'contratos', 'atas'):
            conn.execute(f"DELETE FROM {tbl} WHERE deleted_at IS NOT NULL AND deleted_at < ?", (limite_iso,))

def _watchdog():
    # Limpa sessões expiradas a cada 5s e verifica encerramento.
    # Com SESSION_TTL=15s e ping a cada 5s, um browser fechado sem logout
    # causa encerramento do servidor em no máximo ~20 segundos.
    while True:
        time.sleep(5)
        if _watchdog_paused:
            continue
        with get_db() as conn:
            conn.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        _check_shutdown()
        if time.time() - _last_trash_purge > 3600:
            try: _purge_old_trash()
            except Exception as e: _log.error('Erro ao esvaziar lixeira: %s', e)
        try: _send_daily_alerts()
        except Exception as e: _log.error('Erro ao enviar alertas por e-mail: %s', e)

# ── Backup automático do banco ─────────────────────────────────────────────────

def _build_backup_payload():
    with get_db() as conn:
        fornecedores = [json.loads(r['data']) for r in conn.execute('SELECT data FROM fornecedores').fetchall()]
        contratos    = [json.loads(r['data']) for r in conn.execute('SELECT data FROM contratos').fetchall()]
        atas         = [json.loads(r['data']) for r in conn.execute('SELECT data FROM atas').fetchall()]
        audit        = [dict(r) for r in conn.execute('SELECT * FROM audit_global').fetchall()]
        settings     = {r['key']: r['value'] for r in conn.execute('SELECT key,value FROM sys_settings').fetchall()}
    return {
        '_sgca': True, 'version': 5, 'exportedAt': _now(),
        'fornecedores': fornecedores, 'contratos': contratos, 'atas': atas,
        'auditGlobal': audit, 'settings': settings,
    }

def _do_json_backup(cfg=None):
    if cfg is None: cfg = _get_backup_cfg()
    bdir = cfg['path']
    keep = cfg['keep']
    os.makedirs(bdir, exist_ok=True)
    name = time.strftime('SIS_SGCA_BACKUP_%Y-%m-%d_%H-%M-%S.json')
    dst  = os.path.join(bdir, name)
    try:
        backup = _build_backup_payload()
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(backup, f, ensure_ascii=False)
        print(f'Backup JSON automático: {name}')
        return name
    except Exception as e:
        _log.error('Falha no backup JSON automático: %s', e)
        return None

def _rotate_backups(cfg=None):
    if cfg is None: cfg = _get_backup_cfg()
    bdir = cfg['path']
    keep = cfg['keep']
    if not os.path.isdir(bdir): return
    for prefix, ext in [('DB_SGCA_BACKUP_', '.db'), ('SIS_SGCA_BACKUP_', '.json')]:
        files = sorted(f for f in os.listdir(bdir) if f.startswith(prefix) and f.endswith(ext))
        to_delete = files[:-keep] if keep else files
        for old in to_delete:
            fp = os.path.join(bdir, old)
            for attempt in range(6):  # tenta por até ~10s (OneDrive pode manter o arquivo aberto)
                try:
                    os.remove(fp)
                    print(f'Rotação: removido {old}')
                    break
                except PermissionError:
                    if attempt < 5:
                        time.sleep(2)
                    else:
                        _log.error('Falha ao remover backup %s: arquivo bloqueado (OneDrive/antivírus). Remova manualmente.', old)
                except Exception as e:
                    _log.error('Falha ao remover backup %s: %s', old, e)
                    break

def _get_backup_cfg():
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key,value FROM sys_settings WHERE key IN ('backup_path','auto_backup_enabled','auto_backup_keep')"
            ).fetchall()
        cfg = {r['key']: r['value'] for r in rows}
    except Exception:
        cfg = {}
    return {
        'path':    cfg.get('backup_path') or BACKUP_DIR,
        'enabled': cfg.get('auto_backup_enabled', '1') != '0',
        'keep':    max(1, int(cfg.get('auto_backup_keep') or BACKUP_KEEP)),
    }

def _do_db_backup(cfg=None):
    if cfg is None: cfg = _get_backup_cfg()
    bdir = cfg['path']
    keep = cfg['keep']
    os.makedirs(bdir, exist_ok=True)
    name = time.strftime('DB_SGCA_BACKUP_%Y-%m-%d_%H-%M-%S.db')
    dst  = os.path.join(bdir, name)
    try:
        with sqlite3.connect(DB_PATH) as src, sqlite3.connect(dst) as bk:
            src.backup(bk)
        # Registra timestamp do último backup
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO sys_settings (key,value) VALUES ('auto_backup_last',?)", (_now(),))
        print(f'Backup automático: {name}')
        _rotate_backups(cfg)
        return name
    except Exception as e:
        _log.error('Falha no backup automático: %s', e)
        return None

# ── Inicialização ─────────────────────────────────────────────────────────────

init_db()

# Verifica integridade do banco na inicialização
def _check_db_integrity():
    try:
        with get_db() as conn:
            result = conn.execute('PRAGMA integrity_check').fetchone()[0]
            if result != 'ok':
                _log.error('INTEGRITY CHECK FALHOU: %s', result)
                print(f'[AVISO] Banco de dados com problema de integridade: {result}')
            else:
                print('[DB] Integridade verificada: ok')
    except Exception as e:
        _log.error('Erro ao verificar integridade do banco: %s', e)

# ── Seleção de modo ───────────────────────────────────────────────────────────

def _selecionar_modo():
    global _modo_servidor
    print()
    print('  ╔══════════════════════════════════════════════════╗')
    print('  ║   SGCA — Sistema de Gestão de Contratos e Atas    ║')
    print('  ╚══════════════════════════════════════════════════╝')
    print()
    print('  Selecione o modo de operação:')
    print()
    print('  [1] Pessoal   — Uso individual no próprio computador')
    print('                  Abre o app automaticamente no navegador')
    print('                  Encerra quando o último usuário sair')
    print()
    print('  [2] Servidor  — Máquina central / acesso pela rede')
    print('                  Não abre navegador automaticamente')
    print('                  Fica rodando continuamente (Ctrl+C para parar)')
    print()
    print('  [3] Diagnóstico — Verifica rede, porta e firewall')
    print()
    if not sys.stdin.isatty():
        op = '2'
    else:
        while True:
            try:
                op = input('  Opção [1/2/3]: ').strip()
            except (EOFError, KeyboardInterrupt):
                op = '1'
            if op in ('1', '2', '3'):
                break
            print('  Digite 1, 2 ou 3.')
    if op == '3':
        import subprocess as _sp
        diag = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagnostico.py')
        _sp.run([sys.executable, diag])
        sys.exit(0)
    _modo_servidor = (op == '2')
    modo_label = 'SERVIDOR CONTÍNUO' if _modo_servidor else 'PESSOAL'
    print()
    print(f'  Modo: {modo_label}')
    print('  ─────────────────────────────────────────────────')

if __name__ == '__main__':
    _selecionar_modo()
    _check_db_integrity()
    _rotate_backups(_get_backup_cfg())  # limpa excedentes dos backups da sessão anterior
    threading.Thread(target=_watchdog, daemon=True).start()

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('', PORT), SGCAHandler) as httpd:
        print(f'  Servidor: http://localhost:{PORT}')

        if _modo_servidor:
            # Modo servidor: exibe IP da rede e fica rodando sem abrir browser
            import socket as _socket
            try:
                ip_local = _socket.gethostbyname(_socket.gethostname())
            except Exception:
                ip_local = 'desconhecido'
            print(f'  Rede:     http://{ip_local}:{PORT}/SGCA.html')
            print()
            print('  Aguardando conexões... (Ctrl+C para encerrar)')
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print('\n  Encerrando servidor...')
        else:
            # Modo pessoal: abre o app no navegador
            browser = _find_browser()
            if browser:
                threading.Thread(target=httpd.serve_forever, daemon=True).start()
                time.sleep(1)
                profile_dir = PROFILE_DIR
                proc = subprocess.Popen([
                    browser,
                    f'--app=http://localhost:{PORT}/SGCA.html',
                    '--start-maximized',
                    '--disable-background-mode',
                    f'--user-data-dir={profile_dir}',
                ])
                print('  App aberto. Feche a janela do SGCA para encerrar.')
                proc.wait()
                print('  Encerrando servidor...')
                while True: time.sleep(1)
            else:
                print(f'  Chrome/Edge não encontrado. Abra manualmente: http://localhost:{PORT}/SGCA.html')
                httpd.serve_forever()
