# Suíte de testes do backend (server.py) — sobe o servidor real contra um
# banco/uploads/backups temporários e bate nos endpoints REST via http.client.
# python -m unittest discover -s tests   (ou: python tests/test_server.py)
import base64
import http.client
import io
import json
import os
import shutil
import socketserver
import sqlite3
import sys
import tempfile
import threading
import unittest
import uuid
import urllib.parse
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402

PORT = 3091
_tmpdir = None
_httpd = None
_thread = None


def setUpModule():
    # Um único servidor para toda a suíte — DB_PATH/UPLOADS_DIR são globais do módulo
    # server.py, então instâncias por classe na mesma porta correm risco de uma classe
    # trocar esses globais enquanto uma thread de requisição da classe anterior ainda
    # está em voo, misturando os dados das duas.
    global _tmpdir, _httpd, _thread
    _tmpdir = tempfile.mkdtemp(prefix='sgca_test_')
    server.DB_PATH = os.path.join(_tmpdir, 'sgca.db')
    server.UPLOADS_DIR = os.path.join(_tmpdir, 'uploads')
    server.BACKUP_DIR = os.path.join(_tmpdir, 'backups')
    os.makedirs(server.UPLOADS_DIR, exist_ok=True)
    os.makedirs(server.BACKUP_DIR, exist_ok=True)
    server.init_db()
    # A suíte age como um sistema já instalado, com a senha padrão trocada: sem
    # isto todo login como admin/admin123 tomaria 403, porque o servidor passou a
    # recusar qualquer rota enquanto a troca obrigatória estiver pendente (o
    # bloqueio em si tem teste próprio, em TestSenhaPadraoObrigatoria).
    with server.get_db() as conn:
        conn.execute("UPDATE usuarios SET must_change_password=0 WHERE username='admin'")
        conn.commit()

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    _httpd = socketserver.ThreadingTCPServer(('127.0.0.1', PORT), server.SGCAHandler)
    _thread = threading.Thread(target=_httpd.serve_forever, daemon=True)
    _thread.start()


def tearDownModule():
    _httpd.shutdown()
    _httpd.server_close()
    shutil.rmtree(_tmpdir, ignore_errors=True)


class SGCATestCase(unittest.TestCase):

    def request(self, method, path, body=None, token=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=5)
        hdrs = {'Content-Type': 'application/json'}
        if token:
            hdrs['Authorization'] = f'Bearer {token}'
        if headers:
            hdrs.update(headers)
        # Content-Length precisa ser em bytes, não em caracteres — corpo com acentos
        # (ex. "Aquisição") tem mais bytes que caracteres em UTF-8; passar a string
        # crua deixa o http.client contar caracteres e truncar o corpo na rede.
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        try:
            parsed = json.loads(data) if data else None
        except ValueError:
            parsed = data  # resposta binária (ex: download de arquivo)
        return resp.status, parsed

    def login(self, username='admin', password='admin123'):
        status, data = self.request('POST', '/api/auth/login', {'username': username, 'password': password})
        self.assertEqual(status, 200, data)
        return data['token']


class TestAuth(SGCATestCase):

    def test_login_com_credenciais_corretas(self):
        status, data = self.request('POST', '/api/auth/login', {'username': 'admin', 'password': 'admin123'})
        self.assertEqual(status, 200)
        self.assertIn('token', data)
        self.assertTrue(data['user']['admin'])

    def test_login_com_senha_errada(self):
        status, data = self.request('POST', '/api/auth/login', {'username': 'admin', 'password': 'errada'})
        self.assertEqual(status, 401)

    def test_endpoint_protegido_sem_token(self):
        status, data = self.request('GET', '/api/contratos')
        self.assertEqual(status, 401)

    def test_endpoint_protegido_com_token_invalido(self):
        status, data = self.request('GET', '/api/contratos', token='token-que-nao-existe')
        self.assertEqual(status, 401)

    def test_me_retorna_usuario_da_sessao(self):
        token = self.login()
        status, data = self.request('GET', '/api/auth/me', token=token)
        self.assertEqual(status, 200)
        self.assertEqual(data['username'], 'admin')


