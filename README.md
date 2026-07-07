# SGCA — Sistema de Gestão de Contratos e Atas

![Versão](https://img.shields.io/badge/versão-v0.3.3-blue) ![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow) ![Tecnologia](https://img.shields.io/badge/tecnologia-Python%20%2B%20SQLite-orange) ![Licença](https://img.shields.io/badge/licença-MIT-green) ![Multiusuário](https://img.shields.io/badge/acesso-multiusuário-blueviolet)

## Descrição

O **SGCA** é uma aplicação web multiusuário em desenvolvimento para o **Departamento de Gestão e Contratos**, destinada ao controle de **Contratos Administrativos** e **Atas de Registro de Preços**.

O sistema nasceu como uma adaptação estrutural do SGCD (Sistema de Gestão de Contratação Direta), reaproveitando os módulos administrativos que não são específicos de nenhum tipo de processo — autenticação, usuários, fornecedores, auditoria, notificações e backup. O módulo de domínio (cadastro e acompanhamento de Contratos e Atas) ainda está em construção.

Funciona em rede local: um único computador executa o servidor e todos os usuários acessam pelo navegador via IP ou `localhost`.

---

## Funcionalidades Já Prontas

- **Autenticação multiusuário** com hashing PBKDF2-HMAC-SHA256 e gestão de usuários pelo admin
- **Cadastro de fornecedores** com consulta automática de CNPJ via ReceitaWS/BrasilAPI e controle de certidões com alertas de vencimento
- **Importação de fornecedores via CSV** e relatório consolidado
- **Configurações** — dados do órgão, brasão, tema claro/escuro, SMTP
- **Notificações por e-mail via SMTP** com editor rich text
- **Notificações in-app** — alertas de certidões vencendo
- **Trilha de auditoria global** com timeline agrupada por dia e filtros por tipo de evento, período e usuário
- **Backup automático** ao encerrar o sistema (JSON + banco de dados SQLite) com rotação configurável
- **Sincronização de backup entre agentes/máquinas** — mescla dados de outra instalação sem substituir o banco inteiro
- **Lixeira** — itens excluídos ficam recuperáveis por 30 dias
- **Diagnóstico e correção automática de rede** — verifica IP, porta, perfil de rede e firewall

## Em Desenvolvimento

O módulo de domínio do sistema — cadastro de **Contratos Administrativos** e **Atas de Registro de Preços**, com vigências, aditivos, apostilamentos, prorrogações, fiscais/gestores designados, alertas de vencimento e geração de documentos — ainda não foi implementado. Este README será atualizado conforme o módulo for lançado.

---

## Requisitos

- **Python 3.7+** (apenas biblioteca padrão — zero dependências externas)
- **Google Chrome** ou **Microsoft Edge** (recomendado)
- Windows 10/11

> **Servidor sem Python instalado (ex.: Windows Server bloqueado por política de TI):**
> o `Iniciar SGCA.bat` detecta automaticamente a ausência do Python e extrai uma versão portátil (embarcável, sem instalador) incluída no próprio projeto (`python-3.12.9-embed-amd64.zip`) para `C:\Python312-embed\` — não exige instalação nem privilégio de administrador.

---

## Instalação e uso

1. Copie a pasta `SGCA/` para o computador que atuará como servidor
2. Clique duas vezes em **`Iniciar SGCA.bat`**
3. Selecione o modo de operação no menu que aparecer
4. Faça login com as credenciais iniciais abaixo e **altere a senha imediatamente**

> ⚠️ **Importante:** abrir o `SGCA.html` diretamente pelo navegador (sem o servidor) impede o funcionamento do sistema. Use sempre o `Iniciar SGCA.bat`.

### Login inicial

| Campo   | Valor       |
|---------|-------------|
| Usuário | `admin`     |
| Senha   | `admin123`  |

### Modo de operação

| Opção | Descrição |
|-------|-----------|
| **[1] Pessoal** | Uso individual — abre o navegador automaticamente e encerra ao sair |
| **[2] Servidor** | Máquina central em rede — fica rodando continuamente (Ctrl+C para parar) |
| **[3] Diagnóstico** | Verifica e corrige automaticamente rede, porta e firewall (pede elevação de Administrador quando necessário) |

### Acesso em rede local

Outros usuários acessam pelo IP do computador servidor:

```
http://192.168.x.x:3002/SGCA.html
```

Execute **`Diagnostico SGCA.bat`** (ou a opção **[3]** do `Iniciar SGCA.bat`) para descobrir o IP e verificar/corrigir automaticamente firewall e perfil de rede.

---

## Estrutura de arquivos

```
SGCA/
├── SGCA.html                # Frontend — aplicação web
├── server.py                # Servidor Python (API REST + SQLite) — porta 3002
├── Iniciar SGCA.bat          # Inicializa o servidor
├── python-3.12.9-embed-amd64.zip  # Python portátil (fallback se não houver Python instalado)
├── Criar Atalho SGCA.bat     # Cria atalho na área de trabalho com ícone
├── Criar Atalho SGCA.ps1     # Script PowerShell de criação do atalho
├── Diagnostico SGCA.bat      # Roda o diagnóstico de rede (clique duplo)
├── Liberar Porta SGCA.bat    # Cria regra de firewall para a porta (Admin)
├── diagnostico.py            # Script de diagnóstico de rede e firewall
├── sgca.ico                  # Ícone do sistema
├── sgca.db                   # Banco de dados SQLite (criado automaticamente)
├── backups/                  # Backups automáticos (criado automaticamente)
├── README.md
├── CHANGELOG.md
└── MANUAL.html
```

---

## Segurança

- Senhas armazenadas com **PBKDF2-HMAC-SHA256** e salt aleatório por usuário
- Sessões server-side invalidadas automaticamente por inatividade
- Acesso à API exige token de sessão em todas as rotas (exceto login)
- Trilha de auditoria imutável registra todas as ações com usuário e timestamp
- Verificação de integridade do banco de dados (SQLite `PRAGMA integrity_check`) na inicialização
- Recomenda-se uso em rede interna (LAN) apenas

---

## Tecnologias

| Tecnologia | Uso |
|-----------|-----|
| **HTML5 + CSS3** | Interface da aplicação, temas claro/escuro, layout responsivo |
| **JavaScript puro (ES6+)** | Toda a lógica de negócio, sem frameworks externos |
| **Python 3 (stdlib)** | Servidor local: REST API, SQLite, auth, SMTP, proxy CNPJ |
| **SQLite** | Armazenamento persistente dos dados (`sgca.db`) |
| **ReceitaWS / BrasilAPI** | Consulta de CNPJ (primária + fallback automático) |
| **ViaCEP** | Preenchimento automático de endereço por CEP |

---

## Desenvolvimento

O sistema em si continua zero-dependência (Python stdlib + HTML puro). Para quem for alterar o código, há um lint opcional que verifica variáveis indefinidas no JavaScript de `SGCA.html`:

```bash
npm install   # uma vez, instala apenas o ESLint (ferramenta de dev, não é usada em produção)
npm run lint
```

Há também uma suíte de testes automatizados do backend (`server.py`), usando só `unittest` da stdlib:

```bash
python -m unittest discover -s tests -v
```

---

## Versionamento

Consulte o [CHANGELOG.md](CHANGELOG.md) para o histórico completo de versões e alterações.

---

## Contribuição

Contribuições são bem-vindas! Veja o [CONTRIBUTING.md](CONTRIBUTING.md) para orientações sobre como reportar bugs, sugerir funcionalidades e enviar Pull Requests.

---

## Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE) para o texto completo.

> **Aviso:** Os dados ficam armazenados no arquivo `sgca.db` na pasta do sistema. Faça backups regulares em **Configurações → Backup de Dados** e mantenha cópia do `sgca.db` em local seguro.
