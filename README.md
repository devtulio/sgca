# SGCA — Sistema de Gestão de Contratos e Atas

![Versão](https://img.shields.io/badge/versão-v0.6.0-blue) ![Tecnologia](https://img.shields.io/badge/tecnologia-Python%20%2B%20SQLite-orange) ![Licença](https://img.shields.io/badge/licença-MIT-green) ![Multiusuário](https://img.shields.io/badge/acesso-multiusuário-blueviolet)

## Descrição

O **SGCA** é uma aplicação web multiusuário para o **Departamento de Gestão e Contratos**, destinada ao controle de **Contratos Administrativos** e **Atas de Registro de Preços** conforme a Lei nº 14.133/2021.

O sistema nasceu como uma adaptação estrutural do SGCD (Sistema de Gestão de Contratação Direta), reaproveitando os módulos administrativos que não são específicos de nenhum tipo de processo — autenticação, usuários, fornecedores, auditoria, notificações e backup — e tendo sua arquitetura posteriormente padronizada com a do SGDP (Sistema de Gestão de Documentos da Procuradoria), o "irmão" mais maduro da mesma família de sistemas.

Funciona em rede local: um único computador executa o servidor e todos os usuários acessam pelo navegador via IP ou `localhost`.

---

## Funcionalidades Já Prontas

- **Contratos** — cadastro, Kanban por status (Vigente/Em prorrogação/Encerrado/Rescindido), vínculo com fornecedor, aditivos e apostilamentos com alerta de limite legal de 25% (Art. 125, Lei nº 14.133/2021)
- **Atas de Registro de Preços** — cadastro, itens registrados com controle de saldo (quantidade utilizada vs. registrada) e alerta visual de esgotamento; vigência final calculada automaticamente a partir da data de assinatura (+12 meses), editável manualmente
- **Documentos gerados** — Extrato de Contrato e Termo Aditivo/Apostilamento (um por tipo: prazo, valor, qualitativo, reequilíbrio, repactuação), no mesmo padrão visual A4 do SGCD
- **Exportação PNCP** — JSON de Contratos e de Atas no formato esperado pelo Portal Nacional de Contratações Públicas, com aviso de campos pendentes
- **Agenda de Vencimentos** unificada — contratos, atas e garantias contratuais vencendo, agrupados por urgência, com envio manual ou automático (resumo diário) por e-mail, incluindo aviso individual ao fiscal cadastrado no contrato
- **Exportação de Contratos e Atas em CSV** para planilha
- **Garantia Contratual** — modalidade, valor, vencimento e devolução, com alerta na Agenda de Vencimentos
- **Sanções e Penalidades** — registro interno por fornecedor (advertência, multa, suspensão, impedimento, inidoneidade), com aviso ao selecionar um fornecedor sancionado em um Contrato/Ata e entrada do fim do prazo na Agenda de Vencimentos
- **Reajuste por índice** (IPCA-E, IGP-M, INCC-M, INPC) em aditivos de repactuação/reequilíbrio, com cálculo automático do novo valor global
- **Anexo do contrato assinado (PDF)** vinculado ao registro do contrato
- **Vínculo Contrato ↔ Ata de Registro de Preços** — campo "Ata de Origem" para contratações por adesão
- **Relatórios consolidados** de Contratos, Atas e Sanções por fornecedor, no mesmo padrão A4 usado nos demais documentos
- **Indicadores na tela de Contratos** — contratos vigentes, vencendo em 30 dias, valor total vigente e atas com saldo baixo
- **Autenticação multiusuário** com hashing PBKDF2-HMAC-SHA256 e gestão de usuários pelo admin
- **Cadastro de fornecedores** com consulta automática de CNPJ via ReceitaWS/BrasilAPI, controle de certidões com alertas de vencimento e exclusão (lixeira)
- **Importação de fornecedores via CSV** e relatório consolidado
- **Configurações** — dados do órgão, brasão, tema claro/escuro, SMTP
- **Notificações in-app** — alertas de certidões de fornecedores vencendo
- **Trilha de auditoria global** — tabela com filtros por tipo de evento, período e usuário (vocabulário próprio do domínio de contratos/atas)
- **Backup automático** ao encerrar o sistema (JSON + banco de dados SQLite) com rotação configurável
- **Sincronização de fornecedores entre agentes/máquinas** — mescla dados de outra instalação sem substituir o banco inteiro
- **Lixeira** — fornecedores, contratos e atas excluídos ficam recuperáveis por 30 dias
- **Diagnóstico e correção automática de rede** — verifica IP, porta, perfil de rede e firewall

> Fora de escopo por decisão de projeto: controle de empenhos/pagamentos (fica a cargo do sistema contábil/financeiro do órgão).

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
