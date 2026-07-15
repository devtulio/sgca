# SGCA — Sistema de Gestão de Contratos e Atas

![Versão](https://img.shields.io/badge/versão-v0.27.0-blue) ![Lei](https://img.shields.io/badge/Lei-14.133%2F2021-green) ![Tecnologia](https://img.shields.io/badge/tecnologia-Python%20%2B%20SQLite-orange) ![Licença](https://img.shields.io/badge/licença-MIT-green) ![Multiusuário](https://img.shields.io/badge/acesso-multiusuário-blueviolet) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21314676.svg)](https://doi.org/10.5281/zenodo.21314676) [![CI](https://github.com/devtulio/sgca/actions/workflows/ci.yml/badge.svg)](https://github.com/devtulio/sgca/actions/workflows/ci.yml)

## Descrição

O **SGCA** é uma aplicação web multiusuário para o **Departamento de Gestão e Contratos**, destinada ao controle de **Contratos Administrativos** e **Atas de Registro de Preços** conforme a Lei nº 14.133/2021.

O sistema nasceu como uma adaptação estrutural do SGCD (Sistema de Gestão de Contratação Direta), reaproveitando os módulos administrativos que não são específicos de nenhum tipo de processo — autenticação, usuários, fornecedores, auditoria, notificações e backup — e tendo sua arquitetura posteriormente padronizada com a do SGDP (Sistema de Gestão de Documentos da Procuradoria), o "irmão" mais maduro da mesma família de sistemas.

Funciona em rede local: um único computador executa o servidor e todos os usuários acessam pelo navegador via IP ou `localhost`.

---

## Funcionalidades Principais

- **Dashboard geral** — primeira tela após o login, com indicadores consolidados de Contratos e Atas, gráfico de vencimentos dos próximos 6 meses e lista dos próximos vencimentos (contratos, atas, garantias e sanções)
- **Contratos** — cadastro, Kanban por status (Vigente/Em prorrogação/Encerrado/Rescindido), vínculo com fornecedor, aditivos e apostilamentos com alerta de limite legal de 25% (Art. 125, Lei nº 14.133/2021); vigência final calculada automaticamente a partir da vigência inicial (+12 meses), editável manualmente
- **Atas de Registro de Preços** — cadastro, itens registrados com código e classificação CMMET (Catálogo Municipal de Materiais e Especificações Técnicas), unidade SCPI, apresentação comercial e controle de saldo (quantidade utilizada vs. registrada) com alerta visual de esgotamento; vigência final calculada automaticamente a partir da data de assinatura (+12 meses), editável manualmente
- **Documentos gerados** — Extrato de Contrato e Termo Aditivo/Apostilamento (um por tipo: prazo, valor, qualitativo, reequilíbrio, repactuação), no mesmo padrão visual A4 do SGCD
- **Exportação PNCP** — JSON de Contratos e de Atas no formato esperado pelo Portal Nacional de Contratações Públicas, com aviso de campos pendentes
- **Agenda de Vencimentos** unificada — contratos, atas e garantias contratuais vencendo, agrupados por urgência, com envio manual ou automático (resumo diário) por e-mail, incluindo aviso individual ao fiscal cadastrado no contrato
- **Exportação de Contratos, Atas, Fornecedores e Trilha de Auditoria em CSV** para planilha, respeitando os filtros ativos na tela
- **Garantia Contratual** — modalidade, valor, vencimento e devolução, com alerta na Agenda de Vencimentos
- **Sanções e Penalidades** — registro interno por fornecedor (advertência, multa, suspensão, impedimento, inidoneidade), com aviso ao selecionar um fornecedor sancionado em um Contrato/Ata e entrada do fim do prazo na Agenda de Vencimentos
- **Reajuste por índice** (IPCA-E, IGP-M, INCC-M, INPC) em aditivos de repactuação/reequilíbrio, com busca automática da variação acumulada no período direto do Banco Central (SGS) e cálculo automático do novo valor global
- **Anexos assinados (PDF, múltiplos)** vinculados ao registro do contrato e da ata
- **Vínculo Contrato ↔ Ata de Registro de Preços** — campo "Ata de Origem" para contratações por adesão a uma ARP nossa; para adesão a ARP de outro órgão gerenciador (não cadastrada no sistema), campos de texto "Nº da ARP de Adesão" e "Órgão Gerenciador de Origem"
- **Gestor do Contrato com e-mail** — recebe o mesmo aviso automático de vencimento e de fiscalização mensal pendente que o fiscal
- **Relatórios consolidados** de Contratos, Atas e Sanções (por fornecedor ou global), no mesmo padrão A4 usado nos demais documentos
- **Indicadores e gráfico de vencimentos** nas telas de Contratos e de Atas — vigentes, vencendo em 30 dias, valor total, saldo baixo e vencimentos dos próximos 6 meses
- **Atalho "Ver Contratos"** a partir do cadastro do fornecedor, e prorrogação assistida (sugestão automática de nova vigência ao criar aditivo de prazo)
- **Numeração automática sugerida** e validação de número duplicado ao cadastrar Contrato/Ata
- **Filtro por Fiscal** na tela de Contratos, e alerta de "Contratos sem Fiscal" no Dashboard (Art. 117, Lei 14.133/2021)
- **Busca global** (botão na sidebar ou atalho Ctrl+K) — pesquisa por número, objeto, órgão gerenciador e fornecedor em todos os Contratos e Atas, com acesso direto ao registro
- **Histórico do registro** — botão "🕘 Histórico" no Contrato/Ata mostra a trilha de auditoria filtrada só para aquele registro
- **Fiscalização Mensal** no Contrato — data, fiscal, parecer e observações, com alerta "Fiscalização Atrasada" no Dashboard quando um contrato vigente fica mais de 45 dias sem registro (Art. 117)
- **Matriz de Risco** do Contrato — riscos com probabilidade, impacto, mitigação e responsável, com documento gerável (Art. 22)
- **Recebimento do Objeto** — datas e responsáveis pelo recebimento provisório e definitivo, com Termo de Recebimento gerável (Art. 140)
- **Subcontratação** — CNPJ, razão social e percentual do subcontratado, com alerta se o total ultrapassar o limite definido para o contrato (Art. 122)
- **Item do Plano de Contratações Anual (PCA)** — campo de rastreabilidade no Contrato (Art. 12, Lei 14.133/2021 / IN SEGES nº 81/2022)
- **Alerta de vigência total próxima do limite legal** — soma da vigência inicial com todas as prorrogações, aviso configurável por contrato (Art. 107)
- **Aniversário de reajuste** na Agenda de Vencimentos — lembrete 12 meses após o último aditivo de reequilíbrio/repactuação (ou desde a assinatura, se nunca houve um)
- **Lembrete de Fiscalização Mensal por e-mail** — aviso automático ao fiscal e ao gestor quando o contrato passa 30 dias sem registro de fiscalização
- **Assinatura de documentos gerados** — Extrato, Termos Aditivos, Matriz de Risco e Termo de Recebimento podem ser salvos como PDF e reanexados ao contrato para assinatura com certificado ICP-Brasil, reaproveitando o mesmo fluxo dos anexos
- **Autenticação multiusuário** com hashing PBKDF2-HMAC-SHA256 e gestão de usuários pelo admin
- **Cadastro de fornecedores** com consulta automática de CNPJ via ReceitaWS/BrasilAPI, controle de certidões com alertas de vencimento e exclusão (lixeira) — bloqueada enquanto o fornecedor tiver contratos ou atas vinculados
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
- Opcional: `pip install -r requirements.txt` — só necessário para o módulo de assinatura com certificado ICP-Brasil (`pyhanko`)

> **Servidor sem Python instalado (ex.: Windows Server bloqueado por política de TI):**
> o `Iniciar SGCA.bat` detecta automaticamente a ausência do Python e extrai uma versão portátil (embarcável, sem instalador) incluída no próprio projeto (`python-3.12.9-embed-amd64.zip`) para `C:\Python312-embed\` — não exige instalação nem privilégio de administrador.
>
> Essa versão portátil não vem com `pip` pronto (limitação do próprio pacote embarcável do Python). Se esse servidor precisar do módulo de assinatura ICP-Brasil, rode **`Instalar Assinatura ICP-Brasil.bat`** depois — ele habilita o pip e instala o `pyhanko` (requer acesso à internet só nesse momento, para baixar do PyPI).

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

O sistema foi projetado para uso multiusuário em rede local (LAN): **uma única máquina executa o servidor** (e guarda o banco de dados) e as demais acessam pelo navegador, sem instalar nada.

**Na máquina servidora (uma vez só):**

1. Execute **`Liberar Porta SGCA.bat`** como Administrador (botão direito → *Executar como administrador*) — cria a regra no Firewall do Windows liberando a porta 3002 para conexões de entrada
2. Inicie o sistema pelo `Iniciar SGCA.bat` e deixe a máquina ligada — ao iniciar, o console mostra o endereço de rede pronto para distribuir (`Rede: http://<IP>:3002/SGCA.html`)

**Nas outras máquinas:** basta abrir o navegador (Chrome ou Edge) no endereço do servidor:

```
http://192.168.x.x:3002/SGCA.html
```

Cada usuário faz login com sua própria conta — o servidor atende acessos simultâneos e todos enxergam os mesmos dados.

Se a conexão não funcionar, execute **`Diagnostico SGCA.bat`** (ou a opção **[3]** do `Iniciar SGCA.bat`) na máquina servidora: ele descobre o IP e verifica/corrige automaticamente firewall e perfil de rede.

> ⚠️ **Uso restrito à rede interna.** A comunicação é HTTP simples (sem criptografia de transporte) — adequado para uma LAN interna confiável, mas **nunca exponha a porta do sistema à internet** (redirecionamento de porta no roteador, DMZ etc.). Para acesso remoto, use a VPN institucional.

---

## Estrutura de arquivos

```
SGCA/
├── SGCA.html                # Frontend — aplicação web
├── server.py                # Servidor Python (API REST + SQLite) — porta 3002
├── tests/                    # Suíte de testes automatizados do backend
│   ├── test_server.py
│   └── e2e/                  # Testes E2E (Playwright) — navegador real de ponta a ponta
├── Iniciar SGCA.bat          # Inicializa o servidor
├── python-3.12.9-embed-amd64.zip  # Python portátil (fallback se não houver Python instalado)
├── Instalar Assinatura ICP-Brasil.bat  # Opcional — instala pip + pyhanko no Python embarcável
├── get-pip.py                # Usado só pelo script acima (Python embarcável não vem com pip)
├── Criar Atalho SGCA.bat     # Cria atalho na área de trabalho com ícone
├── Criar Atalho SGCA.ps1     # Script PowerShell de criação do atalho
├── Diagnostico SGCA.bat      # Roda o diagnóstico de rede (clique duplo)
├── Liberar Porta SGCA.bat    # Cria regra de firewall para a porta (Admin)
├── diagnostico.py            # Script de diagnóstico de rede e firewall
├── sgca.ico                  # Ícone do sistema
├── sgca.db                   # Banco de dados SQLite (criado automaticamente)
├── uploads/                  # Anexos armazenados (criado automaticamente)
├── backups/                  # Backups automáticos (criado automaticamente)
├── browser-profile/          # Perfil do Chrome/Edge no Modo Pessoal (criado automaticamente)
├── requirements.txt          # Dependência opcional (pyhanko — só p/ assinatura ICP-Brasil)
├── README.md
├── CHANGELOG.md
└── MANUAL.html
```

---

## Segurança

- Senhas armazenadas com **PBKDF2-HMAC-SHA256** e salt aleatório por usuário
- Sessões server-side invalidadas automaticamente por inatividade
- Acesso à API exige token de sessão em todas as rotas (exceto login e verificação)
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

Há também uma suíte de testes automatizados do backend (`server.py`), usando só `unittest` da stdlib — sobe o servidor real contra um banco e uploads temporários e testa os endpoints REST (login, contratos, atas, fornecedores, auditoria, configurações, usuários, backup):

```bash
python -m unittest discover -s tests -v
```

Há também uma suíte de testes E2E (`tests/e2e/`), usando Playwright — sobe o servidor real e dirige um Chromium de verdade pelo fluxo completo (login com troca de senha obrigatória, criar contrato):

```bash
npm install
npx playwright install chromium   # uma vez, baixa o navegador de teste
npm run test:e2e
```

Roda contra um banco/uploads/backups temporários (nunca o `sgca.db` real), criados e descartados automaticamente a cada execução.

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