class TestFornecedores(SGCATestCase):

    def test_criar_e_atualizar_fornecedor(self):
        token = self.login()
        status, created = self.request('POST', '/api/fornecedores',
                                        {'cnpj': '00000000000191', 'razaoSocial': 'Fornecedor Teste LTDA'},
                                        token=token)
        self.assertEqual(status, 200)
        fid = created['id']

        status, updated = self.request('PUT', f'/api/fornecedores/{fid}', {'razaoSocial': 'Nome Atualizado'}, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(updated['razaoSocial'], 'Nome Atualizado')

        status, listed = self.request('GET', '/api/fornecedores', token=token)
        self.assertTrue(any(f['id'] == fid for f in listed['items']))


class TestContratos(SGCATestCase):

    def test_criar_listar_atualizar_e_excluir_contrato(self):
        token = self.login()

        status, created = self.request('POST', '/api/contratos', {
            'objeto': 'Manutenção predial', 'numero': '10/2026',
            'valorGlobal': 100000.0, 'vigenciaFinal': '2027-01-01', 'status': 'vigente'
        }, token=token)
        self.assertEqual(status, 200)
        cid = created['id']
        self.assertEqual(created['objeto'], 'Manutenção predial')
        self.assertEqual(created['aditivos'], [])

        status, listed = self.request('GET', '/api/contratos', token=token)
        self.assertEqual(status, 200)
        self.assertTrue(any(c['id'] == cid for c in listed['items']))

        status, updated = self.request('PUT', f'/api/contratos/{cid}', {'status': 'em_prorrogacao'}, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(updated['status'], 'em_prorrogacao')

        # soft-delete + lixeira + restauração
        status, _ = self.request('DELETE', f'/api/contratos/{cid}', token=token)
        self.assertEqual(status, 200)
        status, listed = self.request('GET', '/api/contratos', token=token)
        self.assertFalse(any(c['id'] == cid for c in listed['items']))
        status, trashed = self.request('GET', '/api/contratos?trash=1', token=token)
        self.assertTrue(any(c['id'] == cid for c in trashed['items']))
        status, _ = self.request('PUT', f'/api/contratos/{cid}/restore', token=token)
        self.assertEqual(status, 200)
        status, listed = self.request('GET', '/api/contratos', token=token)
        self.assertTrue(any(c['id'] == cid for c in listed['items']))

    def test_filtro_por_fornecedor(self):
        token = self.login()
        status, f1 = self.request('POST', '/api/fornecedores', {'razao_social': 'Fornecedor Filtro A'}, token=token)
        status, f2 = self.request('POST', '/api/fornecedores', {'razao_social': 'Fornecedor Filtro B'}, token=token)
        self.request('POST', '/api/contratos', {'objeto': 'Contrato do A', 'fornecedorId': f1['id']}, token=token)
        self.request('POST', '/api/contratos', {'objeto': 'Contrato do B', 'fornecedorId': f2['id']}, token=token)

        status, listed = self.request('GET', f"/api/contratos?fornecedor={f1['id']}", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(len(listed['items']), 1)
        self.assertEqual(listed['items'][0]['objeto'], 'Contrato do A')

    def test_filtro_por_fiscal(self):
        token = self.login()
        self.request('POST', '/api/contratos', {'objeto': 'Contrato do fiscal X', 'fiscalNome': 'Fiscal X'}, token=token)
        self.request('POST', '/api/contratos', {'objeto': 'Contrato do fiscal Y', 'fiscalNome': 'Fiscal Y'}, token=token)

        status, listed = self.request('GET', '/api/contratos?fiscal=' + urllib.parse.quote('Fiscal X'), token=token)
        self.assertEqual(status, 200)
        self.assertEqual(len(listed['items']), 1)
        self.assertEqual(listed['items'][0]['objeto'], 'Contrato do fiscal X')

    def test_aditivo_de_prazo_atualiza_vigencia_e_de_valor_acumula_percentual(self):
        token = self.login()
        status, created = self.request('POST', '/api/contratos', {
            'objeto': 'Serviço de vigilância', 'valorGlobal': 200000.0, 'vigenciaFinal': '2026-12-31'
        }, token=token)
        cid = created['id']

        status, updated = self.request('POST', f'/api/contratos/{cid}/aditivos', {
            'tipo': 'prazo', 'novaVigenciaFinal': '2027-06-30', 'justificativa': 'Prorrogação de prazo'
        }, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(updated['vigenciaFinal'], '2027-06-30')
        self.assertEqual(len(updated['aditivos']), 1)

        status, updated = self.request('POST', f'/api/contratos/{cid}/aditivos', {
            'tipo': 'valor', 'valorVariacao': 20000.0, 'justificativa': 'Acréscimo de escopo'
        }, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(updated['valorGlobal'], 220000.0)
        self.assertEqual(updated['percentualAcumulado'], 10.0)

        aid = updated['aditivos'][-1]['id']
        status, _ = self.request('DELETE', f'/api/contratos/{cid}/aditivos/{aid}', token=token)
        self.assertEqual(status, 200)
        status, single = self.request('GET', f'/api/contratos/{cid}', token=token)
        self.assertEqual(len(single['aditivos']), 1)

    def test_busca_contrato_inexistente_retorna_404(self):
        token = self.login()
        status, data = self.request('GET', '/api/contratos/id-que-nao-existe', token=token)
        self.assertEqual(status, 404)

    def test_indice_reajuste_rejeita_indice_ou_datas_invalidas(self):
        token = self.login()
        status, data = self.request('GET', '/api/indice-reajuste?indice=outro&de=2025-01-01&ate=2026-01-01', token=token)
        self.assertEqual(status, 400)
        status, data = self.request('GET', '/api/indice-reajuste?indice=IPCA-E&de=01-01-2025&ate=2026-01-01', token=token)
        self.assertEqual(status, 400)

    def test_ceis_cnep_rejeita_cnpj_invalido(self):
        token = self.login()
        status, data = self.request('GET', '/api/ceis-cnep?cnpj=123', token=token)
        self.assertEqual(status, 400)

    def test_ceis_cnep_exige_chave_de_api_configurada(self):
        token = self.login()
        status, data = self.request('GET', '/api/ceis-cnep?cnpj=12345678000199', token=token)
        self.assertEqual(status, 400)
        self.assertIn('Chave de API', data['error'])


class TestAtas(SGCATestCase):

    def test_criar_ata_com_itens_e_controlar_saldo(self):
        token = self.login()

        status, created = self.request('POST', '/api/atas', {
            'numero': '05/2026', 'orgaoGerenciador': 'Prefeitura Municipal', 'vigenciaFinal': '2027-03-01'
        }, token=token)
        self.assertEqual(status, 200)
        aid = created['id']
        self.assertEqual(created['itens'], [])

        status, updated = self.request('POST', f'/api/atas/{aid}/itens', {
            'descricao': 'Papel A4', 'quantidadeRegistrada': 1000, 'precoUnitario': 25.0
        }, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(len(updated['itens']), 1)
        self.assertEqual(updated['itens'][0]['quantidadeUtilizada'], 0)
        iid = updated['itens'][0]['id']

        status, updated = self.request('PUT', f'/api/atas/{aid}/itens/{iid}', {'quantidadeUtilizada': 850}, token=token)
        self.assertEqual(status, 200)
        self.assertEqual(updated['itens'][0]['quantidadeUtilizada'], 850)

        status, listed = self.request('GET', '/api/atas', token=token)
        self.assertTrue(any(a['id'] == aid for a in listed['items']))

        status, _ = self.request('DELETE', f'/api/atas/{aid}/itens/{iid}', token=token)
        self.assertEqual(status, 200)
        status, single = self.request('GET', f'/api/atas/{aid}', token=token)
        self.assertEqual(single['itens'], [])

    def test_busca_ata_inexistente_retorna_404(self):
        token = self.login()
        status, data = self.request('GET', '/api/atas/id-que-nao-existe', token=token)
        self.assertEqual(status, 404)


class TestAudit(SGCATestCase):

    def test_registra_e_lista_evento_de_auditoria(self):
        token = self.login()
        status, _ = self.request('POST', '/api/audit', {'type': 'TESTE', 'label': 'Evento de teste'}, token=token)
        self.assertEqual(status, 200)

        status, data = self.request('GET', '/api/audit', token=token)
        self.assertEqual(status, 200)
        self.assertTrue(any(e['type'] == 'TESTE' for e in data['items']))

    def test_filtro_de_auditoria_por_processo(self):
        token = self.login()
        self.request('POST', '/api/audit', {'type': 'CONTRATO_EDITADO', 'label': 'Contrato editado', 'processId': 'abc-123'}, token=token)
        self.request('POST', '/api/audit', {'type': 'CONTRATO_EDITADO', 'label': 'Contrato editado', 'processId': 'xyz-999'}, token=token)

        status, data = self.request('GET', '/api/audit?processId=abc-123', token=token)
        self.assertEqual(status, 200)
        self.assertTrue(all(e['process_id'] == 'abc-123' for e in data['items']))
        self.assertTrue(any(e['process_id'] == 'abc-123' for e in data['items']))

    def test_bulk_de_auditoria_exige_admin(self):
        # cria usuário não-admin e confirma que /api/audit/bulk nega acesso
        admin_token = self.login()
        status, _ = self.request('POST', '/api/usuarios', {
            'username': 'comum', 'nome': 'Usuário Comum', 'password': 'senha123', 'admin': False
        }, token=admin_token)
        self.assertEqual(status, 200)

        user_token = self.login('comum', 'senha123')
        status, data = self.request('POST', '/api/audit/bulk', [{'type': 'X', 'label': 'Y'}], token=user_token)
        self.assertEqual(status, 403)


class TestSettingsAndUsers(SGCATestCase):

    def test_settings_get_e_save_exige_admin(self):
        admin_token = self.login()
        status, _ = self.request('PUT', '/api/settings', {'tema': 'escuro'}, token=admin_token)
        self.assertEqual(status, 200)
        status, data = self.request('GET', '/api/settings', token=admin_token)
        self.assertEqual(status, 200)
        self.assertEqual(data.get('tema'), 'escuro')

    def test_settings_geral_nao_inclui_brasao_dataurl(self):
        # brasao_dataurl pode ter alguns MB (imagem em base64) e tem endpoint
        # próprio (/api/settings/brasao) — não deve viajar no GET /api/settings
        # geral, consultado a cada login, sob risco de deixar essa rota lenta
        # o bastante para 401ar durante a sessão curta (SESSION_TTL).
        admin_token = self.login()
        self.request('PUT', '/api/settings/brasao', {'brasao_dataurl': 'data:image/png;base64,AAAA'}, token=admin_token)
        status, data = self.request('GET', '/api/settings', token=admin_token)
        self.assertEqual(status, 200)
        self.assertNotIn('brasao_dataurl', data)
        status, data = self.request('GET', '/api/settings/brasao', token=admin_token)
        self.assertEqual(status, 200)
        self.assertEqual(data.get('brasao_dataurl'), 'data:image/png;base64,AAAA')

    def test_usuario_comum_nao_pode_criar_usuario(self):
        admin_token = self.login()
        self.request('POST', '/api/usuarios', {
            'username': 'user2', 'nome': 'Outro Usuário', 'password': 'senha123', 'admin': False
        }, token=admin_token)
        user_token = self.login('user2', 'senha123')

        status, data = self.request('POST', '/api/usuarios', {
            'username': 'user3', 'nome': 'Terceiro', 'password': 'senha123', 'admin': False
        }, token=user_token)
        self.assertEqual(status, 403)


class TestBackup(SGCATestCase):

    def test_export_backup_json_contem_dados_criados(self):
        token = self.login()
        self.request('POST', '/api/contratos', {'objeto': 'Contrato para backup'}, token=token)

        status, data = self.request('GET', '/api/backup', token=token)
        self.assertEqual(status, 200)
        self.assertEqual(data.get('_sgx'), 'SGCA')   # envelope padronizado da família
        self.assertNotIn('usuarios', data)           # SGCA não leva contas no JSON portátil
        self.assertTrue(any(c['objeto'] == 'Contrato para backup' for c in data['contratos']))

    def test_do_db_backup_aciona_rotacao_automaticamente(self):
        # _do_db_backup() era chamado em vários pontos (fechar sistema, backup manual,
        # antes de restaurar) sem nunca acionar _rotate_backups() — os arquivos só eram
        # limpos na próxima vez que o servidor fosse reiniciado do zero, deixando a pasta
        # de backups crescer sem limite entre reinícios.
        admin_token = self.login()
        self.request('PUT', '/api/settings', {'auto_backup_keep': '2'}, token=admin_token)
        for i in range(3):
            open(os.path.join(server.BACKUP_DIR, f'DB_SGCA_BACKUP_2020-01-0{i+1}_00-00-00.db'), 'w').close()
            open(os.path.join(server.BACKUP_DIR, f'SIS_SGCA_BACKUP_2020-01-0{i+1}_00-00-00.json'), 'w').close()
        server._do_db_backup()
        db_files  = [f for f in os.listdir(server.BACKUP_DIR) if f.startswith('DB_SGCA_BACKUP_')]
        sis_files = [f for f in os.listdir(server.BACKUP_DIR) if f.startswith('SIS_SGCA_BACKUP_')]
        self.assertEqual(len(db_files), 2)
        self.assertEqual(len(sis_files), 2)


class TestAgendaAlerts(SGCATestCase):

    def test_send_daily_alerts_detecta_vencimento_e_marca_enviado(self):
        import datetime
        token = self.login()
        vig = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        self.request('POST', '/api/contratos', {'objeto': 'Contrato vencendo', 'vigenciaFinal': vig, 'status': 'vigente'}, token=token)

        with server.get_db() as conn:
            conn.execute("DELETE FROM sys_settings WHERE key='alert_email_last_sent'")
        # sem SMTP configurado: não deve marcar como enviado (retorna cedo)
        server._send_daily_alerts()
        with server.get_db() as conn:
            row = conn.execute("SELECT value FROM sys_settings WHERE key='alert_email_last_sent'").fetchone()
        self.assertIsNone(row)

        # com SMTP "configurado" (host inválido de propósito — só testa que a lógica roda até o fim)
        with server.get_db() as conn:
            for k, v in [('smtp_host', 'smtp.invalido.test'), ('smtp_user', 'a@a.com'),
                         ('smtp_pass', 'x'), ('smtp_to', 'dest@teste.com')]:
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (k, v))
        server._send_daily_alerts()
        with server.get_db() as conn:
            row = conn.execute("SELECT value FROM sys_settings WHERE key='alert_email_last_sent'").fetchone()
            for k in ('smtp_host', 'smtp_user', 'smtp_pass', 'smtp_to', 'alert_email_last_sent'):
                conn.execute('DELETE FROM sys_settings WHERE key=?', (k,))
        self.assertIsNotNone(row)

    def test_send_daily_alerts_notifica_fiscal_sem_email_interno_configurado(self):
        import datetime
        token = self.login()
        vig = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        self.request('POST', '/api/contratos',
                     {'objeto': 'Contrato com fiscal', 'vigenciaFinal': vig, 'status': 'vigente',
                      'fiscalEmail': 'fiscal@teste.com', 'gestorEmail': 'gestor@teste.com'}, token=token)

        with server.get_db() as conn:
            conn.execute("DELETE FROM sys_settings WHERE key='alert_email_last_sent'")
            # SMTP configurado, mas SEM e-mail interno (smtp_to) — só o aviso ao fiscal deve ser tentado
            for k, v in [('smtp_host', 'smtp.invalido.test'), ('smtp_user', 'a@a.com'), ('smtp_pass', 'x')]:
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (k, v))
        server._send_daily_alerts()
        with server.get_db() as conn:
            row = conn.execute("SELECT value FROM sys_settings WHERE key='alert_email_last_sent'").fetchone()
            for k in ('smtp_host', 'smtp_user', 'smtp_pass', 'alert_email_last_sent'):
                conn.execute('DELETE FROM sys_settings WHERE key=?', (k,))
        self.assertIsNotNone(row)

    def test_send_daily_alerts_nao_duplica_quando_fiscal_e_gestor_sao_a_mesma_pessoa(self):
        import datetime
        token = self.login()
        vig = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
        self.request('POST', '/api/contratos',
                     {'objeto': 'Contrato com fiscal-gestor único', 'vigenciaFinal': vig, 'status': 'vigente',
                      'fiscalEmail': 'mesma@teste.com', 'gestorEmail': 'mesma@teste.com'}, token=token)

        sent = []
        original = server._send_email_raw
        server._send_email_raw = lambda smtp, frm, to, subj, html, plain='': sent.append((to, subj, html))
        with server.get_db() as conn:
            conn.execute("DELETE FROM sys_settings WHERE key='alert_email_last_sent'")
            for k, v in [('smtp_host', 'smtp.invalido.test'), ('smtp_user', 'a@a.com'), ('smtp_pass', 'x')]:
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (k, v))
        try:
            server._send_daily_alerts()
        finally:
            server._send_email_raw = original
            with server.get_db() as conn:
                for k in ('smtp_host', 'smtp_user', 'smtp_pass', 'alert_email_last_sent'):
                    conn.execute('DELETE FROM sys_settings WHERE key=?', (k,))

        vencimento_emails = [s for s in sent if s[0] == 'mesma@teste.com' and 'sob sua fiscalização' in s[1]]
        self.assertEqual(len(vencimento_emails), 1)
        self.assertEqual(vencimento_emails[0][2].count('Contrato com fiscal-gestor único'), 1)

    def test_send_daily_alerts_detecta_fiscalizacao_pendente(self):
        import datetime
        token = self.login()
        vig_inicial = (datetime.date.today() - datetime.timedelta(days=40)).isoformat()
        # vigência final bem no futuro para não disparar o alerta de vencimento,
        # isolando o teste no novo caminho de fiscalização pendente
        vig_final = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()
        self.request('POST', '/api/contratos',
                     {'objeto': 'Contrato sem fiscalização recente', 'vigenciaInicial': vig_inicial,
                      'vigenciaFinal': vig_final, 'status': 'vigente', 'fiscalEmail': 'fiscal2@teste.com'}, token=token)

        with server.get_db() as conn:
            conn.execute("DELETE FROM sys_settings WHERE key='alert_email_last_sent'")
            for k, v in [('smtp_host', 'smtp.invalido.test'), ('smtp_user', 'a@a.com'), ('smtp_pass', 'x')]:
                conn.execute('INSERT OR REPLACE INTO sys_settings (key,value) VALUES (?,?)', (k, v))
        server._send_daily_alerts()
        with server.get_db() as conn:
            row = conn.execute("SELECT value FROM sys_settings WHERE key='alert_email_last_sent'").fetchone()
            for k in ('smtp_host', 'smtp_user', 'smtp_pass', 'alert_email_last_sent'):
                conn.execute('DELETE FROM sys_settings WHERE key=?', (k,))
        self.assertIsNotNone(row)


class TestHealth(SGCATestCase):

    def test_health_check(self):
        status, data = self.request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertTrue(data['ok'])


class TestNuncaEncerraSozinho(SGCATestCase):

    def test_ultima_sessao_expirar_nao_derruba_o_processo(self):
        # Regressão: existia um modo "Pessoal" em que _check_shutdown() chamava
        # os._exit(0) quando a última sessão ativa expirava. os._exit(0) mata o
        # processo Python na hora, sem exceção capturável — se ainda existisse,
        # o processo deste teste morreria aqui e nada abaixo executaria.
        token = self.login()
        with server.get_db() as conn:
            conn.execute('DELETE FROM sessions')  # simula a última sessão expirando
        server._had_session = True
        server._backup_pos_sess = False
        server._check_shutdown()

        # Se chegou aqui, o processo sobreviveu — confirma que o servidor
        # ainda responde normalmente (não travou nem morreu).
        status, _ = self.request('GET', '/health')
        self.assertEqual(status, 200)

    def test_sessao_sobrevive_atraso_maior_que_o_ttl_antigo(self):
        # Regressão: SESSION_TTL era 15s (renovado pelo ping a cada 5s) — margem
        # curta o bastante para uma sessão expirar sozinha no uso normal (várias
        # chamadas de API concorrentes disputando conexão HTTP logo no login,
        # ou a aba principal perdendo foco ao abrir um popup de documento),
        # derrubando o usuário de volta pro login no meio do trabalho sem
        # ninguém ter saído de propósito.
        #
        # Simula 20s "consumidos" do TTL sem nenhum ping renovar a sessão —
        # sob o TTL antigo (15s) isso já teria expirado; sob o atual (60s)
        # ainda sobra bastante margem.
        self.assertGreater(server.SESSION_TTL, 20,
                            'SESSION_TTL muito curto — sessão expira sozinha em uso normal sem ping')
        token = self.login()
        with server.get_db() as conn:
            conn.execute('UPDATE sessions SET expires=expires-20 WHERE token=?', (token,))
        status, _ = self.request('GET', '/api/fornecedores', token=token)
        self.assertEqual(status, 200, 'sessão expirou com atraso que o TTL antigo (15s) não sobreviveria')


class TestRestoreNaoPerdeDados(SGCATestCase):
    """Regressão do eixo perda de dado (auditoria 2026-07-24).

    Dois defeitos no mesmo caminho: (a) `deleted_at` não ia no backup, então
    restaurar devolvia ao cadastro tudo o que estava na Lixeira; (b) havia um
    commit() logo depois dos DELETEs, que confirmava o apagamento antes de
    qualquer inserção ser validada — um item malformado no arquivo deixava o
    sistema vazio, sem nada restaurado.
    """

    def _criar(self, token):
        status, f = self.request('POST', '/api/fornecedores',
                                 {'cnpj': '11.222.333/0001-81', 'razao': 'Alfa Ltda'}, token=token)
        self.assertEqual(status, 200, f)
        status, c = self.request('POST', '/api/contratos',
                                 {'objeto': 'Contrato de teste', 'numero': '1/2026',
                                  'fornecedorId': f['id']}, token=token)
        self.assertEqual(status, 200, c)
        return f['id'], c['id']

    def _deleted_at(self, tabela, rid):
        with server.get_db() as conn:
            row = conn.execute(f'SELECT deleted_at FROM {tabela} WHERE id=?', (rid,)).fetchone()
        return row['deleted_at'] if row else None

    def test_restaurar_nao_ressuscita_contrato_da_lixeira(self):
        token = self.login()
        _, cid = self._criar(token)
        self.assertEqual(self.request('DELETE', f'/api/contratos/{cid}', token=token)[0], 200)
        excluido_em = self._deleted_at('contratos', cid)
        self.assertIsNotNone(excluido_em, 'exclusão não marcou deleted_at — teste inválido')

        _, backup = self.request('GET', '/api/backup', token=token)
        self.assertEqual(self.request('POST', '/api/backup/restore', backup, token=token)[0], 200)
        self.assertEqual(self._deleted_at('contratos', cid), excluido_em,
                         'restaurar backup tirou o contrato da Lixeira')

    def test_restore_que_falha_nao_apaga_o_banco(self):
        token = self.login()
        self._criar(token)
        _, backup = self.request('GET', '/api/backup', token=token)

        def contar():
            with server.get_db() as conn:
                return {t: conn.execute(f'SELECT COUNT(*) c FROM {t}').fetchone()['c']
                        for t in ('fornecedores', 'contratos', 'atas')}

        antes = contar()
        self.assertGreater(antes['contratos'], 0, 'sem dados para perder — teste inválido')

        corrompido = dict(backup)
        corrompido['contratos'] = ['isto-nao-e-um-dicionario']   # explode depois dos DELETEs
        status, _ = self.request('POST', '/api/backup/restore', corrompido, token=token)
        self.assertEqual(status, 500)
        self.assertEqual(contar(), antes,
                         'restauração que falhou apagou dados em vez de preservar o banco')


class TestBackupNaoVazaCredencial(SGCATestCase):
    """Regressão do eixo perda de dado (auditoria 2026-07-24).

    O backup JSON exportava `sys_settings` inteiro, e ali mora a senha do SMTP
    do sistema (texto puro) e a chave do Portal da Transparência. O arquivo sai
    do servidor — o manual orienta enviá-lo a outra máquina —, então essas
    credenciais circulavam junto. Restaurar não as perde: o que o arquivo não
    traz é preservado como já está no banco.
    """

    SEGREDO = 'SENHA-SMTP-DO-SISTEMA-XYZ'

    def _gravar_segredo(self):
        with server.get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO sys_settings (key,value) VALUES ('smtp_pass',?)",
                         (self.SEGREDO,))
            conn.commit()

    def _ler_segredo(self):
        with server.get_db() as conn:
            row = conn.execute("SELECT value FROM sys_settings WHERE key='smtp_pass'").fetchone()
        return row['value'] if row else None

    def test_backup_nao_contem_a_senha_do_smtp(self):
        token = self.login()
        self._gravar_segredo()
        status, backup = self.request('GET', '/api/backup', token=token)
        self.assertEqual(status, 200)
        self.assertNotIn(self.SEGREDO, json.dumps(backup, ensure_ascii=False),
                         'senha do SMTP do sistema vazou no arquivo de backup')

    def test_restaurar_preserva_a_senha_do_smtp(self):
        token = self.login()
        self._gravar_segredo()
        _, backup = self.request('GET', '/api/backup', token=token)
        self.assertEqual(self.request('POST', '/api/backup/restore', backup, token=token)[0], 200)
        self.assertEqual(self._ler_segredo(), self.SEGREDO,
                         'restaurar backup apagou a senha do SMTP do sistema')


class TestSenhaPadraoObrigatoria(SGCATestCase):
    """Regressão do eixo permissão/sigilo (auditoria 2026-07-24).

    A troca de senha obrigatória existia só no navegador: quem falasse direto
    com a API entrava com a senha padrão (que está no README e no manual) e
    usava o sistema inteiro, rotas de administrador inclusive.
    """

    def _usuario_pendente(self):
        adm = self.login()
        self.request('POST', '/api/usuarios',
                     {'username': 'pendente', 'nome': 'Pendente',
                       'password': 'senha123', 'senha': 'senha123', 'admin': True}, token=adm)
        with server.get_db() as conn:
            uid = conn.execute("SELECT id FROM usuarios WHERE username='pendente'").fetchone()['id']
            conn.execute('UPDATE usuarios SET must_change_password=1 WHERE id=?', (uid,))
            conn.commit()
        st, log = self.request('POST', '/api/auth/login', {'username': 'pendente', 'password': 'senha123'})
        self.assertEqual(st, 200, log)
        return log['token'], uid

    def test_api_recusa_enquanto_a_senha_nao_for_trocada(self):
        tok, _ = self._usuario_pendente()
        for rota in ('/api/contratos', '/api/usuarios', '/api/backup'):
            st, _ = self.request('GET', rota, token=tok)
            self.assertEqual(st, 403, f'{rota} respondeu {st} com a senha padrão pendente')

    def test_libera_o_que_a_tela_de_troca_precisa(self):
        tok, uid = self._usuario_pendente()
        self.assertEqual(self.request('GET', '/api/auth/me', token=tok)[0], 200)
        st, _ = self.request('PUT', f'/api/usuarios/{uid}', {'password': 'TrocadaAgora#2026'}, token=tok)
        self.assertEqual(st, 200, 'não deu para trocar a própria senha')
        st, log = self.request('POST', '/api/auth/login',
                               {'username': 'pendente', 'password': 'TrocadaAgora#2026'})
        self.assertEqual(st, 200)
        self.assertEqual(self.request('GET', '/api/contratos', token=log['token'])[0], 200,
                         'sistema continuou bloqueado depois de trocar a senha')


class TestAuditoriaDeConfiguracao(SGCATestCase):
    """Achado 9 do eixo permissão/sigilo (auditoria 2026-07-24).

    Dados de Organização e brasão seguem abertos a qualquer usuário autenticado
    — decisão de projeto —, mas saem em todo documento gerado. Sem registro na
    trilha, uma alteração no nome do órgão ou no brasão aparecia em documento
    oficial sem rastro de quem fez.
    """
    def _ids_config(self):
        with server.get_db() as conn:
            return {r['id'] for r in conn.execute(
                "SELECT id FROM audit_global WHERE type='CONFIG_ALTERADA'")}

    def _novos_desde(self, ids_antes):
        # Compara por conjunto de ids, não por contagem: o banco é compartilhado
        # pela suíte e outros testes também mexem em configuração.
        with server.get_db() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM audit_global WHERE type='CONFIG_ALTERADA'")
                if r['id'] not in ids_antes]

    def test_alterar_dados_da_organizacao_gera_evento(self):
        token = self.login()
        antes = self._ids_config()
        st, _ = self.request('PUT', '/api/settings/org',
                             {'orgao': f'Prefeitura {uuid.uuid4().hex[:8]}'}, token=token)
        self.assertEqual(st, 200)
        novos = self._novos_desde(antes)
        self.assertEqual(len(novos), 1, 'alteração não entrou na trilha')
        self.assertIn('orgao', novos[0]['detail'])
        self.assertEqual(novos[0]['label'], 'Dados da organização alterados')

    def test_reenviar_os_mesmos_valores_nao_polui_a_trilha(self):
        # A tela reenvia todos os campos a cada "Salvar"; sem alteração real não
        # deve virar evento.
        token = self.login()
        fixo = f'Prefeitura {uuid.uuid4().hex[:8]}'
        self.request('PUT', '/api/settings/org', {'orgao': fixo}, token=token)
        antes = self._ids_config()
        self.request('PUT', '/api/settings/org', {'orgao': fixo}, token=token)
        self.assertEqual(self._novos_desde(antes), [], 'reenvio sem alteração gerou evento')

    def test_alterar_brasao_gera_evento(self):
        token = self.login()
        antes = self._ids_config()
        st, _ = self.request('PUT', '/api/settings/brasao',
                             {'brasao_dataurl': 'data:image/png;base64,' + uuid.uuid4().hex}, token=token)
        self.assertEqual(st, 200)
        novos = self._novos_desde(antes)
        self.assertEqual(len(novos), 1)
        self.assertEqual(novos[0]['label'], 'Brasão alterado')

class TestAditivosRecalculo(SGCATestCase):
    """Eixo documentos/cálculos (auditoria 2026-07-24).

    Dois defeitos no mesmo ponto: remover um aditivo não desfazia a conta (o
    contrato seguia valendo um aditivo inexistente, com o percentual comparado
    ao teto legal errado), e acréscimo e supressão se anulavam no percentual —
    +25% seguido de -25% exibia 0%, escondendo que os dois tetos do art. 125
    tinham sido usados.
    """

    def _contrato(self, token, valor='100.000,00'):
        st, c = self.request('POST', '/api/contratos',
                             {'objeto': 'Contrato de teste', 'numero': f'{uuid.uuid4().hex[:6]}/2026',
                              'valorGlobal': valor}, token=token)
        self.assertEqual(st, 200, c)
        return c['id']

    def _ler(self, token, cid):
        st, c = self.request('GET', f'/api/contratos/{cid}', token=token)
        self.assertEqual(st, 200, c)
        return c

    def _aditivo(self, token, cid, valor):
        st, _ = self.request('POST', f'/api/contratos/{cid}/aditivos',
                             {'tipo': 'valor', 'valorVariacao': valor}, token=token)
        self.assertEqual(st, 200)

    def test_remover_aditivo_desfaz_valor_e_percentual(self):
        token = self.login()
        cid = self._contrato(token)
        self._aditivo(token, cid, '25.000,00')
        self._aditivo(token, cid, '10.000,00')
        c = self._ler(token, cid)
        self.assertEqual(c['valorGlobal'], 135000.0)
        self.assertEqual(c['percentualAcumulado'], 35.0)

        aid = c['aditivos'][-1]['id']
        st, _ = self.request('DELETE', f'/api/contratos/{cid}/aditivos/{aid}', token=token)
        self.assertEqual(st, 200)
        c = self._ler(token, cid)
        self.assertEqual(len(c['aditivos']), 1)
        self.assertEqual(c['valorGlobal'], 125000.0, 'valor global não voltou ao estado sem o aditivo')
        self.assertEqual(c['percentualAcumulado'], 25.0, 'percentual não voltou ao estado sem o aditivo')

    def test_acrescimo_e_supressao_nao_se_anulam(self):
        token = self.login()
        cid = self._contrato(token)
        self._aditivo(token, cid, '25.000,00')
        self._aditivo(token, cid, '-25.000,00')
        c = self._ler(token, cid)
        # o valor volta ao original, mas os dois tetos foram usados
        self.assertEqual(c['valorGlobal'], 100000.0)
        self.assertEqual(c['percentualAcrescimo'], 25.0)
        self.assertEqual(c['percentualSupressao'], 25.0)
        self.assertEqual(c['percentualAcumulado'], 25.0,
                         'acréscimo e supressão se anularam no percentual')


class TestConflitoDeEdicao(SGCATestCase):
    """Eixo concorrência (auditoria 2026-07-24).

    Contratos e atas não tinham detecção de conflito: duas pessoas salvando o
    mesmo registro recebiam 200 e a última apagava o trabalho da primeira.
    A base da comparação é o `_baseUpdatedAt` explícito ou o próprio
    `updatedAt` que a tela devolve dentro do objeto.
    """

    def _criar(self, token, rota):
        corpo = ({'objeto': 'Original', 'numero': f'{uuid.uuid4().hex[:6]}/2026'} if 'contratos' in rota
                 else {'numero': f'{uuid.uuid4().hex[:6]}/2026', 'objeto': 'Original'})
        st, it = self.request('POST', rota, corpo, token=token)
        self.assertEqual(st, 200, it)
        return it['id']

    def _checa(self, rota, rotulo):
        token = self.login()
        iid = self._criar(token, rota)
        st, carregado = self.request('GET', f'{rota}/{iid}', token=token)
        copia_a, copia_b = dict(carregado), dict(carregado)
        copia_a['objeto'] = 'Versão A'
        copia_b['objeto'] = 'Versão B'
        self.assertEqual(self.request('PUT', f'{rota}/{iid}', copia_a, token=token)[0], 200)
        st, _ = self.request('PUT', f'{rota}/{iid}', copia_b, token=token)
        self.assertEqual(st, 409, f'{rotulo}: cópia velha sobrescreveu')
        st, fim = self.request('GET', f'{rota}/{iid}', token=token)
        self.assertEqual(fim['objeto'], 'Versão A')
        # recarregar e salvar segue funcionando
        st, atual = self.request('GET', f'{rota}/{iid}', token=token)
        atual['objeto'] = 'Versão C'
        self.assertEqual(self.request('PUT', f'{rota}/{iid}', atual, token=token)[0], 200)

    def test_contrato_detecta_conflito(self):
        self._checa('/api/contratos', 'contrato')

    def test_ata_detecta_conflito(self):
        self._checa('/api/atas', 'ata')


class TestSenhaPadraoMarcadaNoBoot(SGCATestCase):
    """Regressão do eixo permissão/sigilo (auditoria 2026-07-24).

    Quem instalou antes da coluna must_change_password existir recebeu 0 pelo
    DEFAULT do ALTER TABLE: ficou com a senha do manual e sem o bloqueio do
    servidor, porque a marca de troca só é gravada na criação do admin. O boot
    precisa remarcar quem continua na senha padrão.
    """

    def _limpa(self):
        with server.get_db() as conn:
            conn.execute("DELETE FROM usuarios WHERE username='antigo'")
            conn.execute("UPDATE usuarios SET must_change_password=0 WHERE username='admin'")
            conn.commit()

    def _cria_e_reinicia(self, senha):
        self.addCleanup(self._limpa)
        with server.get_db() as conn:
            conn.execute(
                'INSERT INTO usuarios (username,nome,senha_hash,admin,ativo,must_change_password)'
                ' VALUES (?,?,?,0,1,0)',
                ('antigo', 'Instalacao antiga', server._hash_password(senha)))
            conn.commit()
        server.init_db()   # o que acontece a cada início do servidor
        with server.get_db() as conn:
            return conn.execute(
                "SELECT must_change_password FROM usuarios WHERE username='antigo'"
            ).fetchone()['must_change_password']

    def test_boot_marca_quem_ficou_na_senha_padrao(self):
        self.assertEqual(self._cria_e_reinicia('admin123'), 1,
                         'conta com a senha padrão seguiu sem exigir troca')

    def test_boot_nao_mexe_em_quem_ja_trocou(self):
        self.assertEqual(self._cria_e_reinicia('OutraSenha#2026'), 0,
                         'exigiu troca de quem já tinha saído da senha padrão')


class TestMotorErros(SGCATestCase):
    """Motor de captura e tratamento de erros (portado do piloto SGCD)."""

    def _raw(self, method, path, data, token=None):
        conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=10)
        hdrs = {'Content-Type': 'application/json'}
        if token: hdrs['Authorization'] = f'Bearer {token}'
        conn.request(method, path, body=data, headers=hdrs)
        resp = conn.getresponse(); body = resp.read(); conn.close()
        try: return resp.status, json.loads(body) if body else None
        except ValueError: return resp.status, body

    def test_param_invalido_400(self):
        tok = self.login()
        self.assertEqual(self.request('GET', '/api/fornecedores?per=abc', token=tok)[0], 400)

    def test_log_client_sem_auth_204(self):
        st, _ = self._raw('POST', '/api/log/client',
                          json.dumps({'msg': 'boom teste', 'view': 'view-x'}).encode())
        self.assertEqual(st, 204)

    def test_log_client_chega_no_log_e_diagnostico(self):
        tok = self.login()
        marca = f'erro-teste-{uuid.uuid4().hex[:8]}'
        self._raw('POST', '/api/log/client', json.dumps({'msg': marca, 'view': 'view-y'}).encode())
        caminho = server.sgx_base.caminho_log_erros(server._DATA_DIR, 'SGCA')
        with open(caminho, encoding='utf-8', errors='replace') as f:
            self.assertIn(marca, f.read())
        st, d = self.request('GET', '/api/diagnostico/erros', token=tok)
        self.assertEqual(st, 200)
        self.assertTrue(any('cliente-js' in g.get('tipo', '') for g in d['erros']))

    def test_diagnostico_so_admin(self):
        admin = self.login()
        self.request('POST', '/api/usuarios', {'username': 'u_diag_ca', 'nome': 'U', 'password': 'senha123'}, token=admin)
        comum = self.request('POST', '/api/auth/login', {'username': 'u_diag_ca', 'password': 'senha123'})[1]['token']
        self.assertEqual(self.request('GET', '/api/diagnostico/erros', token=comum)[0], 403)


