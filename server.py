# SGCA v0.27.2 — Servidor local: SQLite, autenticação, REST API, proxy CNPJ/BCB, e-mail SMTP, backup automático
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

import sgx_base   # esqueleto compartilhado da família — ver _esqueleto/README.md

PORT          = int(os.environ.get('SGCA_PORT', 3002))
_BASE         = os.path.dirname(os.path.abspath(__file__))
# SGCA_DATA_DIR: usado pelos testes E2E para isolar banco/uploads/backups do
# sgca.db real sem precisar rodar o servidor a partir de outra pasta (os
# arquivos estáticos como SGCA.html continuam servidos a partir de _BASE).
_DATA_DIR     = os.environ.get('SGCA_DATA_DIR', _BASE)
DB_PATH       = os.path.join(_DATA_DIR, 'sgca.db')
UPLOADS_DIR   = os.path.join(_DATA_DIR, 'uploads')
BACKUP_DIR    = os.path.join(_DATA_DIR, 'backups')
PROFILE_DIR   = os.path.join(_DATA_DIR, 'browser-profile')
LOG_PATH      = os.path.join(_DATA_DIR, 'sgca_errors.log')
BACKUP_KEEP   = 7        # número de backups automáticos mantidos
SESSION_TTL   = 60   # renovado pelo ping a cada 5s (ver comentário em _watchdog mais abaixo)

