# Changelog — SGCA
## Sistema de Gestão de Contratos e Atas
> Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
> Versionamento semântico: [SemVer](https://semver.org/lang/pt-BR/)

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
