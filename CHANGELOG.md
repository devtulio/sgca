# Changelog — SGCA
## Sistema de Gestão de Contratos e Atas
> Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
> Versionamento semântico: [SemVer](https://semver.org/lang/pt-BR/)

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

## Próximos passos

- Documentos gerados do domínio de Contratos/Atas (extrato, termo aditivo)
- Agenda de Vencimentos unificada (contratos + atas vencendo)
- Exportação PNCP de contratos/atas