class TestRecusaSenhaPadrao(SGCATestCase):
    """Não deixa definir a senha de fábrica como NOVA senha (ver sgx_base.eh_senha_padrao)."""

    def test_recusa_admin123_como_nova_senha(self):
        tok = self.login()
        with server.get_db() as conn:
            uid = conn.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()['id']
        st, r = self.request('PUT', f'/api/usuarios/{uid}', {'password': 'admin123'}, token=tok)
        self.assertEqual(st, 400, r)
        self.assertIn('padrão', (r or {}).get('error', ''))


class TestSyncFornecedor(SGCATestCase):
    """Cadastro de fornecedor compartilhado (2026-07): export + sync peer por CNPJ,
    last-write-wins com revisão manual (marca d'água syncedAt). Mesmo padrão do SGCD.
    CNPJs próprios por teste; confere só o que escreveu (banco compartilhado na suíte)."""

    def _set_data(self, cnpj_like, **kv):
        with server.get_db() as conn:
            row = conn.execute("SELECT id,data FROM fornecedores WHERE cnpj LIKE ?", (cnpj_like,)).fetchone()
            d = json.loads(row['data']); d.update(kv)
            conn.execute("UPDATE fornecedores SET data=? WHERE id=?", (json.dumps(d), row['id'])); conn.commit()

    def test_export_envelope(self):
        tok = self.login()
        self.request('POST', '/api/fornecedores', {'cnpj': '90.101.001/0001-00', 'razao_social': 'ExpA', 'updatedAt': 1000}, token=tok)
        st, d = self.request('GET', '/api/fornecedores/export', token=tok)
        self.assertEqual(st, 200)
        self.assertEqual((d['_sgx'], d['tipo']), ('SGCA', 'fornecedores'))
        self.assertTrue(any((f.get('cnpj') or '').startswith('90.101') for f in d['fornecedores']))

    def test_preview_apply(self):
        tok = self.login()
        self.request('POST', '/api/fornecedores', {'cnpj': '90.102.001/0001-00', 'razao_social': 'Base', 'updatedAt': 1000}, token=tok)
        self._set_data('90.102.001%', syncedAt=1000)
        arq = {'tipo': 'fornecedores', 'fornecedores': [
            {'cnpj': '90.102.002/0001-00', 'razao_social': 'Novo', 'updatedAt': 2000},
            {'cnpj': '90.102.001/0001-00', 'razao_social': 'Base Ltda', 'updatedAt': 5000}]}
        st, prev = self.request('POST', '/api/fornecedores/sync/preview', arq, token=tok)
        self.assertEqual((prev['inserir'], prev['atualizar'], len(prev['conflitos'])), (1, 1, 0))
        st, ap = self.request('POST', '/api/fornecedores/sync/apply', arq, token=tok)
        self.assertEqual((ap['novos'], ap['atualizados']), (1, 1))
        st, lst = self.request('GET', '/api/fornecedores?per=2000', token=tok)
        nomes = {f.get('cnpj'): f.get('razao_social') for f in lst['items']}
        self.assertEqual(nomes.get('90.102.001/0001-00'), 'Base Ltda')
        self.assertEqual(nomes.get('90.102.002/0001-00'), 'Novo')

    def test_conflito_resolve_arquivo(self):
        tok = self.login()
        self.request('POST', '/api/fornecedores', {'cnpj': '90.103.001/0001-00', 'razao_social': 'Local', 'updatedAt': 5000}, token=tok)
        self._set_data('90.103.001%', syncedAt=1000)
        arq = {'tipo': 'fornecedores', 'fornecedores': [{'cnpj': '90.103.001/0001-00', 'razao_social': 'Remoto', 'updatedAt': 3000}]}
        st, prev = self.request('POST', '/api/fornecedores/sync/preview', arq, token=tok)
        self.assertEqual(len(prev['conflitos']), 1)
        st, ap = self.request('POST', '/api/fornecedores/sync/apply',
                              {**arq, 'resolver': {'90103001000100': 'arquivo'}}, token=tok)
        self.assertEqual(ap['conflitos_aplicados'], 1)
        st, lst = self.request('GET', '/api/fornecedores?per=2000', token=tok)
        alvo = next(f for f in lst['items'] if (f.get('cnpj') or '').startswith('90.103.001'))
        self.assertEqual(alvo['razao_social'], 'Remoto')

    def test_arquivo_invalido(self):
        tok = self.login()
        self.assertEqual(self.request('POST', '/api/fornecedores/sync/preview', {'foo': 1}, token=tok)[0], 400)


