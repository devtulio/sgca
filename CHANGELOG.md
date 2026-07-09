# Changelog — SGCA
## Sistema de Gestão de Contratos e Atas
> Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
> Versionamento semântico: [SemVer](https://semver.org/lang/pt-BR/)

---

## [0.15.2] — 2026-07-09

### Alterado
- **Modal do Contrato mais largo** (de 640px para 760px) e ajuste na proporção de duas linhas de campos ("Limite de Vigência" e "Recebimento do Objeto") — os rótulos mais longos quebravam em duas linhas nas colunas mais estreitas

---

## [0.15.1] — 2026-07-09

### Corrigido
- **Alertas de limite sem estilo na tela** — os avisos de vigência total (Art. 107), subcontratação acima do limite (Art. 122) e variação acumulada de aditivos (Art. 125) usavam classes (`.aviso`/`.nota`) que só existem na folha de estilo dos documentos impressos; fora desse contexto apareciam como texto simples, sem nenhuma cor de destaque. Corrigido com o mesmo padrão inline já usado no aviso de fornecedor sancionado
- **Cards do Dashboard sem cor de status no modo escuro** — duas regras CSS concorrentes definiam o fundo/borda de `.stat` no tema escuro; a que sempre vencia não tinha variantes para `.blocked`/`.brand`, deixando cards como "Contratos sem Fiscal", "Fiscalização Atrasada" e "Contratos Vigentes" com borda cinza neutra em vez da cor de status
- **Botões `.btn-outline` com fundo branco fixo no modo escuro** — afetava todo botão outline do sistema (Cancelar, Gerar Extrato, Histórico, Exportar PNCP etc.), não só os das funcionalidades novas; cor de texto e borda já se adaptavam ao tema escuro, só o fundo ficou esquecido

---

## [0.15.0] — 2026-07-09

### Adicionado
- **Item do Plano de Contratações Anual (PCA)** — novo campo no Contrato, junto de Nº do Contrato/Processo Administrativo, para rastreabilidade exigida pela IN SEGES nº 81/2022 (Art. 12, Lei 14.133/2021)
- **Alerta de vigência total próxima do limite legal** (Art. 107) — campo "Limite de Vigência (anos)" no Contrato; soma a vigência inicial com as prorrogações acumuladas e avisa quando o total se aproxima ou ultrapassa o limite informado
- **Aniversário de reajuste** na Agenda de Vencimentos — novo tipo de evento lembrando, 12 meses após o último aditivo de reequilíbrio/repactuação (ou desde a assinatura, se nunca houve um), que o contrato pode ter direito a reajuste
- **Lembrete de Fiscalização Mensal por e-mail** — o job diário de alertas (que já avisa vencimentos) passa a notificar também o fiscal titular/substituto quando o contrato ficar 30+ dias sem registro de fiscalização
- **Assinatura eletrônica dos documentos gerados** — Extrato de Contrato, Termos Aditivos, Matriz de Risco e Termo de Recebimento ganham um campo para reanexar o PDF (depois de salvo pelo diálogo de impressão do navegador) diretamente na lista de Anexos do Contrato, de onde já é possível assinar com certificado ICP-Brasil pelo fluxo existente — sem exigir conversão de HTML para PDF no servidor

---

## [0.14.0] — 2026-07-09

### Adicionado
- **Busca automática do índice de reajuste** — no aditivo de reequilíbrio/repactuação, botão "🔍 Buscar no Banco Central" consulta a API pública do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central e preenche sozinho a variação % acumulada no período informado (IPCA-E, IGP-M, INPC ou INCC-M), em vez de exigir digitação manual
- **Fiscalização Mensal** (Art. 117, Lei 14.133/2021) — nova seção no Contrato para registrar data, fiscal responsável, parecer (conforme/não conforme) e observações de cada fiscalização; novo indicador "Fiscalização Atrasada" no Dashboard, contando contratos vigentes sem registro de fiscalização há mais de 45 dias
- **Matriz de Risco** (Art. 22, Lei 14.133/2021) — lista de riscos do Contrato (descrição, probabilidade, impacto, mitigação, responsável), com botão "⚠️ Matriz de Risco" gerando documento A4 no mesmo padrão dos demais
- **Recebimento do Objeto** (Art. 140, Lei 14.133/2021) — datas e responsáveis pelo recebimento provisório e definitivo no Contrato, com botão "📥 Termo de Recebimento" gerando o documento correspondente
- **Subcontratação** (Art. 122, Lei 14.133/2021) — registro de CNPJ, razão social, percentual e objeto de cada subcontratação no Contrato, com limite configurável por contrato e alerta quando o total subcontratado ultrapassa o limite definido

---

## [0.13.0] — 2026-07-09

### Adicionado
- **Busca global (Ctrl+K)** — botão "Buscar" na sidebar e atalho Ctrl+K abrem um modal de busca unificada por Contratos e Atas (número, objeto, órgão gerenciador, fornecedor), igual ao padrão já existente no SGCD/SGDP. Antes o Ctrl+K só focava o campo de busca local da tela visível

## [0.12.2] — 2026-07-09

### Alterado
- **Usuário admin padrão** — removido o cargo pré-preenchido ("Agente de Contratação") na criação do usuário admin de instalações novas; agora fica em branco por padrão, igual ao SGDP/SGCD. Instalações já existentes não são alteradas

## [0.12.1] — 2026-07-09

### Alterado
- **Modal de "Editar/Novo Usuário" reescrito** — substitui o overlay construído dinamicamente via JS por um modal estático (`.overlay`/`.modal-header`/`.info-field`/`.modal-footer`), o mesmo padrão já usado nos modais de Fornecedor, Contrato e Assinatura. Sem mudança de campos ou comportamento — só a estrutura interna, para consistência visual com o resto do sistema

## [0.12.0] — 2026-07-09

### Adicionado
- **CPF e E-mail no cadastro de usuário** — novos campos no modal Editar/Novo Usuário, posicionados junto do Nome (separados de Cargo/Matrícula), para uso futuro (ex. notificações, assinatura). Sincronizado com SGDP (já tinha E-mail) e SGCD

## [0.11.0] — 2026-07-08

### Adicionado
- **Assinatura digital ICP-Brasil** — botão "🔏 Assinar" em cada anexo PDF de Contrato/Ata; assina com certificado .pfx A1, gera código de verificação público e página `/verificar/<código>` (sem login). Registro imutável em `signatures`, sobrevive mesmo se o anexo for depois substituído. Escopo alinhado ao SGDP (só ICP-Brasil, sem os métodos simples/gov.br do SGCD)
- **Tabela `arquivos` própria para anexos** — pré-requisito da assinatura: anexos de Contrato/Ata deixam de ser base64 embutido no JSON do registro (reescrevia o blob inteiro a cada edição de qualquer campo) e passam a ser armazenados como arquivo em disco + linha em tabela, no mesmo padrão do `files`/`arquivos` do SGCD/SGDP. Migração automática e idempotente do formato antigo, roda no início do servidor
- `SGCA/requirements.txt` — documenta `pyhanko` (dependência opcional, só necessária para assinar; o servidor sobe normalmente sem ela)

## [0.10.0] — 2026-07-08

### Adicionado
- **Busca full-text (FTS5)** — busca no campo Objeto de Contratos agora usa índice SQLite FTS5 (com fallback automático para `LIKE` caso o build do SQLite não tenha FTS5 compilado), em vez de só `LIKE`; sincronizado do padrão já usado no SGDP. Atas não ganharam FTS5 — seu único campo de texto livre é gerado automaticamente, não há conteúdo de usuário para indexar
- **Etiquetas (tags) em Contratos e Atas** — tags livres com autocomplete, filtro dedicado na listagem e marcadores nos cards do Kanban; sincronizado do modelo relacional já usado no SGDP (`tags` + `contrato_tags`/`ata_tags`)

### Corrigido
- **Contraste no tema escuro** — `#notif-panel` usava um seletor `[data-theme="dark"]` que nunca era ativado (a troca de tema usa a classe `body.dark`, não o atributo `data-theme`); `.table-wrap` não tinha nenhuma cobertura no tema escuro. Mesmo bug clonado no SGDP e já corrigido lá; achado ao comparar os 3 sistemas

## [0.9.4] — 2026-07-07

### Corrigido
- **Manual Operacional** — bloco "Sobre esta versão" na capa usava o estilo de destaque amarelo (`.nota`), inconsistente com o SGCD/SGDP, que não têm caixas coloridas na capa; convertido para o mesmo estilo itálico discreto (`.cover-legal`) usado nos blocos legais dos outros dois sistemas

## [0.9.3] — 2026-07-07

### Adicionado
- **Rate limit de login** — bloqueia com HTTP 429 após 5 tentativas falhas em 5 minutos (janela deslizante, por usuário); login correto limpa o contador. Gap encontrado na auditoria de servidor: nenhum dos 3 sistemas tinha proteção contra força bruta

### Removido
- **`MAX_UPLOAD`/`ALLOWED_EXTS`** — constantes declaradas mas nunca usadas, resíduo do clone do SGCD (SGCA não tem feature de anexo de arquivo/assinatura que precisasse desses limites)

## [0.9.2] — 2026-07-07

### Corrigido
- **Brasão do município podia ser perdido silenciosamente** — o perfil de navegador dedicado do Modo Pessoal (que guarda o brasão e demais preferências salvas só no navegador, quando a sincronização com o servidor falha) era criado em `%TEMP%\SGCA-Profile`, uma pasta que o Windows e ferramentas de limpeza de disco podem apagar a qualquer momento. Agora o perfil fica em `browser-profile/`, ao lado de `sgca.db` e `backups/`, junto com os demais dados persistentes da aplicação

---

## [0.9.1] — 2026-07-07

### Adicionado
- **Vigência automática no Contrato** — ao informar a Vigência Inicial, a Vigência Final é sugerida automaticamente como +12 meses (editável), no mesmo mecanismo já usado na Ata de Registro de Preços (Data de Assinatura → Vigência Final)

### Corrigido
- **Documentos gerados ainda mencionavam "Sistema de Gestão de Contratação Direta" (SGCD)** — o rodapé compartilhado por praticamente todo documento impresso (`_qrFooterReport()`: Extrato de Contrato, Termos Aditivos, todos os Relatórios) e o Relatório de Trilha de Auditoria diziam o nome do sistema de origem do clone em vez de "Sistema de Gestão de Contratos e Atas"
- **Exportação PNCP de Contrato nunca identificava o vínculo com Ata de Registro de Preços** — o código verificava um campo `ataId`, que nunca existiu; o campo real é `ataOrigemId` (introduzido na v0.7.0). Na prática, `categoriaProcesso` e `tipoContratoId` sempre assumiam o valor de contratação direta, mesmo para contratos vinculados a uma ata. Corrigido usando o nome de campo certo, e o rótulo genérico "Contratação Direta" foi trocado por "Contrato Administrativo" para não presumir uma modalidade específica de licitação

---

## [0.9.0] — 2026-07-07

### Adicionado
- **Numeração automática sugerida** — ao criar um novo Contrato ou Ata, o número já vem preenchido com o próximo sequencial do ano corrente, editável
- **Validação de número duplicado** — não é mais possível salvar um Contrato ou Ata com um número já usado no mesmo cadastro
- **Múltiplos anexos por Contrato/Ata** — o que antes era um único PDF agora é uma lista de anexos, cada um com seu próprio link de download e remoção (registros já existentes com o anexo antigo continuam acessíveis)
- **Filtro por Fiscal** na tela de Contratos, no mesmo padrão do filtro por fornecedor
- **Alerta de "Contratos sem Fiscal"** no Dashboard geral — designação de fiscal é exigência do Art. 117, Lei 14.133/2021
- **Histórico do registro** — botão "🕘 Histórico" no Contrato e na Ata mostra a trilha de auditoria (criação, edições, aditivos, anexos, exportações) filtrada só para aquele registro, reaproveitando a auditoria global já existente (novo filtro `processId` em `GET /api/audit`)

---

## [0.8.0] — 2026-07-07

### Adicionado
- **Dashboard geral** — nova tela inicial (antes do login recair direto em Contratos), com indicadores consolidados de Contratos e Atas, gráfico de vencimentos dos próximos 6 meses e lista de próximos vencimentos (contratos, atas, garantias e sanções), com atalho na barra lateral antes da seção "Contratações"
- **Gráfico de vencimentos também na tela de Atas** — a tela de Contratos já tinha o gráfico dos próximos 6 meses; a de Atas não tinha o mesmo recurso
- **Bloqueio de exclusão de fornecedor vinculado** — o botão "Excluir Fornecedor" agora verifica se há contratos ou itens de ata referenciando aquele fornecedor e impede a exclusão (com aviso do total vinculado) até que os vínculos sejam resolvidos

---

## [0.7.1] — 2026-07-07

### Corrigido
- **Rotação de backups não era acionada após criar um backup** — `_do_db_backup()` é chamado em vários pontos (encerrar o sistema, backup manual, antes de restaurar), mas `_rotate_backups()` só rodava uma vez, no início do servidor. Na prática, a pasta de backups crescia sem limite entre reinícios, ignorando o número configurado em "Backups mantidos". Corrigido chamando `_rotate_backups()` ao final de `_do_db_backup()`, cobrindo automaticamente todos os pontos que criam backup

---

## [0.7.0] — 2026-07-07

### Adicionado
- **Anexo de PDF na Ata** (ata assinada digitalizada) — mesmo padrão de upload/download já usado no Contrato
- **Fiscal Substituto** no Contrato (nome + e-mail) — Art. 117, §2º da Lei 14.133/2021; recebe o mesmo aviso automático de vencimento que o fiscal titular
- **Atalho "Ver Contratos"** no card do fornecedor — abre a tela de Contratos já filtrada pelos contratos daquele fornecedor, com selo removível indicando o filtro ativo (novo parâmetro `fornecedor` no `GET /api/contratos`)
- **Prorrogação assistida** — ao abrir "+ Novo Aditivo" (tipo Prazo), o campo de nova vigência já vem preenchido com a vigência atual + 12 meses, editável
- **Relatório global de Sanções** — botão na tela de Fornecedores gera um relatório consolidado com as sanções de todos os fornecedores, além do relatório já existente por fornecedor individual
- **Gráfico de vencimentos dos próximos 6 meses** na tela de Contratos, combinando contratos e atas por mês (SVG simples, sem biblioteca de gráficos)

---

## [0.6.2] — 2026-07-07

### Adicionado
- **Indicadores na tela de Atas** — atas vigentes, vencendo em 30 dias, valor total registrado e itens com saldo baixo, no mesmo padrão visual dos indicadores de Contratos

### Corrigido
- **Indicador "Atas com saldo baixo" (tela de Contratos) sempre mostrava 0** — o cálculo usava os nomes de campo `qtdRegistrada`/`qtdUtilizada`, mas os itens de ata são salvos como `quantidadeRegistrada`/`quantidadeUtilizada`; o indicador nunca correspondia a dados reais desde que foi introduzido na v0.6.0

---

## [0.6.1] — 2026-07-07

### Corrigido
- **Brasão customizado não se mantinha entre reinícios do sistema** — o `GET /api/settings` geral (consultado a cada login) incluía o `brasao_dataurl`, um base64 de alguns MB, deixando essa rota lenta o bastante para ocasionalmente sofrer 401 durante a rajada de requisições do login, sob a sessão curta (`SESSION_TTL`= 15s). Como `_onLoginSuccess()` tratava essa falha em silêncio, o brasão simplesmente não voltava para o navegador — obrigando o usuário a reenviar e salvar o arquivo a cada início. Corrigido excluindo `brasao_dataurl` do `GET /api/settings` geral (já existia um endpoint dedicado, `/api/settings/brasao`, criado para isso mas nunca consultado pelo frontend) e buscando o brasão nessa rota separada, dissociado do restante da sincronização

---

## [0.6.0] — 2026-07-07

### Adicionado
- **Aviso de sanção vigente ao vincular fornecedor** — ao selecionar um fornecedor em um Contrato ou item de Ata, um aviso aparece se ele tiver suspensão, impedimento de licitar ou declaração de inidoneidade vigente (Art. 156, Lei 14.133/2021)
- **Relatório consolidado de Contratos e de Atas** — botão "Relatório" nas telas de listagem, no mesmo padrão A4 já usado no relatório de Fornecedores
- **Indicadores na tela de Contratos** — contratos vigentes, vencendo em 30 dias, valor total vigente e atas com saldo baixo, reaproveitando o componente `.stat` (já existente no CSS mas até então sem uso)
- **Fim de sanção na Agenda de Vencimentos** — sanções com prazo final cadastrado (suspensão, impedimento, inidoneidade) agora geram um evento na Agenda, levando direto à aba Sanções do fornecedor
- **Vínculo Contrato ↔ Ata de Registro de Preços** — campo "Ata de Origem" no Contrato, para casos de contratação por adesão; aparece também no Extrato de Contrato quando preenchido
- **Relatório de Sanções por fornecedor** — botão "📄 Relatório" na aba Sanções, gera um documento formal com o histórico de sanções aplicadas

### Corrigido
- **Nome do sistema errado nos relatórios impressos** — o relatório de Fornecedores ainda dizia "Sistema de Gestão de Contratação Direta" (herança do clone do SGCD); corrigido para "Sistema de Gestão de Contratos e Atas"

---

## [0.5.0] — 2026-07-07

### Adicionado
- **Exportação de Contratos e Atas em CSV** — botão "Exportar CSV" nas telas de listagem, com dados legíveis (fornecedor, status por extenso, valores em formato pt-BR)
- **Aviso automático ao fiscal do contrato** — novo campo "E-mail do Fiscal"; o resumo diário de vencimentos passa a enviar também um aviso individual a cada fiscal com contrato(s) vencendo, mesmo sem e-mail interno configurado
- **Garantia Contratual** — modalidade (caução/seguro-garantia/fiança bancária), valor, vencimento e data de devolução, com entrada própria na Agenda de Vencimentos
- **Sanções e Penalidades** — nova aba no cadastro de fornecedores para registrar advertências, multas, suspensões, impedimentos de licitar e declarações de inidoneidade, com fundamentação e prazo
- **Reajuste por índice** em aditivos de reequilíbrio/repactuação — índice (IPCA-E, IGP-M, INCC-M, INPC ou outro) e percentual de variação, com cálculo automático do valor de reajuste e prévia antes de salvar
- **Anexo do contrato assinado (PDF)** — upload/download vinculado ao registro do contrato

### Corrigido
- **`fmtMoney()` inflava por 10x valores monetários com centavos** — a função reaproveitava `parseValor()` (feito para strings já formatadas em pt-BR) mesmo quando recebia um número puro do banco; `String(15000.5)` vira `"15000.5"`, e a lógica de striping de separador de milhar tratava o ponto decimal como separador de milhar, multiplicando o valor por 10 ao reexibir. Afetava toda exibição de Valor Global, variação de aditivos e preço unitário de item de ata sempre que o valor tinha centavos — e, mais grave, corrompia o valor permanentemente se o contrato fosse salvo novamente nesse estado (o campo já formatado incorretamente era reinterpretado por `parseValor` no submit)
- **`toggleFornCard` não reconhecia a aba "sancoes"** — introduzido durante o desenvolvimento desta versão e corrigido antes do release

---

## [0.5.1] — 2026-07-07

### Corrigido
- **`openContratoModal`/`openAtaModal` exibiam dados desatualizados quando o registro já estava em cache local** (`_contratos`/`_atas`) — o fallback para buscar da API só era acionado quando o item não existia no cache; se existia porém estava desatualizado (ex.: alterado em outra aba, ou reaberto pela Agenda logo após uma edição feita por outro caminho), o modal mostrava os valores antigos. Agora sempre busca da API ao abrir o modal, e mantém o cache local sincronizado com o resultado
- **Remover o anexo do contrato assinado não funcionava** — `delete contrato.anexoContrato` seguido de `PUT` não removia o campo no servidor, pois `_update_contrato` faz um merge raso (`dict.update()`) que só sobrescreve chaves presentes no payload, nunca remove as ausentes. Corrigido enviando `anexoContrato: null` explicitamente em vez de apagar a chave

---

## [0.1.0] — 2026-07-05

### Adicionado
- Esqueleto inicial do SGCA, criado a partir do SGCD (Sistema de Gestão de Contratação Direta): autenticação multiusuário, gestão de usuários, cadastro de fornecedores (CNPJ, certidões, alertas de vencimento, importação CSV), configurações (organização, brasão, SMTP, tema), trilha de auditoria, notificações in-app e por e-mail, backup automático/manual com sincronização entre máquinas, lixeira e diagnóstico de rede
- Servidor próprio na porta 3002 (SGCD usa 3000, SGDP usa 3001)
- Ícone próprio do sistema (`sgca.ico`)

### Removido
- Geradores de documentos específicos de Dispensa de Licitação (Autorização de Abertura, Aviso de Dispensa, Termos de Adjudicação/Homologação, Despachos, Mapa de Preços, Extrato de Contrato, Enquadramento Legal, exportação PNCP, análise de fracionamento)

### Oculto (código ainda presente, será substituído na Fase 2)
- Dashboard/Kanban de processos e Agenda de Vencimentos — específicos do fluxo de Dispensa de Licitação (checklist de 18 etapas). Removidos da navegação; Fornecedores passa a ser a tela inicial pós-login. Serão reescritos para o domínio de Contratos e Atas de Registro de Preços.

---

## [0.2.0] — 2026-07-05

### Adicionado
- Módulo de **Contratos**: cadastro, Kanban por status (Vigente/Em prorrogação/Encerrado/Rescindido), vínculo com Fornecedores, aditivos/apostilamentos com alerta de limite legal de 25% (Art. 125, Lei 14.133/2021)
- Módulo de **Atas de Registro de Preços**: cadastro, itens registrados com controle de saldo (quantidade utilizada vs. registrada) e alerta visual de esgotamento
- Backend: tabelas `contratos`/`atas` e endpoints REST completos (CRUD, lixeira, aditivos, itens)

### Removido — domínio de Dispensa de Licitação totalmente descontinuado
- Todo o fluxo de checklist de 18 etapas, geração de documentos, fracionamento, dotação orçamentária, propostas/cotações, conformidade, PNCP e vinculação entre processos (~4.500 linhas de código morto)
- Assinatura eletrônica de documentos (Simples/gov.br/ICP-Brasil) e verificação de autenticidade por QR Code — dependiam do sistema de documentos removido
- Upload de arquivos/anexos e endpoint de download — sem uso após a remoção do módulo de processos
- Busca global (Ctrl+K), templates de processo, "mais ações" do card de processo — telas sem funcionalidade após a remoção do domínio
- Dependência opcional `pyhanko` (só usada pela assinatura ICP-Brasil)

### Corrigido
- **Lixeira** agora lista itens excluídos de Fornecedores, Contratos e Atas (antes só enxergava processos, já removidos)
- Painel de Diagnóstico (Configurações) simplificado para checar só fornecedores/dados institucionais, sem mais depender de processos inexistentes
- Backup (exportar/importar/sincronizar) atualizado para o novo formato de dados (`contratos`/`atas` em vez de `processes`/`files`)
- Diversas referências órfãs deixadas por uma remoção anterior malfeita (funções chamadas mas não mais definidas: `_debounce`, `_closeNotifOutside`, `_pinCheckCaps`, atalhos de teclado para telas removidas)

---

## [0.2.1] — 2026-07-06

### Adicionado
- **Atalho Ctrl+K** — foca o campo de busca da seção visível (Contratos ou Atas), no padrão da família SGCD/SGDP

### Corrigido
- **Badge de versão** — o fallback do badge na sidebar mostrava "1.17.0" (resquício do SGCD); corrigido para acompanhar a versão real

---

## [0.3.0] — 2026-07-06

### Alterado — padronização arquitetural com o SGDP (mudança grande)
- **Design tokens CSS** — `--aubergine`/`--aubergine-mid` renomeados para `--accent`/`--accent-light`; completada a escala de cinza (`--gray-600`/`--gray-800`, usados em 11 lugares mas nunca definidos) e adicionadas `--green`/`--red`/`--yellow`/`--shadow-lg`
- **Sidebar** — `<nav id="sidebar">` virou `<aside id="sidebar">` com `<nav class="sidebar-nav">` interno (landmark semântico correto); CSS morto de `.sidebar-search` removido
- **Mensagens de erro** — "Acesso negado" padronizado para "Acesso restrito" nos 403 de admin
- **Tabela e rota de usuários** — `users` → `usuarios`, `/api/users` → `/api/usuarios`; colunas `cargo`/`matricula` preservadas; migração automática e silenciosa na inicialização, sem perda de dado
- **Camada de acesso a dados** — removida a indireção `dbGetAll/dbGet/dbPut` (resquício de um design com IndexedDB que o SGCA nunca usou de fato); chamadas `API.get/put/post` diretas, como o SGDP já fazia
- **Busca de Contratos/Atas** — passou a ser feita no servidor (`?q=`) em vez de buscar tudo e filtrar no navegador; Fornecedores manteve busca no cliente (cobre `nome_fantasia`, que só existe dentro do JSON, não indexado)

### Corrigido
- **Código morto do clone do SGCD** — `loadProcesses()`, a variável `processes` e `updateAgendaBadge()` nunca funcionaram no SGCA (chamavam `/api/processes`, inexistente; referenciavam elementos e campos de dados do domínio de dispensa). Diálogos de wipe/exportar backup, que mostravam "0 processos" sempre, agora mostram contagem real de contratos/atas
- **`API_BASE` com porta fixa** — o frontend tinha `http://localhost:3002` fixo no código; quebrava se o servidor rodasse em outra porta. Trocado por caminhos relativos, como o SGDP sempre fez
- **Busca de contratos quebrava o servidor** — `_list_contratos` fazia `numero LIKE ?` em SQL, mas `numero` não é coluna da tabela `contratos` (só existe dentro do JSON); toda vez que `q` fosse enviado o servidor caía com `sqlite3.OperationalError`. Bug dormente até esta versão, porque o frontend nunca mandava `q` para esse endpoint antes. Corrigido com `json_extract(data, '$.numero')`
- **Fonte ajustável** — resolvido no SGDP nesta mesma rodada de padronização (era o único dos três que usava `zoom` no CSS em vez de `font-size`); SGCA já seguia o padrão correto, sem mudança necessária aqui

Todas as mudanças foram testadas em ambiente isolado (cópia do projeto, banco de teste, porta separada) antes de aplicar — o banco de produção não foi tocado em nenhuma etapa. 17/17 testes automatizados passando.

---

## [0.3.1] — 2026-07-06

### Alterado
- **Trilha de Auditoria** — timeline agrupada por dia (buscava até 2000 registros de uma vez, filtro 100% no cliente) substituída por tabela com filtros server-side (busca, tipo, período) e paginação via servidor, igual ao SGDP
  - Menu "Auditoria" agora só aparece para administradores
  - `/api/audit` ganhou filtros (q/tipo/de/ate), mas continua sem restrição de admin — usado também pelo histórico de alterações por campo, aberto a qualquer usuário logado

---

## [0.3.2] — 2026-07-06

### Corrigido
- **Vocabulário de eventos de auditoria era o do SGCD, não o de contratos/atas** — mapa de rótulos (`_AUDIT_EVENT_LABELS`) tinha só eventos herdados do clone (ETAPA_*, PROCESSO_*, CERTIDAO_* etc.), nenhum deles emitido de fato pelo SGCA; eventos reais (`CONTRATO_CRIADO`, `CONTRATO_EDITADO`, `CONTRATO_ADITIVO`, `ATA_CRIADA`, `ATA_EDITADA`, `FORNECEDOR_EXCLUIDO`, `SYNC_BACKUP`) apareciam crus na tabela. Corrigido trocando pelo vocabulário correto

### Alterado
- Dropdown "Tipo" trocado de lista fixa no HTML para geração dinâmica a partir do mapa de rótulos, evitando desincronia futura
- Coluna "Tipo" renomeada para "Ação", alinhando com o SGDP

---

## [0.3.3] — 2026-07-06

### Corrigido
- **Tipo de evento malformado ao restaurar/excluir da lixeira** — `restoreLixeiraItem()`/`purgeLixeiraItem()` geravam o tipo do evento a partir do rótulo de exibição (`cfg.label.toUpperCase()`); para "Ata de RP" isso produzia `"ATA DE RP_RESTAURADO"`, com espaço embutido no tipo. Corrigido com um campo `codigo` estável em `_LIXEIRA_TIPOS`, independente do texto de exibição
- Completados os 6 rótulos que faltavam: `CONTRATO_RESTAURADO`/`CONTRATO_EXPURGADO`, `ATA_RESTAURADO`/`ATA_EXPURGADO`, `FORNECEDOR_RESTAURADO`/`FORNECEDOR_EXPURGADO`

Verificação sistemática (script comparando eventos emitidos no código vs mapa de rótulos) confirmou que SGDP e SGCD já estavam 100% cobertos após as correções da v0.3.2 — só o SGCA tinha esse gap adicional.

---

## [0.4.0] — 2026-07-06

### Adicionado
- **Agenda de Vencimentos** unificada — lista contratos e atas com vigência vencendo, agrupados por urgência; botão "Enviar por e-mail" (resumo manual) e alerta automático diário por e-mail (`_send_daily_alerts()`, dedupe via `alert_email_last_sent`), com badge de contagem no menu
- **Documentos gerados**: "Gerar Extrato" (Contrato) e "Gerar Termo" por aditivo/apostilamento (prazo, valor, qualitativo, reequilíbrio, repactuação), no mesmo padrão visual A4 (`_DOC_CSS`) e rodapé de autenticação (QR) do SGCD
- **Exportação PNCP** — botão "Exportar PNCP" em Contratos e Atas, gerando JSON no formato esperado pelo portal, com lista de `_pendencias` para campos obrigatórios ainda não preenchidos

### Corrigido
- `_getBrasaoB64()` estava quebrado (tentava extrair base64 de uma função já removida na Fase 2); reescrito para buscar `brasao.png` de forma assíncrona com cache em memória
- Campo de fornecedor errado (`razaoSocial`/`razao`) usado em 3 pontos do código de Contrato/Ata; corrigido para os nomes reais (`razao_social`/`nome_fantasia`)
- `openContratoModal`/`openAtaModal` só encontravam o registro se a tela de lista já tivesse sido visitada antes (cache local); agora buscam da API quando necessário — corrige navegação direta da Agenda de Vencimentos para o modal

---
