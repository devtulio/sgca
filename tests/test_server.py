# Suíte de testes do backend (server.py) — sobe o servidor real contra um
# banco/uploads/backups temporários e bate nos endpoints REST via http.client.
# python -m unittest discover -s tests   (ou: python tests/test_server.py)
import base64
import http.client
import json
import os
import shutil
import socketserver
import sys
import tempfile
import threading
import unittest

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
    server._modo_servidor = True  # evita os._exit(0) do watchdog em logout (não usado aqui, mas por segurança)
    server.init_db()

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
        self.assertTrue(data['_sgca'])
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
                      'fiscalEmail': 'fiscal@teste.com'}, token=token)

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


class TestHealth(SGCATestCase):

    def test_health_check(self):
        status, data = self.request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertTrue(data['ok'])


if __name__ == '__main__':
    unittest.main()