os.makedirs(_DATA_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH, level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
_log = logging.getLogger('sgca')

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(UPLOADS_DIR, exist_ok=True)

_watchdog_paused  = False   # pausa o watchdog durante diálogos bloqueantes (ex: FolderBrowser)
_had_session      = False   # True após primeiro login; controla quando o backup pós-sessão pode disparar
_backup_pos_sess  = False   # True = backup pós-sessão já executado; aguarda nova sessão para resetar
FTS_AVAILABLE     = False   # True se o SQLite tem FTS5 compilado (setado em init_db)

# ── Banco de dados ────────────────────────────────────────────────────────────
# _ConnAutoClose vem do sgx_base (esqueleto compartilhado da família) — mantido
# como alias de módulo porque o nome é referenciado diretamente em vários pontos
# do arquivo (backup/restore/integrity check), não só dentro de get_db().
_ConnAutoClose = sgx_base.ConnAutoClose

# get_db() fica local (não um valor capturado no import) porque os testes
# reatribuem DB_PATH depois do import (setUpModule isola o banco num dir
# temporário) — get_db() precisa reler esse global a cada chamada, não uma
# closure de DB_PATH.
def get_db():
    return sgx_base.connect_db(DB_PATH)

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
                cpf        TEXT,
                email      TEXT,
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
            CREATE TABLE IF NOT EXISTS arquivos (
                id            TEXT PRIMARY KEY,
                nome_original TEXT NOT NULL,
                nome_disco    TEXT NOT NULL,
                tamanho       INTEGER,
                mime          TEXT,
                uploaded_by   INTEGER REFERENCES usuarios(id),
                uploaded_em   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS signatures (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                cod            TEXT NOT NULL UNIQUE,
                entity_type    TEXT NOT NULL CHECK(entity_type IN ('contrato','ata')),
                entity_id      TEXT NOT NULL,
                arquivo_id     TEXT REFERENCES arquivos(id),
                doc_numero     TEXT,
                doc_objeto     TEXT,
                signer_user_id INTEGER REFERENCES usuarios(id),
                signer_name    TEXT,
                cert_subject   TEXT,
                hash_sha256    TEXT,
                signed_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
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
            CREATE INDEX IF NOT EXISTS idx_sig_entity     ON signatures(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_sig_cod        ON signatures(cod);
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
        # Migração: colunas cpf/email em usuarios (cadastro de dados de contato)
        for col in ('cpf', 'email'):
            try:
                conn.execute(f'ALTER TABLE usuarios ADD COLUMN {col} TEXT')
            except sqlite3.OperationalError:
                pass
        try:
            conn.execute('ALTER TABLE usuarios ADD COLUMN must_change_password INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        _migrar_anexos_dataurl(conn)
        conn.commit()
        # Sessões são descartadas a cada início do servidor (logout automático ao fechar janela)
        conn.execute('DELETE FROM sessions')
        # Cria admin padrão se não houver usuários
        if conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0:
            conn.execute(
                'INSERT INTO usuarios (username,nome,senha_hash,admin,must_change_password) VALUES (?,?,?,1,1)',
                ('admin', 'Administrador', _hash_password('admin123'))
            )
            conn.commit()
            print('Usuário padrão criado: admin / admin123 — troque a senha no primeiro acesso.')

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

def _migrar_anexos_dataurl(conn):
    """Migra anexos armazenados como dataurl embutido no JSON do registro (formato
    antigo, base64 dentro do próprio blob) para a tabela arquivos + disco, no mesmo
    padrão do SGCD/SGDP. Idempotente: só mexe em entradas sem arquivo_id ainda."""
    for tabela, campo_pl, campo_sg in (('contratos', 'anexosContrato', 'anexoContrato'),
                                        ('atas', 'anexosAta', 'anexoAta')):
        rows = conn.execute(f"SELECT id, data FROM {tabela} WHERE data LIKE '%dataurl%'").fetchall()
        for row in rows:
            item = json.loads(row['data'])
            anexos = item.get(campo_pl) or ([item[campo_sg]] if item.get(campo_sg) else [])
            if not anexos: continue
            changed = False
            for anexo in anexos:
                if not anexo.get('dataurl') or anexo.get('arquivo_id'):
                    continue
                try:
                    b64 = anexo['dataurl'].split(',', 1)[-1]
                    binary = base64.b64decode(b64)
                except Exception:
                    continue
                fid = str(uuid.uuid4())
                nome_disco = f'{secrets.token_hex(16)}.bin'
                with open(os.path.join(UPLOADS_DIR, nome_disco), 'wb') as f:
                    f.write(binary)
                conn.execute(
                    'INSERT INTO arquivos (id,nome_original,nome_disco,tamanho,mime) VALUES (?,?,?,?,?)',
                    (fid, anexo.get('nome', 'arquivo'), nome_disco, len(binary), 'application/pdf')
                )
                anexo['arquivo_id'] = fid
                anexo['tamanho'] = len(binary)
                del anexo['dataurl']
                changed = True
            if changed:
                item[campo_pl] = anexos
                item[campo_sg] = None
                conn.execute(f'UPDATE {tabela} SET data=? WHERE id=?', (json.dumps(item, ensure_ascii=False), row['id']))

def _gerar_cod_assinatura(conn):
    """Código curto de verificação (ex: A1B2-C3D4), único na tabela signatures."""
    for _ in range(10):
        raw = secrets.token_hex(4).upper()
        cod = raw[:4] + '-' + raw[4:]
        if not conn.execute('SELECT 1 FROM signatures WHERE cod=?', (cod,)).fetchone():
            return cod
    raise RuntimeError('Não foi possível gerar código de verificação único')

def _assinar_pdf_icp(pdf_bytes, cert_bytes, senha):
    """Assina um PDF com certificado ICP-Brasil A1 (.pfx), nível qualificado.
    Import tardio de pyHanko: o servidor sobe normalmente mesmo sem a lib
    instalada — só este módulo fica indisponível, com erro claro. Portado do SGCD/SGDP.
    Retorna (pdf_assinado_bytes, subject_do_certificado)."""
    import tempfile, io
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as tf:
        tf.write(cert_bytes)
        pfx_path = tf.name
    try:
        signer = signers.SimpleSigner.load_pkcs12(pfx_path, passphrase=senha.encode('utf-8'))
        if signer is None:
            raise ValueError('Senha do certificado incorreta ou arquivo .pfx inválido/corrompido')
        cert_subject = str(signer.signing_cert.subject.human_friendly)
        writer = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))
        out = io.BytesIO()
        signers.sign_pdf(writer, signers.PdfSignatureMetadata(field_name='Signature1'), signer=signer, output=out)
        return out.getvalue(), cert_subject
    finally:
        os.remove(pfx_path)

# ── Segurança ─────────────────────────────────────────────────────────────────

# hash/verify de senha vêm do sgx_base (esqueleto compartilhado da família)
_hash_password   = sgx_base.hash_password
_verify_password = sgx_base.verify_password

# ── Rate limit de login (vem do sgx_base) ───────────────────────────────────
_rate_limiter = sgx_base.LoginRateLimiter(max_attempts=5, lockout_window=300)
_login_rate_limited   = _rate_limiter.is_locked
_record_login_failure = _rate_limiter.record_failure
_clear_login_failures = _rate_limiter.clear

# ── Sessões ──────────────────────────────────────────────────────────────────
# create_session/delete_session/renew_session/active_sessions delegam pro
# sgx_base (mecânica idêntica nos 4 sistemas). get_session() fica local: faz
# um SELECT de colunas explícito (não u.*) por segurança — nunca deve devolver
# a coluna de hash de senha junto com os dados da sessão — e as colunas
# selecionadas divergem por sistema (schema de usuarios não é idêntico).
def create_session(user_id):
    return sgx_base.create_session(get_db, user_id, SESSION_TTL)

def get_session(token):
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            '''SELECT s.token, s.user_id, s.expires,
                      u.nome, u.username, u.cpf, u.email, u.cargo, u.matricula, u.admin, u.ativo
               FROM sessions s JOIN usuarios u ON u.id=s.user_id
               WHERE s.token=? AND s.expires>? AND u.ativo=1''',
            (token, time.time())
        ).fetchone()
    return dict(row) if row else None

def delete_session(token):
    sgx_base.delete_session(get_db, token)

def renew_session(token):
    sgx_base.renew_session(get_db, token, SESSION_TTL)

def active_sessions():
    return sgx_base.active_sessions(get_db)

def _check_shutdown():
    """O servidor nunca encerra sozinho por contagem de sessões — só via Ctrl+C
    no terminal (ver bloco principal). Aqui só dispara um backup automático,
    uma única vez, depois que a última sessão ativa termina.

    ponytail: existia um modo "Pessoal" que fazia os._exit(0) nesta função
    quando a última sessão caía — a ideia era encerrar sozinho ao fechar a
    janela do navegador. Removido — se o encerramento automático por
    inatividade real for necessário de novo, a forma correta é um timeout bem
    mais longo (minutos, não segundos), não a contagem de sessões do ping."""
    global _backup_pos_sess
    if _had_session and active_sessions() == 0 and not _backup_pos_sess:
        _backup_pos_sess = True
        cfg = _get_backup_cfg()
        if cfg['enabled']:
            print('\nÚltima sessão encerrada. Executando backup automático...')
            _do_json_backup(cfg)
            _do_db_backup(cfg)

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

    def _safe_dispatch(self, inner):
        # handle_error (mais abaixo) nunca era chamado de verdade — é método de
        # socketserver.BaseServer, não do request handler, então exceções não
        # tratadas em qualquer do_GET/POST/PUT/DELETE só apareciam no console
        # (nada no log, cliente só via a conexão cair). Isso escondia bugs reais.
        try:
            inner()
        except Exception as e:
            _log.error('Erro não tratado em %s %s: %s', self.command, self.path, e)
            try:
                self._json(500, {'error': 'Erro interno no servidor.'})
            except Exception:
                pass  # resposta já pode ter começado a ser enviada

    def do_GET(self):
        self._safe_dispatch(self._do_GET)

    def _do_GET(self):
        parsed = urlparse(self.path)
        p  = parsed.path.rstrip('/')
        qs = parse_qs(parsed.query)

        if p == '/health':
            self._json(200, {'ok': True})
        elif p.startswith('/verificar/'):
            self._serve_verificar(p[len('/verificar/'):].strip('/').upper())
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
        self._safe_dispatch(self._do_POST)

    def _do_POST(self):
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
        self._safe_dispatch(self._do_PUT)

    def _do_PUT(self):
        p = urlparse(self.path).path.rstrip('/')
        s = self._auth()
        if not s: return
        self._route_put(p, self._body(), s)

    def do_DELETE(self):
        self._safe_dispatch(self._do_DELETE)

    def _do_DELETE(self):
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
        elif p == '/api/indice-reajuste':
            self._proxy_indice(qs)
        elif p == '/api/ceis-cnep':
            self._proxy_ceis_cnep(qs)
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

        # Arquivos
        elif re.fullmatch(r'/api/arquivos/[^/]+', p):
            self._serve_arquivo(p.split('/')[-1])

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
                    'SELECT id,username,nome,cpf,email,cargo,matricula,admin,ativo,criado_em FROM usuarios'
                ).fetchall()
            self._json(200, [dict(r) for r in rows])

        elif p == '/api/relatorio/integridade':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._relatorio_integridade()

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
                with sqlite3.connect(DB_PATH, factory=_ConnAutoClose) as src, sqlite3.connect(tmp.name, factory=_ConnAutoClose) as bk:
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

        elif p == '/api/arquivos':
            self._create_arquivo(data, s)

        elif re.fullmatch(r'/api/contratos/[^/]+/anexos/[^/]+/assinar', p):
            self._assinar_anexo('contrato', p.split('/')[3], p.split('/')[5], data, s)

        elif re.fullmatch(r'/api/atas/[^/]+/anexos/[^/]+/assinar', p):
            self._assinar_anexo('ata', p.split('/')[3], p.split('/')[5], data, s)

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
            self._restore_backup(data, s)

        elif p == '/api/backups/db/restore':
            if not s['admin']: self._json(403, {'error': 'Acesso restrito'}); return
            self._restore_db_backup(body, s)

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

        elif re.fullmatch(r'/api/arquivos/[^/]+', p):
            self._delete_arquivo(p.split('/')[-1])

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
                _insert_audit_raw(conn, {'type': 'FACTORY_RESET', 'ts': _now(),
                                          'user_id': s['user_id'], 'user_nome': s['nome'],
                                          'label': 'Todos os dados apagados', 'detail': 'Reset de fábrica'})
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
            'cpf': s.get('cpf'), 'email': s.get('email'),
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
                'cpf': row['cpf'], 'email': row['email'],
                'cargo': row['cargo'], 'matricula': row['matricula'], 'admin': bool(row['admin']),
                'mustChangePassword': bool(row['must_change_password'])
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

    # ── Arquivos ─────────────────────────────────────────────────────────────
    # ponytail: front-end já lê todo upload como base64 (_lerArquivoComoDataUrl),
    # então os endpoints de arquivo seguem essa convenção (JSON/base64) em vez de
    # multipart/form-data — sem parser de multipart a mais para manter.

    def _create_arquivo(self, data, s):
        nome = (data.get('nome') or 'arquivo').strip()
        mime = data.get('mime') or 'application/octet-stream'
        b64  = data.get('data_b64') or ''
        if not b64:
            self._json(400, {'error': 'data_b64 é obrigatório'}); return
        try:
            binary = base64.b64decode(b64)
        except Exception:
            self._json(400, {'error': 'data_b64 inválido'}); return
        fid = str(uuid.uuid4())
        nome_disco = f'{secrets.token_hex(16)}.bin'
        with open(os.path.join(UPLOADS_DIR, nome_disco), 'wb') as f:
            f.write(binary)
        with get_db() as conn:
            conn.execute(
                'INSERT INTO arquivos (id,nome_original,nome_disco,tamanho,mime,uploaded_by) VALUES (?,?,?,?,?,?)',
                (fid, nome, nome_disco, len(binary), mime, s['user_id'])
            )
        self._json(200, {'id': fid, 'nome_original': nome, 'tamanho': len(binary), 'mime': mime})

    def _serve_arquivo(self, fid):
        with get_db() as conn:
            row = conn.execute('SELECT * FROM arquivos WHERE id=?', (fid,)).fetchone()
        if not row: self._json(404, {'error': 'Arquivo não encontrado'}); return
        fp = os.path.join(UPLOADS_DIR, row['nome_disco'])
        if not os.path.isfile(fp): self._json(404, {'error': 'Arquivo não encontrado no disco'}); return
        with open(fp, 'rb') as f:
            binary = f.read()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', row['mime'] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(binary)))
        safe_fn = row['nome_original'].replace('"', '_').replace('\n', '_').replace('\r', '_')
        self.send_header('Content-Disposition', f'inline; filename="{safe_fn}"')
        self.end_headers()
        self.wfile.write(binary)

    def _delete_arquivo(self, fid):
        with get_db() as conn:
            row = conn.execute('SELECT nome_disco FROM arquivos WHERE id=?', (fid,)).fetchone()
            if row:
                fp = os.path.join(UPLOADS_DIR, row['nome_disco'])
                if os.path.isfile(fp): os.remove(fp)
                conn.execute('DELETE FROM arquivos WHERE id=?', (fid,))
        self._json(200, {'ok': True})

    def _assinar_anexo(self, entity_type, entity_id, arquivo_id, data, s):
        """Assina digitalmente (ICP-Brasil) um anexo já enviado de Contrato ou Ata,
        substituindo seu conteúdo pela versão assinada. Registro imutável em
        signatures sobrevive mesmo se o anexo for depois removido/trocado."""
        tabela   = 'contratos' if entity_type == 'contrato' else 'atas'
        campo_pl = 'anexosContrato' if entity_type == 'contrato' else 'anexosAta'

        cert_b64 = data.get('cert_b64')
        senha    = data.get('senha') or ''
        if not cert_b64 or not senha:
            self._json(400, {'error': 'Certificado (.pfx) e senha são obrigatórios'}); return
        try:
            cert_bytes = base64.b64decode(cert_b64)
        except Exception:
            self._json(400, {'error': 'Certificado inválido'}); return

        with get_db() as conn:
            arq = conn.execute('SELECT * FROM arquivos WHERE id=?', (arquivo_id,)).fetchone()
        if not arq: self._json(404, {'error': 'Arquivo não encontrado'}); return
        fp = os.path.join(UPLOADS_DIR, arq['nome_disco'])
        if not os.path.isfile(fp): self._json(404, {'error': 'Arquivo não encontrado no disco'}); return
        with open(fp, 'rb') as f:
            pdf_bytes = f.read()

        try:
            pdf_assinado, cert_subject = _assinar_pdf_icp(pdf_bytes, cert_bytes, senha)
        except ImportError:
            self._json(400, {'error': 'Módulo de assinatura ICP-Brasil indisponível — instale com "pip install -r requirements.txt"'}); return
        except Exception as e:
            self._json(400, {'error': f'Falha ao assinar com o certificado: {e}'}); return
        finally:
            cert_bytes = None; senha = None  # descarta referências assim que possível

        with get_db() as conn:
            row = conn.execute(f'SELECT data FROM {tabela} WHERE id=?', (entity_id,)).fetchone()
            if not row: self._json(404, {'error': 'Registro não encontrado'}); return
            item = json.loads(row['data'])

            with open(fp, 'wb') as f:
                f.write(pdf_assinado)
            hash_sha256 = hashlib.sha256(pdf_assinado).hexdigest()
            conn.execute('UPDATE arquivos SET tamanho=? WHERE id=?', (len(pdf_assinado), arquivo_id))

            cod = _gerar_cod_assinatura(conn)
            agora = _now()
            doc_numero = item.get('numero') or ''
            doc_objeto = item.get('objeto') or (f"Ata de Registro de Preços nº {item.get('numero','')}" if entity_type == 'ata' else '')
            conn.execute(
                '''INSERT INTO signatures (cod,entity_type,entity_id,arquivo_id,doc_numero,doc_objeto,
                   signer_user_id,signer_name,cert_subject,hash_sha256,signed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (cod, entity_type, entity_id, arquivo_id, doc_numero, doc_objeto,
                 s['user_id'], s['nome'], cert_subject, hash_sha256, agora)
            )

            anexos = item.get(campo_pl) or []
            for anexo in anexos:
                if anexo.get('arquivo_id') == arquivo_id:
                    anexo['assinado']       = True
                    anexo['assinadoPor']    = s['nome']
                    anexo['assinadoEm']     = agora
                    anexo['codVerificacao'] = cod
                    anexo['tamanho']        = len(pdf_assinado)
            item[campo_pl] = anexos
            conn.execute(f'UPDATE {tabela} SET data=? WHERE id=?', (json.dumps(item, ensure_ascii=False), entity_id))
            conn.commit()

        self._json(200, {'ok': True, 'cod_verificacao': cod, 'cert_subject': cert_subject})

    def _serve_verificar(self, cod):
        with get_db() as conn:
            row = conn.execute('SELECT * FROM signatures WHERE cod=?', (cod,)).fetchone()
        if row:
            tipo_label = 'Contrato' if row['entity_type'] == 'contrato' else 'Ata de Registro de Preços'
            doc_label = f"{tipo_label} nº {row['doc_numero']}" if row['doc_numero'] else tipo_label
            status_html = f'''<h2>✓ Assinatura Encontrada</h2>
    <div class="field"><strong>Documento:</strong> {html_mod.escape(doc_label)}</div>
    <div class="field"><strong>Objeto:</strong> {html_mod.escape(row['doc_objeto'] or '—')}</div>
    <div class="field"><strong>Assinado por:</strong> {html_mod.escape(row['signer_name'] or '—')}</div>
    <div class="field"><strong>Certificado:</strong> {html_mod.escape(row['cert_subject'] or '—')}</div>
    <div class="field"><strong>Data:</strong> {html_mod.escape(row['signed_at'] or '—')}</div>'''
            status_class = 'ok'
            extra_note = '<p style="font-size:12px;color:#6b7280;margin-top:10px">Para validar a cadeia de certificação, confira também o <a href="https://verificador.iti.gov.br/" target="_blank" rel="noopener">verificador oficial do ITI</a>.</p>'
        else:
            status_html = '<h2>✗ Não encontrado</h2><p style="font-size:13px;margin-top:6px">O código não corresponde a nenhuma assinatura registrada nesta instalação.</p>'
            status_class = 'err'
            extra_note = ''

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verificação de Autenticidade — SGCA</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,sans-serif;background:#f3f4f6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
  .card{{background:#fff;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);max-width:480px;width:100%;padding:32px;text-align:center}}
  h2{{font-size:20px;margin-bottom:14px}}
  .card.ok h2{{color:#15803d}}
  .card.err h2{{color:#dc2626}}
  .field{{text-align:left;font-size:14px;margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0}}
  .brand{{margin-top:20px;font-size:11px;color:#9ca3af}}
</style>
</head>
<body>
  <div class="card {status_class}">
    {status_html}
    {extra_note}
    <div class="brand">SGCA — Sistema de Gestão de Contratos e Atas</div>
  </div>
</body>
</html>"""
        payload = html.encode('utf-8')
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
                    'INSERT INTO usuarios (username,nome,cpf,email,cargo,matricula,senha_hash,admin) VALUES (?,?,?,?,?,?,?,?)',
                    (username, nome, data.get('cpf'), data.get('email'), data.get('cargo'), data.get('matricula'),
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
            for col in ('nome', 'cpf', 'email', 'cargo', 'matricula'):
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
                fields.append('must_change_password=0')
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

    def _restore_backup(self, data, s):
        if not data.get('_sgca'):
            self._json(400, {'error': 'Arquivo não é um backup SGCA válido'}); return
        _do_db_backup()  # backup do atual antes de substituir tudo
        with get_db() as conn:
            conn.execute('DELETE FROM audit_global')
            conn.execute('DELETE FROM fornecedores')
            conn.execute('DELETE FROM contratos')
            conn.execute('DELETE FROM atas')
            conn.execute('DELETE FROM signatures')
            conn.execute('DELETE FROM arquivos')
            conn.commit()

            for fd in data.get('arquivos', []):
                b64 = fd.get('data_b64') or ''
                if not b64: continue
                try:
                    binary = base64.b64decode(b64)
                    nome_disco = f'{secrets.token_hex(16)}.bin'
                    with open(os.path.join(UPLOADS_DIR, nome_disco), 'wb') as fh:
                        fh.write(binary)
                    conn.execute(
                        '''INSERT INTO arquivos (id,nome_original,nome_disco,tamanho,mime,uploaded_by,uploaded_em)
                           VALUES (?,?,?,?,?,?,?)''',
                        (fd.get('id') or str(uuid.uuid4()), fd.get('nome_original', 'arquivo'),
                         nome_disco, len(binary), fd.get('mime', 'application/octet-stream'),
                         fd.get('uploaded_by'), fd.get('uploaded_em'))
                    )
                except Exception:
                    pass

            for sg in data.get('signatures', []):
                conn.execute(
                    '''INSERT OR REPLACE INTO signatures
                       (id,cod,entity_type,entity_id,arquivo_id,doc_numero,doc_objeto,
                        signer_user_id,signer_name,cert_subject,hash_sha256,signed_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (sg.get('id'), sg.get('cod'), sg.get('entity_type'), sg.get('entity_id'),
                     sg.get('arquivo_id'), sg.get('doc_numero'), sg.get('doc_objeto'),
                     sg.get('signer_user_id'), sg.get('signer_name'), sg.get('cert_subject'),
                     sg.get('hash_sha256'), sg.get('signed_at'))
                )

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

            # Registrado por último: as linhas acima apagam e reimportam audit_global
            # a partir do payload, então logar antes seria perdido no DELETE.
            _insert_audit_raw(conn, {'type': 'RESTAURAR_BACKUP', 'ts': _now(),
                                      'user_id': s['user_id'], 'user_nome': s['nome'],
                                      'label': 'Backup do sistema restaurado', 'detail': 'Restauração via arquivo JSON'})

        self._json(200, {'ok': True})

    def _restore_db_backup(self, raw_bytes, s):
        # raw_bytes é o conteúdo bruto do arquivo .db enviado via multipart ou binário
        if len(raw_bytes) < 16 or raw_bytes[:16] != b'SQLite format 3\x00':
            self._json(400, {'error': 'Arquivo não é um banco SQLite válido'}); return
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        try:
            tmp.write(raw_bytes); tmp.close()
            # Valida que o arquivo tem as tabelas esperadas
            with sqlite3.connect(tmp.name, factory=_ConnAutoClose) as test_conn:
                tables = {r[0] for r in test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            required = {'fornecedores', 'contratos', 'atas', 'sys_settings'}
            if not required.issubset(tables):
                self._json(400, {'error': 'Banco inválido: tabelas obrigatórias ausentes'}); return
            # Backup do atual antes de restaurar
            _do_db_backup()
            # Substitui o banco atual com o backup via API de backup SQLite (seguro)
            with sqlite3.connect(tmp.name, factory=_ConnAutoClose) as src, get_db() as dst:
                src.backup(dst)
                # Registrado na conexão já restaurada — o backup() acima substitui todo o
                # banco, então logar antes seria sobrescrito pelo conteúdo do arquivo restaurado.
                _insert_audit_raw(dst, {'type': 'RESTAURAR_DB', 'ts': _now(),
                                         'user_id': s['user_id'], 'user_nome': s['nome'],
                                         'label': 'Banco de dados restaurado', 'detail': 'Restauração via arquivo .db'})
            self._json(200, {'ok': True})
        except Exception as e:
            _log.error('Erro ao restaurar banco: %s', e)
            self._json(500, {'error': str(e)})
        finally:
            try: os.remove(tmp.name)
            except: pass

    def _relatorio_integridade(self):
        def _dir_size(path):
            total = 0
            if os.path.isdir(path):
                for f in os.listdir(path):
                    fp = os.path.join(path, f)
                    if os.path.isfile(fp): total += os.path.getsize(fp)
            return total

        cfg = _get_backup_cfg()
        bdir = cfg['path']
        backups_db = sorted(
            (f for f in os.listdir(bdir) if f.startswith('DB_SGCA_BACKUP_') and f.endswith('.db')),
            reverse=True
        ) if os.path.isdir(bdir) else []
        backups_json = sorted(
            (f for f in os.listdir(bdir) if f.startswith('SIS_SGCA_BACKUP_') and f.endswith('.json')),
            reverse=True
        ) if os.path.isdir(bdir) else []

        with get_db() as conn:
            contagens = {
                'contratos_ativos': conn.execute('SELECT COUNT(*) FROM contratos WHERE deleted_at IS NULL').fetchone()[0],
                'atas_ativas': conn.execute('SELECT COUNT(*) FROM atas WHERE deleted_at IS NULL').fetchone()[0],
                'na_lixeira': (conn.execute('SELECT COUNT(*) FROM contratos WHERE deleted_at IS NOT NULL').fetchone()[0]
                               + conn.execute('SELECT COUNT(*) FROM atas WHERE deleted_at IS NOT NULL').fetchone()[0]),
                'fornecedores': conn.execute('SELECT COUNT(*) FROM fornecedores').fetchone()[0],
                'arquivos': conn.execute('SELECT COUNT(*) FROM arquivos').fetchone()[0],
                'usuarios_ativos': conn.execute('SELECT COUNT(*) FROM usuarios WHERE ativo=1').fetchone()[0],
                'etiquetas': conn.execute('SELECT COUNT(*) FROM tags').fetchone()[0],
                'assinaturas': conn.execute('SELECT COUNT(*) FROM signatures').fetchone()[0],
            }
            eventos = [dict(r) for r in conn.execute(
                '''SELECT * FROM audit_global WHERE type IN
                   ('SYNC_BACKUP','RESTAURAR_BACKUP','RESTAURAR_DB','FACTORY_RESET')
                   ORDER BY ts DESC LIMIT 15''').fetchall()]
            last_row = conn.execute("SELECT value FROM sys_settings WHERE key='auto_backup_last'").fetchone()

        self._json(200, {
            'auto_backup_enabled': cfg['enabled'], 'auto_backup_keep': cfg['keep'], 'backup_path': bdir,
            'last_backup': last_row['value'] if last_row else None,
            'db_size_bytes': os.path.getsize(DB_PATH) if os.path.isfile(DB_PATH) else 0,
            'uploads_size_bytes': _dir_size(UPLOADS_DIR),
            'uploads_count': len([f for f in os.listdir(UPLOADS_DIR)]) if os.path.isdir(UPLOADS_DIR) else 0,
            'backups_db_count': len(backups_db), 'backups_json_count': len(backups_json),
            'backups_db_size_bytes': sum(os.path.getsize(os.path.join(bdir, f)) for f in backups_db),
            'contagens': contagens, 'eventos_recentes': eventos,
        })

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

    # ── Índice de Reajuste (Banco Central / SGS) ───────────────────────────────
    # Séries mensais de variação % — acumula o período multiplicando (1+var/100)
    # de cada mês, evitando digitação manual do percentual em aditivos de
    # reequilíbrio/repactuação.

    _INDICE_SGS = {'IPCA-E': 10764, 'IGP-M': 189, 'INPC': 188, 'INCC-M': 192}

    def _proxy_indice(self, qs):
        def qp(k): v = qs.get(k); return (v[0] if v else '').strip()
        indice, de, ate = qp('indice'), qp('de'), qp('ate')
        codigo = self._INDICE_SGS.get(indice)
        if not codigo or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', de or '') or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', ate or ''):
            self._json(400, {'message': 'Índice ou datas inválidos'}); return
        d1 = '/'.join(reversed(de.split('-')))
        d2 = '/'.join(reversed(ate.split('-')))
        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={d1}&dataFinal={d2}'
        req = urllib.request.Request(url, headers={'User-Agent': 'SGCA/2.0'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                dados = json.loads(resp.read())
            if not dados:
                self._json(200, {'percentual': None, 'meses': 0}); return
            fator = 1.0
            for item in dados:
                fator *= (1 + float(item['valor'].replace(',', '.')) / 100)
            self._json(200, {'percentual': round((fator - 1) * 100, 2), 'meses': len(dados)})
        except Exception as e:
            self._json(502, {'message': f'Falha ao consultar Banco Central: {e}'})

    # ── CEIS/CNEP (Portal da Transparência/CGU) ────────────────────────────────
    # Consulta automatizada de sanções federais por CNPJ, complementando os
    # links manuais já existentes no cadastro de Fornecedores. Exige chave de
    # API gratuita (cadastro em api.portaldatransparencia.gov.br), salva em
    # Configurações → Organização e lida aqui via sys_settings.

    def _proxy_ceis_cnep(self, qs):
        def qp(k): v = qs.get(k); return (v[0] if v else '').strip()
        cnpj = re.sub(r'\D', '', qp('cnpj'))
        if len(cnpj) != 14:
            self._json(400, {'error': 'CNPJ inválido'}); return
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM sys_settings WHERE key='portal_transparencia_key'"
            ).fetchone()
        api_key = row['value'] if row else ''
        if not api_key:
            self._json(400, {'error': 'Chave de API do Portal da Transparência não configurada (Configurações → Organização)'}); return

        resultado = {'ceis': [], 'cnep': [], 'erro': None}
        for tipo in ('ceis', 'cnep'):
            url = f'https://api.portaldatransparencia.gov.br/api-de-dados/{tipo}?cnpjSancionado={cnpj}&pagina=1'
            req = urllib.request.Request(url, headers={'chave-api-dados': api_key, 'User-Agent': 'SGCA/2.0'})
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resultado[tipo] = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                resultado['erro'] = f'{tipo.upper()}: HTTP {e.code} (verifique a chave de API)'
            except Exception as e:
                resultado['erro'] = f'{tipo.upper()}: {e}'
        self._json(200, resultado)

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

# _send_email_raw vem do sgx_base (esqueleto compartilhado da família)
_send_email_raw = sgx_base.send_email_raw

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
                    itens.append((nome, dias, item.get('fiscalEmail'), item.get('gestorEmail')))
            except Exception:
                pass
        return itens

    def _fiscalizacoes_pendentes():
        with get_db() as conn:
            rows = conn.execute("SELECT data FROM contratos WHERE deleted_at IS NULL").fetchall()
        itens = []
        for row in rows:
            try:
                item = json.loads(row['data'])
            except Exception:
                continue
            if item.get('status') in ('encerrado', 'rescindido'):
                continue
            ultima = max((f.get('data') for f in (item.get('fiscalizacoes') or []) if f.get('data')), default=None)
            ancora = ultima or item.get('vigenciaInicial')
            if not ancora:
                continue
            try:
                ts = time.mktime(time.strptime(ancora[:10], '%Y-%m-%d'))
                dias = int((agora - ts) / 86400)
                if dias >= 30:
                    nome = item.get('numero') and f"Contrato {item['numero']}" or (item.get('objeto') or item.get('id'))
                    itens.append((nome, dias, item.get('fiscalEmail'), item.get('gestorEmail')))
            except Exception:
                pass
        return itens

    contratos = _vencimentos('contratos', 'Contrato')
    atas      = _vencimentos('atas', 'Ata')
    fiscalizacoes_pendentes = _fiscalizacoes_pendentes()

    if not contratos and not atas and not fiscalizacoes_pendentes:
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

    # Notifica individualmente o fiscal e o gestor de cada contrato vencendo
    por_fiscal = {}
    for nome, dias, email, email_gestor in contratos:
        if email:
            por_fiscal.setdefault(email, []).append((nome, dias))
        if email_gestor and email_gestor != email:  # fiscal e gestor podem ser a mesma pessoa
            por_fiscal.setdefault(email_gestor, []).append((nome, dias))
    for email, itens in por_fiscal.items():
        corpo_f = (f"<p>Resumo automático do SGCA — {hoje}</p>"
                   f"<p>Contrato(s) sob sua fiscalização com vigência vencendo:</p>" + _linhas('', itens))
        try:
            _send_email_raw(smtp_cfg, frm, email, f'SGCA — Contrato(s) sob sua fiscalização ({hoje})', corpo_f)
            print(f'  [ALERTAS] E-mail enviado ao fiscal {email} ({len(itens)} contrato(s))', flush=True)
        except Exception as e:
            _log.error('Falha ao enviar e-mail ao fiscal %s: %s', email, e)

    # Notifica o fiscal e o gestor de contratos sem fiscalização mensal
    # registrada há 30 dias ou mais (Art. 117, Lei 14.133/2021)
    por_fiscal_fiscalizacao = {}
    for nome, dias, email, email_gestor in fiscalizacoes_pendentes:
        if email:
            por_fiscal_fiscalizacao.setdefault(email, []).append((nome, dias))
        if email_gestor and email_gestor != email:  # fiscal e gestor podem ser a mesma pessoa
            por_fiscal_fiscalizacao.setdefault(email_gestor, []).append((nome, dias))
    for email, itens in por_fiscal_fiscalizacao.items():
        linhas = ''.join(f'<li><strong>{html_mod.escape(str(nome))}</strong> — {dias} dia(s) sem fiscalização registrada</li>' for nome, dias in sorted(itens, key=lambda x: -x[1]))
        corpo_fz = (f"<p>Resumo automático do SGCA — {hoje}</p>"
                    f"<p>Contrato(s) sob sua fiscalização pendentes de registro de fiscalização mensal:</p><ul>{linhas}</ul>")
        try:
            _send_email_raw(smtp_cfg, frm, email, f'SGCA — Fiscalização mensal pendente ({hoje})', corpo_fz)
            print(f'  [ALERTAS] E-mail de fiscalização pendente enviado a {email} ({len(itens)} contrato(s))', flush=True)
        except Exception as e:
            _log.error('Falha ao enviar e-mail de fiscalização ao fiscal %s: %s', email, e)

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
    # Limpa sessões expiradas a cada 5s e dispara o backup pós-sessão
    # (_check_shutdown — não encerra mais o servidor, só faz backup).
    # SESSION_TTL=60s dá folga de sobra sobre o ping a cada 5s: um TTL curto
    # (era 15s) expirava sessões à toa quando o ping atrasava por qualquer
    # motivo comum — carregamento inicial da página disputando conexão HTTP
    # com várias outras chamadas simultâneas, ou a aba principal perdendo
    # foco ao abrir um popup de documento.
    while True:
        time.sleep(5)
        if _watchdog_paused:
            continue
        sgx_base.purge_expired_sessions(get_db)
        try: _check_shutdown()
        except Exception as e: _log.error('Erro em _check_shutdown: %s', e)
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
        arqs = []
        for r in conn.execute('SELECT * FROM arquivos').fetchall():
            p = os.path.join(UPLOADS_DIR, r['nome_disco'])
            if os.path.isfile(p):
                with open(p, 'rb') as f:
                    arqs.append({**dict(r), 'data_b64': base64.b64encode(f.read()).decode()})
        signatures = [dict(r) for r in conn.execute('SELECT * FROM signatures').fetchall()]
    return {
        '_sgca': True, 'version': 5, 'exportedAt': _now(),
        'fornecedores': fornecedores, 'contratos': contratos, 'atas': atas,
        'auditGlobal': audit, 'settings': settings,
        'arquivos': arqs, 'signatures': signatures,
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
    try:
        keep = max(1, int(cfg.get('auto_backup_keep') or BACKUP_KEEP))
    except (TypeError, ValueError):
        keep = BACKUP_KEEP  # valor não-numérico salvo por engano (ex.: via chamada direta à API) — ignora em vez de derrubar o watchdog
    return {
        'path':    cfg.get('backup_path') or BACKUP_DIR,
        'enabled': cfg.get('auto_backup_enabled', '1') != '0',
        'keep':    keep,
    }

def _do_db_backup(cfg=None):
    if cfg is None: cfg = _get_backup_cfg()
    bdir = cfg['path']
    keep = cfg['keep']
    os.makedirs(bdir, exist_ok=True)
    name = time.strftime('DB_SGCA_BACKUP_%Y-%m-%d_%H-%M-%S.db')
    dst  = os.path.join(bdir, name)
    try:
        with sqlite3.connect(DB_PATH, factory=_ConnAutoClose) as src, sqlite3.connect(dst, factory=_ConnAutoClose) as bk:
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

# ── Menu inicial ──────────────────────────────────────────────────────────────

def _selecionar_modo():
    print()
    print('  ╔══════════════════════════════════════════════════╗')
    print('  ║   SGCA — Sistema de Gestão de Contratos e Atas    ║')
    print('  ╚══════════════════════════════════════════════════╝')
    print()
    print('  [1] Diagnóstico     — Verifica rede, porta e firewall')
    print('  [2] Iniciar Servidor')
    print()
    if not sys.stdin.isatty():
        op = '2'
    else:
        while True:
            try:
                op = input('  Opção [1/2]: ').strip()
            except (EOFError, KeyboardInterrupt):
                op = '2'
            if op in ('1', '2'):
                break
            print('  Digite 1 ou 2.')
    if op == '1':
        import subprocess as _sp
        diag = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagnostico.py')
        _sp.run([sys.executable, diag])
        sys.exit(0)
    print()
    print('  ─────────────────────────────────────────────────')

if __name__ == '__main__':
    _selecionar_modo()
    _check_db_integrity()
    _rotate_backups(_get_backup_cfg())  # limpa excedentes dos backups da sessão anterior
    threading.Thread(target=_watchdog, daemon=True).start()

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('', PORT), SGCAHandler) as httpd:
        print(f'  Servidor: http://localhost:{PORT}')
        import socket as _socket
        try:
            ip_local = _socket.gethostbyname(_socket.gethostname())
        except Exception:
            ip_local = 'desconhecido'
        print(f'  Rede:     http://{ip_local}:{PORT}/SGCA.html')
        print()

        browser = _find_browser()
        if browser:
            profile_dir = PROFILE_DIR
            subprocess.Popen([
                browser,
                f'--app=http://localhost:{PORT}/SGCA.html',
                '--start-maximized',
                '--disable-background-mode',
                f'--user-data-dir={profile_dir}',
            ])
            print('  App aberto no navegador.')
        else:
            print(f'  Chrome/Edge não encontrado. Abra manualmente: http://localhost:{PORT}/SGCA.html')

        print('  Aguardando conexões... (Ctrl+C para encerrar)')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n  Encerrando servidor...')