class TestBackupCofre(SGCATestCase):
    """Padronização do backup (2026-07): Cofre .zip (banco + anexos) via sgx_base,
    com leitura retrocompatível do .db legado. O round-trip de anexos em si é
    coberto pela suíte do SGDP (mesmo helper compartilhado)."""

    def _raw(self, method, path, data, token):
        conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=15)
        hdrs = {'Content-Length': str(len(data))}
        if token: hdrs['Authorization'] = f'Bearer {token}'
        conn.request(method, path, body=data, headers=hdrs)
        resp = conn.getresponse(); body = resp.read(); conn.close()
        try: return resp.status, json.loads(body)
        except ValueError: return resp.status, body

    def test_cofre_e_zip_com_banco(self):
        token = self.login()
        self.request('POST', '/api/contratos', {'objeto': 'Contrato do Cofre'}, token=token)
        st, raw = self.request('GET', '/api/backup/db', token=token)
        self.assertEqual(st, 200)
        self.assertEqual(raw[:4], b'PK\x03\x04')
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertIn('banco.db', z.namelist())

    def test_restaura_cofre_zip(self):
        token = self.login()
        self.request('POST', '/api/contratos', {'objeto': 'Contrato que volta do Cofre'}, token=token)
        _, raw = self.request('GET', '/api/backup/db', token=token)
        st, d = self._raw('POST', '/api/backups/db/restore', raw, token)
        self.assertEqual(st, 200, d)
        st, listado = self.request('GET', '/api/contratos', token=token)
        self.assertTrue(any(c['objeto'] == 'Contrato que volta do Cofre' for c in listado['items']))

    def test_restore_aceita_db_legado(self):
        token = self.login()
        legado = os.path.join(server.BACKUP_DIR, 'legado.db')
        s = sqlite3.connect(server.DB_PATH); k = sqlite3.connect(legado)
        try:
            with k: s.backup(k)
        finally:
            s.close(); k.close()
        with open(legado, 'rb') as f: db_bytes = f.read()
        os.remove(legado)
        st, d = self._raw('POST', '/api/backups/db/restore', db_bytes, token)
        self.assertEqual(st, 200, d)

    def test_arquivos_invalidos_recusados(self):
        token = self.login()
        self.assertEqual(self.request('POST', '/api/backup/restore', {'foo': 1}, token=token)[0], 400)
        self.assertEqual(self._raw('POST', '/api/backups/db/restore', b'lixo', token)[0], 400)


if __name__ == '__main__':
    unittest.main()
