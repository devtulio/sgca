# Changelog — SGCA
## Sistema de Gestão de Contratos e Atas
> Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
> Versionamento semântico: [SemVer](https://semver.org/lang/pt-BR/)

---

## [Não versionado]

### Alterado
- **Data por extenso passa a vir do esqueleto compartilhado.** O fecho "local, data" dos documentos usava uma expressão repetida em cada gerador — 18 cópias somadas nos quatro sistemas. Agora todas chamam `fmtExtenso()`, no `base.js`, que já trata a armadilha de fuso (string só-data lida sem âncora volta um dia). Nada muda no que sai impresso; o que muda é haver um só lugar para corrigir.

### Documentação
- **Capturas de tela no README.** As imagens são geradas por `docs/screenshots.spec.js` contra um banco temporário, com dados fictícios e sem brasão — a captura nunca enxerga o banco real. Para atualizá-las depois de mudar a interface: `npx playwright test -c docs/screenshots.config.js`.

---

## [0.41.0] — 2026-08-01

### Adicionado
- **CNPJ da subcontratação resolve sozinho.** Ao informar o CNPJ de um subcontratado, o sistema procura o fornecedor **no cadastro** — o mesmo compartilhado com SGCD e SGEA — e preenche a razão social na hora. Se não estiver lá, consulta a Receita Federal, cadastra e preenche. Evita digitar a razão social à mão e evita o mesmo fornecedor virar dois registros com grafias diferentes.
  - **CNPJ inválido não cadastra nada** e o número digitado é preservado. A razão social só é preenchida se estiver vazia: quem já digitou não perde o que escreveu.

### Corrigido
- **Cálculo de "hoje" errava um dia depois das 21h.** O sistema calculava "hoje" convertendo o horário para o fuso de Greenwich. Depois das 21h, "hoje" já era o dia seguinte lá — e tudo que dependia disso errava um dia, mas só à noite. No SGCA isso afetava os campos de data que já nascem preenchidos (fiscalização, pagamento, reajuste), a contagem de certidões vencidas e de sanções vigentes no relatório por fornecedor, e a data no nome dos arquivos exportados.

---

## [0.40.12] — 2026-07-31

### Alterado
- **Página do projeto no GitHub revisada.** O selo de versão passa a ser lido da última release publicada, então deixa de precisar de atualização manual a cada lançamento. Novos selos de domínio e plataforma; nova seção **Como citar**, com o DOI do Zenodo; e novo bloco **Sistemas irmãos**, com links para os outros sistemas da família — antes eles eram citados apenas pelo nome.

### Corrigido
- **O selo de DOI não aparecia** na página do GitHub. O proxy de imagens do GitHub não consegue buscar do Zenodo, e a imagem chegava vazia, sem erro visível — estava assim desde que o selo foi criado. Passa a ser servido pelo mesmo provedor dos demais selos, com o link continuando a levar ao DOI.
- Comentário de versão no topo do `server.py`, parado na v0.37.0.

---

## [0.40.11] — 2026-07-31

### Corrigido
- **Ata assinada em 1º de janeiro era registrada com o ano anterior.** O ano da ata — usado na numeração e na exportação para o PNCP — vinha de uma leitura de data que o navegador interpreta como UTC; no nosso fuso, 1º de janeiro virava 31 de dezembro do ano anterior. Só se manifestava na virada do ano, e agora está corrigido.

---

## [0.40.10] — 2026-07-29

### Alterado
- **A tela "Erros recentes" passa a mostrar só os últimos 7 dias.** Antes ela listava tudo o que estivesse no log, então um defeito já corrigido continuava aparecendo indefinidamente — o arquivo só é rotacionado ao chegar a 2 MB, o que na prática não acontece. O que é mais antigo não some sem aviso: aparece como *"mais N registros anteriores a 7 dias, guardados no arquivo de log"*. **Nada é apagado** — o log continua íntegro no disco.

---

## [0.40.9] — 2026-07-29

### Corrigido
- **A janela do sistema voltava a acumular gigabytes, apesar da correção anterior.** Desligar o modelo de inteligência artificial do navegador impedia que ele fosse *instalado*, mas não que fosse **baixado**: o pacote de 4 GB ia parar em outra pasta de cache do próprio perfil. Medido aqui: o perfil de um dos sistemas estava de volta aos 4,2 GB no mesmo dia. Agora a janela também sobe com a atualização de componentes desligada — ela só abre o sistema local, então não há perda. **Medido depois da correção: 86 MB após três minutos de janela aberta, contra 4,2 GB antes.**

---

## [0.40.8] — 2026-07-29

### Removido
- **QR Code do rodapé dos documentos.** Ele codificava exatamente o mesmo texto que já vinha impresso ao lado — sistema, versão, órgão e código de autenticidade — e não levava a lugar nenhum: o sistema é local, não há página pública para o QR apontar. Era decoração, e custava um gerador de quase 200 linhas dentro do arquivo. **O rodapé continua igual em conteúdo**, com data, versão e o código de autenticidade; só a imagem saiu. Documentos já impressos não são afetados.

---

## [0.40.7] — 2026-07-29

### Removido
- **Código morto herdado do clone do SGCD** (198 linhas): o motor de classificação de objeto e de fracionamento, a tabela de ícones, o mapa de migração de certidões e treze variáveis de estado de telas que o SGCA não tem (etapas de processo, kanban, seleção de proposta). Nada muda no uso.

---

## [0.40.6] — 2026-07-28

### Removido
- **Código morto herdado do SGCD** (função de situação por etapas, que não existe no SGCA): não era chamada em lugar nenhum. Nada muda no uso.

---

## [0.40.5] — 2026-07-28

### Corrigido
- **Aviso técnico no console do servidor.** Ao reportar um erro de JavaScript, o servidor respondia "sem conteúdo" mas ainda enviava um corpo junto, e o motor do servidor registrava o aviso `application-written content was ignored`. Sem efeito para quem usa; o log fica limpo.

---

## [0.40.4] — 2026-07-28

### Adicionado
- **SINTEGRA — Inscrição Estadual** passa a ser um tipo de certidão do fornecedor, junto dos demais cadastros oficiais (mesma lista do SGCD).

### Corrigido
- **Endereços de dois órgãos atualizados na lista de tipos de certidão** (TCU — Inabilitados e Inidôneos, e Certidão Simples Nacional): as páginas antigas saíram do ar. No SGCA a lista é usada só para nomear o tipo da certidão do fornecedor, então nada muda na tela — o acerto mantém a lista igual à do SGCD.
- **A janela do sistema acumulava vários GB no computador.** O sistema abre o app numa janela dedicada do navegador, com perfil próprio, e o Chrome baixava para dentro desse perfil o modelo de inteligência artificial local dele — cerca de **4 GB** que nada aqui usa. A abertura passa a desligar esse recurso: o perfil fica em algumas dezenas de MB.
- **O perfil do navegador saiu de dentro da pasta do sistema** e passou para a pasta temporária do Windows, como já era nos sistemas irmãos — antes ele inchava a pasta e ia junto em qualquer cópia dela. Na primeira execução da nova versão o sistema **avisa no console** que a pasta `browser-profile` antiga pode ser apagada; ela não é removida automaticamente. A janela do app pede login de novo e as preferências de aparência (tema, largura, fonte) voltam ao padrão nessa máquina — nada disso fica no banco de dados.

---

## [0.40.3] — 2026-07-28

### Adicionado
- **`Perguntar Onde Salvar Downloads.reg`** passa a acompanhar o sistema. Executado como administrador num posto da rede, faz o Chrome e o Edge perguntarem onde salvar cada arquivo baixado — o que o navegador não permite que a própria página faça fora de `localhost`/HTTPS. Uma vez por computador; desnecessário na máquina do servidor. Instruções no próprio arquivo e na seção de uso em rede local do manual.

---

## [0.40.2] — 2026-07-28

### Documentação
- **Manual: como fazer os postos da rede perguntarem onde salvar os downloads.** A janela "Salvar como" só é oferecida à página em origem segura (`localhost` ou HTTPS); nos computadores que acessam pelo endereço de rede o arquivo vai direto para a pasta de Downloads. A seção de uso em rede local passa a trazer a opção do navegador e a política equivalente (`PromptForDownloadLocation`), com o arquivo `.reg` pronto — uma vez por computador, ou uma GPO única onde houver domínio.

---

## [0.40.1] — 2026-07-28

### Corrigido
- **Baixar um anexo de contrato ou ata mandava o arquivo direto para a pasta de downloads** (mesma correção feita no SGCD). O download passa a abrir a janela **"Salvar como"** do navegador, e o link do anexo deixa de carregar o token da sessão no endereço. Onde essa janela não está disponível — navegador antigo, ou acesso pelo **endereço de rede** (`http://192.168.x.x:3000`), que o navegador não trata como origem segura —, o comportamento continua o de antes; nessas máquinas, a opção *"Perguntar onde salvar cada arquivo"* do próprio navegador é o que resolve.

---

## [0.40.0] — 2026-07-28

### Adicionado
- **Tela de Relatórios** (menu Administração) com nove documentos gerenciais em A4, prontos para imprimir ou salvar em PDF, com brasão e identificação do órgão. Todos consideram **todos** os registros, não apenas o que está filtrado na tela:
  - **Execução Financeira dos Contratos** — valor atual (com aditivos), pago, saldo e % executado, com totais da carteira
  - **Saldo das Atas de Registro de Preços** — por ata e por item: registrado, utilizado, saldo e % consumido, destacando o que passou de 80% e o que esgotou
  - **Controle de Aditivos (Art. 125)** — aditivos de cada contrato e o percentual acumulado contra o limite legal de 25%
  - **Fiscalização dos Contratos** — última fiscalização, dias decorridos, e contratos sem fiscal designado ou nunca fiscalizados
  - **Vencimentos e Prazos** — contratos, atas e garantias vencendo em 30/60/90 dias
  - **Garantias Contratuais** — modalidade, valor, vencimento e devolução, separando as vencidas e não devolvidas
  - **Recebimento do Objeto** — recebimentos provisório e definitivo, com destaque para contratos encerrados sem o definitivo
  - **Contratos por Fornecedor** — carteira por fornecedor, com certidões vencidas e sanção vigente
  - **Riscos Consolidados** — riscos de todos os contratos por grau (probabilidade × impacto)

### Corrigido
- **Documentos e relatórios saíam com margem dobrada na impressão.** O recuo usado para a janela de prévia somava com a margem de página do próprio documento, resultando em cerca de 4 cm de branco em cima e embaixo. Pior em documento de várias páginas: esse recuo só valia na primeira e na última folha, e o miolo saía colado na borda. A margem impressa passa a ser **só a de página (20 mm)**, em todos os documentos e relatórios; a prévia na tela continua com o recuo confortável de sempre.

---

## [0.39.6] — 2026-07-27

### Adicionado
- **O campo Código Fiorilli/SCPI (CADPRO) do item da ata passou a ter máscara**, no formato **NNN.NNN.NNN** (9 dígitos): digite só os números e os pontos entram sozinhos; colar um código pontuado ou com texto em volta também funciona. O campo continua opcional, mas se for preenchido tem de estar completo — é a chave usada pelo *Alimentar do Fiorilli*, e um código pela metade não casaria com nada.

---

## [0.39.5] — 2026-07-27

### Alterado
- **O item da ata deixa de pedir o "Código SCPI".** SCPI é o próprio sistema contábil da Fiorilli, ou seja, o código SCPI e o código Fiorilli/CADPRO são a mesma informação — o formulário pedia duas vezes o mesmo dado. Fica apenas um campo, agora rotulado **"Código Fiorilli/SCPI (CADPRO)"**, que é a chave usada pelo *Alimentar do Fiorilli*.
- **O campo "Unidade SCPI" também foi removido**, pelo mesmo motivo e por nunca ter sido usado por nenhuma rotina do sistema. Fica a **Unidade de contratação**.

Nenhum dado foi perdido: os dois campos eram gravados, mas nunca lidos por relatório, exportação ou pelo casamento com o Fiorilli.

---

## [0.39.4] — 2026-07-27

### Alterado
- **A importação de fornecedores por CSV passou a ser restrita ao administrador** e a gravar tudo de uma vez, em vez de um fornecedor por vez a partir do navegador. Quem não é administrador deixa de ver o botão. Cadastrar fornecedor pela tela continua liberado para todos. O **Alimentar do Fiorilli** não muda: continua disponível a todos, por ser edição de uma ata já aberta.

### Corrigido
- **Reimportar o mesmo arquivo duplicava o cadastro inteiro.** Cada linha do CSV virava um fornecedor novo, mesmo com CNPJ repetido. Agora casa por **CNPJ**: atualiza o existente (preservando certidões e sanções) e insere só o que falta.
- Se a importação falhar no meio, nada é gravado.

---

## [0.39.3] — 2026-07-27

### Corrigido
- **Excluir uma ata deixava contratos vivos apontando para ela.** Contratos guardam a ata de origem, que aparece no extrato e define o tipo enviado ao PNCP — mas nada impedia excluir a ata mesmo assim, e o único sintoma era o extrato deixar de citá-la. Agora a exclusão é recusada enquanto houver contratos ligados, dizendo quantos são.
- **Anexos ficavam órfãos no disco.** Ao excluir um contrato ou ata **de vez** (Lixeira → Excluir de vez), os PDFs continuavam ocupando espaço em `uploads/` para sempre, sem dono. A purga passa a apagá-los junto. Enquanto o registro está na Lixeira os arquivos continuam guardados, para a restauração seguir funcionando.
- **O número de um contrato ou ata na Lixeira era liberado para reuso.** A conferência de duplicidade só olhava os registros ativos: dava para criar outro contrato com o mesmo número e, ao restaurar o primeiro, ficavam dois iguais sem erro nenhum. A checagem passou para o servidor e considera também a Lixeira, avisando onde o número está.
- **Listas dentro das janelas de confirmação voltam a quebrar linha** — correção no componente compartilhado pelos quatro sistemas.

---

## [0.39.2] — 2026-07-25

### Documentação
- **Auditoria do manual e do README.** Cinco blocos do cadastro de contrato que existiam sem documentação entraram no manual: **Fiscalização Mensal**, **Matriz de Risco**, **Recebimento do Objeto**, **Subcontratação** e **Item do PCA**, além do alerta de vigência acima do limite do Art. 107.
- **Correções do que não correspondia ao sistema:** o backup do banco (é pacote .zip com banco e anexos desde a 0.36.0), a aba onde ele fica (Dados, não Backup), a troca da senha padrão (tela bloqueante no primeiro login, que recusa `admin123`), o índice de reajuste (o sistema busca a variação acumulada direto no Banco Central), o alerta de fornecedor (virou selo na linha da tabela, não coloração de card), a aba Interface (tema, largura, fonte e cor de destaque) e a barra lateral (sem "Notificações", com a Auditoria marcada como exclusiva de administrador).
- **Passaram a ser documentados:** o painel **Erros recentes do sistema**, a **sincronização do cadastro de fornecedores** com SGCD/SGEA por CNPJ, as **etiquetas** em contratos e atas, o indicador **Fiscalização Atrasada**, o **aniversário de reajuste** na Agenda, o **QR de autenticidade** e o reanexo do PDF assinado, o **Factory Reset**, o **Relatório de Backup e Integridade** e a restrição de backup/restauração a administradores.
- **README:** Agenda descrita por completo, sincronização desdobrada em duas (backup JSON entre instalações e cadastro por CNPJ entre sistemas), funcionalidades recentes acrescentadas (MINUTA, bloqueio de edição concorrente, faixa de servidor desatualizado, erros recentes e etiquetas) e árvore de arquivos atualizada — sem o `browser-profile/`, que não existe mais, e com o esqueleto compartilhado e o waitress vendorizado.

### Corrigido
- **CHANGELOG e Histórico de Versões:** o bloco mais antigo (0.1.0 a 0.5.1) estava fora de ordem — 0.5.1 aparecia depois da 0.5.0 e o trecho 0.1.0→0.4.0 vinha em ordem crescente, contra a ordem do resto do arquivo. Reordenado nos dois documentos.

---

## [0.39.1] — 2026-07-25

### Corrigido
- **Campos dos formulários de adição de item (ATA) e de aditivo (contrato) ganharam o visual arredondado** dos demais campos, em vez do estilo "quadradão" cru.

---

## [0.39.0] — 2026-07-25

### Alterado
- **A tela de Fornecedores virou tabela** (mesmo padrão dos demais cadastros), no lugar da lista de cards: colunas Razão Social, CNPJ e Situação, com **ordenação ao clicar no cabeçalho** e **seleção em massa** (excluir vários para a Lixeira). O detalhe completo do fornecedor — dados, certidões, sanções, consulta de CNPJ e CEIS/CNEP, edição — passou para uma **janela (modal)**, aberta ao clicar na linha ou em Editar.
- **Padronização visual:** a tabela da **Trilha de Auditoria** passa a usar o mesmo estilo de tabela canônico das demais listas do sistema (cabeçalho, espaçamento e zebra iguais). Sem mudança de comportamento.

### Corrigido
- **Modo escuro:** os selos de situação do fornecedor (ativa/inativa/outra) ganharam cores próprias para o tema escuro, em vez das cores claras que destoavam do fundo escuro.

---

## [0.38.1] — 2026-07-25

### Corrigido
- **A data do e-mail de resumo diário volta ao formato brasileiro.** Estava saindo como `2026-07-25` (ISO) no assunto e no corpo; passa a `25/07/2026`.

### Documentação
- Corrige no README a referência ao **Diagnóstico de rede** pelo menu de inicialização: era "opção **[3]**" (numeração do menu antigo, já removida) e passa a "opção **[1]**", igual ao menu atual (`[1] Diagnóstico` / `[2] Iniciar Servidor`).

---

## [0.38.0] — 2026-07-25

### Alterado
- **O servidor interno foi trocado por um mais robusto (waitress).** Em uso simultâneo, o servidor anterior às vezes parava sozinho ("servidor parou"); o novo aguenta várias requisições ao mesmo tempo sem cair. O jeito de usar não muda — continua abrindo pelo mesmo atalho.

### Adicionado
- **Motor de captura e tratamento de erros.** O sistema passa a registrar falhas num arquivo de log rotativo (sem estourar o disco), separa "erro de quem usa" de "erro do programa", captura também erros do navegador e traz a tela **Erros recentes** no Diagnóstico (só para administradores). Se o programa travar de vez, o motivo fica gravado num arquivo `*_crash.log`.

### Corrigido
- **A aba de Auditoria volta a acompanhar o modo Compacto/Expandido da interface.** Antes ela ignorava a largura escolhida.

### Documentação
- Padronização do **README** e do **LICENSE** entre os sistemas da família (não altera o sistema): subseção "Menu de inicialização" unificada e igual ao código, referência aos sistemas irmãos na Descrição, seção "Documentos Gerados pelo Sistema" (com a correção do menu de inicialização, que documentava o modo "Pessoal" já removido do código), e LICENSE normalizado para o template MIT canônico (LF) — o GitHub voltou a classificar o repositório como MIT.

---

## [0.37.0] — 2026-07-24

### Adicionado
- **Cadastro de fornecedores compartilhado entre os sistemas.** Agora dá para **exportar** o cadastro de fornecedores e **sincronizá-lo** com os outros sistemas da família por CNPJ: soma os novos, atualiza os que mudaram e, quando o mesmo fornecedor foi editado dos dois lados desde a última sincronização, abre uma tela para você escolher qual versão manter. Não apaga nada.

### Segurança
- **A senha de fábrica não pode mais ser definida como nova senha.** Ao trocar a senha, `admin123` (a padrão publicada no manual) é recusada — antes era possível "trocar" para ela e assim contornar a exigência de sair da senha padrão.

---

## [0.36.0] — 2026-07-24

### Alterado
- **O backup do banco passa a incluir os anexos.** Antes o "backup do banco" era só o arquivo do banco de dados; os documentos digitalizados (PDFs), que ficam guardados fora do banco, não iam junto. Agora ele é um pacote **.zip** com o banco **e** a pasta de anexos, e restaurá-lo recupera também os arquivos. Backups no formato antigo (.db) continuam podendo ser restaurados — apenas sem os anexos, como antes.
- **Formato de backup unificado com os demais sistemas da família**, com leitura compatível: nenhum arquivo de backup já gerado deixa de ser restaurável.

---

## [0.35.1] — 2026-07-24

### Corrigido
- **Instalações anteriores à troca de senha obrigatória seguiam aceitando a senha de fábrica.** A exigência de trocar a senha só era gravada no momento em que o usuário administrador é criado; nos bancos que já existiam, a coluna nasceu desligada pelo padrão da migração. Ou seja: a proteção valia para instalação nova e deixava de fora justamente as que já estavam em uso, que continuavam abertas com a senha publicada no manual. O servidor passa a conferir a cada início se alguma conta ainda está na senha padrão e a exigir a troca — o que cobre também quem voltar a ela ou for cadastrado com ela.

---

## [0.35.0] — 2026-07-24

### Corrigido
- **Duas pessoas editando o mesmo contrato ou ata: a última apagava o trabalho da primeira, em silêncio.** Ambas recebiam confirmação de sucesso. Agora a gravação é recusada quando o registro mudou desde que a tela o carregou, com aviso pedindo para reabrir. O mesmo mecanismo que o SGCD já usava.

---

## [0.34.0] — 2026-07-24

### Corrigido
- **Remover um aditivo não desfazia a conta.** O contrato continuava com o valor global e o percentual de quando o aditivo existia — ou seja, valendo um aditivo que não está mais lá, e com o percentual comparado ao limite legal errado. Agora valor e percentuais são sempre recalculados a partir da lista de aditivos, tanto ao acrescentar quanto ao remover.
- **Acréscimo e supressão deixam de se anular.** Um aditivo de +25% seguido de outro de −25% exibia "0%", escondendo que os dois limites do art. 125 da Lei 14.133/2021 tinham sido usados. Passam a ser contados separadamente, cada um contra o seu teto de 25%, e a tela mostra os dois quando existem.
- **Leitura de valores em dinheiro unificada** com a mesma regra do restante da família (ver CHANGELOG do SGCD).

### Alterado
- O valor global e o valor original do contrato passam a ser gravados como número desde o cadastro. Antes nasciam como texto e só viravam número no primeiro aditivo.

---

## [0.33.0] — 2026-07-24

### Adicionado
- **Alterações nos Dados da Organização e no brasão passam a ficar registradas na Trilha de Auditoria**, com autor, data e quais campos mudaram. Esses dados saem em todo documento gerado — nome do órgão, município, autoridade, brasão —, e qualquer usuário pode editá-los (segue assim, é a forma de trabalho do setor); o que faltava era o rastro de quem mudou. Reenviar a tela sem alterar nada não gera evento.

---

## [0.32.0] — 2026-07-24

### Corrigido
- **A troca da senha padrão passou a valer no servidor.** A tela de "troque a senha no primeiro acesso" era só do navegador: quem conversasse diretamente com o sistema entrava com a senha padrão — que está no manual e no README — e usava tudo, inclusive as telas de administrador, enquanto ninguém tivesse trocado. Agora, com a troca pendente, o servidor só aceita as chamadas necessárias para exibir e concluir a própria troca; qualquer outra é recusada.
- **A chave de API do Portal da Transparência e a conta de e-mail do órgão apareciam para qualquer usuário.** A tela de Configurações é aberta a todos (usa os dados de organização), e junto vinham a chave do Portal, o endereço da conta de e-mail e a pasta de backup. Passaram a ir só para o administrador. A senha do e-mail nunca esteve nessa lista.

### Alterado
- Removidas mensagens de depuração que sobraram no console do servidor e imprimiam, a cada leitura ou gravação de configurações, o nome de quem estava usando o sistema.

---

## [0.31.10] — 2026-07-24

### Corrigido
- **A senha do e-mail do sistema saía dentro do arquivo de backup.** O backup em JSON exportava todas as configurações, e entre elas está a senha do SMTP (guardada em texto puro) e a chave do Portal da Transparência. Como esse é o arquivo que se envia a outra máquina para sincronizar, essas credenciais circulavam junto. Elas passaram a ficar de fora. **Restaurar não as perde:** o que o arquivo não traz é preservado como já está no sistema.

---

## [0.31.9] — 2026-07-24

### Corrigido
- **Uma restauração que falhava no meio deixava o sistema vazio.** Os registros atuais eram apagados e a confirmação acontecia *antes* de os dados do arquivo serem gravados — se qualquer item do arquivo estivesse malformado, o apagamento já estava consolidado e nada era restaurado. Agora a restauração inteira é uma operação só: qualquer falha desfaz tudo e o banco continua como estava. O sistema também passou a responder com uma mensagem clara em vez de erro genérico.
- **Restaurar um backup esvaziava a Lixeira, devolvendo tudo ao cadastro.** A marca de exclusão fica numa coluna do banco, fora do conteúdo do registro, e não ia no arquivo: contratos, atas e fornecedores que estavam na Lixeira voltavam como ativos.
- **Cadastrar um fornecedor com o mesmo identificador de um excluído** o tirava da Lixeira silenciosamente.

---

## [0.31.8] — 2026-07-23

### Corrigido
- **Som duplicado nas caixas de confirmação.** Confirmar ou cancelar tocava dois sons sobrepostos: o tratamento global de clique já sonoriza qualquer botão, e a cópia local da caixa de confirmação tocava um segundo som por conta própria. Ao unificar a caixa de confirmação com a do esqueleto, a duplicação saiu.

### Alterado
- **Fonte única para o que os quatro sistemas repetiam.** O aviso de rodapé (`toast`) e a caixa de confirmação (`customConfirm`) existiam em cópia local em cada sistema, quase idênticas: uma correção feita em um não chegava aos outros. Passaram a vir do esqueleto compartilhado — o som continua sendo de cada sistema, através de um gancho (`_toastSom`). Saiu junto uma variável de cache de elementos que ficou sem uso.
- **Histórico de Versões no manual.** A seção 15 do `MANUAL.html` só remetia ao `CHANGELOG.md` do repositório — que o usuário do sistema não abre. Passou a trazer o histórico completo, no mesmo formato dos manuais dos outros sistemas.
- **Margem de impressão dos documentos com fonte única.** O bloco `@page` (A4, 20 mm, "Folha N" no rodapé) estava copiado em cinco lugares nos quatro sistemas; agora é uma constante só, no esqueleto. Era exatamente o trecho que a versão anterior teve de corrigir em cinco lugares de uma vez.
- **O esqueleto compartilhado passou a ter histórico.** Os arquivos comuns (`base.css`, `base.js`, `sgx_base.py`) tinham fonte única, mas fora de qualquer repositório: um erro neles se espalhava para os quatro sistemas sem registro do que mudou nem como voltar atrás. Agora são versionados.
- **O CI acusa cópia do esqueleto editada por fora.** Alterar `base.js` dentro deste repositório funciona, passa no lint e é apagado sem aviso na próxima distribuição. O CI passou a conferir as cópias contra o manifesto `_esqueleto.sha256` e quebra o build quando divergem. Verificado nos dois sentidos: acusa edição real e ignora diferença de quebra de linha (o repositório guarda LF, o runner Windows faz checkout com CRLF).

---

## [0.31.7] — 2026-07-22

### Corrigido
- **Envio de e-mail podia prender uma thread do servidor para sempre.** O helper compartilhado `send_email_raw` abria a conexão SMTP sem `timeout`, e o padrão do Python é esperar indefinidamente; como o servidor é multithread, cada envio a um SMTP que aceita a conexão e não responde deixava uma thread presa — inclusive no resumo diário automático, que se repete todo dia. Agora o timeout é de 30 s e a falha vira mensagem de erro. Verificado contra um SMTP que nunca responde: falha em 30 s, em vez de travar.
- **Tecla Esc deixava a página sem rolagem.** O tratamento genérico de Esc (compartilhado) era registrado antes dos tratamentos de cada tela e apenas escondia a janela; o tratamento da tela, ao rodar depois, via a janela "já fechada" e pulava a rotina de fechamento — que é quem devolve a rolagem da página. Fechar um modal com Esc travava a rolagem até recarregar. O tratamento genérico passou a ser registrado por último, e ainda devolve a rolagem por segurança.
- **Margem de impressão dos documentos.** A margem agora é declarada no `@page` (vale para **todas** as páginas) e padronizada em **20 mm** nos quatro lados, em todos os modelos de documento e relatório. Antes, o recuo era zerado na impressão em vários modelos e o rodapé saía a ~4 mm da borda — dentro da faixa que muitas impressoras não imprimem, com risco de cortar o código de autenticidade. Medido em PDF gerado: 20,1 mm.

---

## [0.31.6] — 2026-07-22

### Corrigido
- **Falhas silenciosas na comunicação com o servidor.** Vários pontos checavam `r.ok` sem antes verificar se a chamada devolveu resposta — e a camada de API devolve `null` quando a sessão expira (401) ou a rede falha. O resultado era um `TypeError` engolido: o botão simplesmente não fazia nada, sem mensagem alguma. Todos os pontos passaram a usar a guarda que o próprio código já adotava em outros lugares.
- **Sessão deslizante.** A sessão (60s) era renovada **apenas** pelo `/api/auth/ping`, um `setInterval` que o navegador estrangula em aba de segundo plano — quem ficasse redigindo com a aba atrás perdia a sessão e a ação seguinte falhava com 401. Agora **qualquer requisição autenticada renova** a sessão. O backup automático não muda: navegador fechado não faz requisições, então a sessão ociosa continua expirando em 60s.

---

## [0.31.5] — 2026-07-22

### Corrigido
- Campos de busca (Contratos, Atas e Fornecedores) agora usam um estilo único compartilhado (`.search-inp` no `base.css`), garantindo o mesmo visual arredondado em toda a família e evitando divergência entre telas.

---

## [0.31.4] — 2026-07-22

### Modificado
- **Busca com ✕ para limpar** nas listas de **Contratos** e **Atas**: o campo de busca ganhou o mesmo botão ✕ já usado em Fornecedores — aparece ao digitar, limpa a busca ao clicar. Helper compartilhado no `base.js`.

---

## [0.31.3] — 2026-07-22

### Corrigido
- Inputs da aba Dados (pasta de backup, backups mantidos) agora aparecem arredondados: a classe `.input` que esses campos usavam **nunca havia sido definida** no CSS, então ficavam com o visual cru do navegador. Definida no `base.css` compartilhado.

## [0.31.2] — 2026-07-21

### Corrigido
- **Relatório de Backup e Integridade**: a mensagem de erro deixou de cravar "acesso restrito a administradores" para qualquer falha — agora mostra o motivo real devolvido pelo servidor (irmão da correção feita no SGEA v0.22.1, encontrado numa varredura de erro mascarado).
- **Acessibilidade (WCAG 1.4.3)**: o contraste do botão "Dispensar" da faixa de aviso de servidor desatualizado subiu de ~3,5:1 para 8,1:1, com `aria-label` e alvo de toque maior.

### Removido
- Endpoints destrutivos sem uso: `DELETE /api/{fornecedores,audit}/all` — mecanismo de factory-reset antigo, já substituído pelo `/api/wipe` único. Remover rota destrutiva sem chamador reduz a superfície de ataque.

### Interno
- Três funções que estavam copiadas idênticas nos 4 sistemas (`checarVersaoServidor` no `base.js`; `backup_ts` e `pick_folder_dialog` no `sgx_base.py`) foram consolidadas no esqueleto compartilhado (fonte única via `sync.py`), sem mudança de comportamento. O `Iniciar SGCA.bat` passou a encerrar um servidor preso na porta antes de subir o novo.

## [0.31.1] — 2026-07-20

### Adicionado
- **Aviso de servidor desatualizado.** O `/health` do servidor passou a informar a versão em execução, e o app compara com a versão do `SGCA.html` carregado ao entrar. Se o servidor Python em execução for mais antigo que a página (processo iniciado antes de uma atualização, situação em que rotas novas dão "Rota não encontrada" até reiniciar), uma faixa de alerta no topo orienta a reiniciar pelo `Iniciar SGCA.bat`. `SERVER_VERSION` no `server.py` deve acompanhar o `SGCA_VERSION` a cada release.

## [0.31.0] — 2026-07-20

### Adicionado
- **Alimentar do Fiorilli** — novo botão na barra de ferramentas da tela de Atas que preenche automaticamente a **quantidade utilizada** dos itens a partir do sistema contábil oficial (Fiorilli), dispensando a digitação manual. Importa o relatório **"Listagem de Licitações Integradas e Pedidos"** (módulo Compras → 07. Relatórios → 07.05. Licitações → 07.05.02, export **CSV Dados**); um mesmo arquivo pode conter um processo licitatório ou todos, com detecção automática. Casa cada item por **processo licitatório + código Fiorilli/CADPRO** e grava a quantidade líquida pedida (Σ pedidos − Σ cancelamentos) por substituição (idempotente — reimportar não altera). Prévia agrupada por ata (valor atual → novo, com saldo negativo sinalizado) e lista dos itens do relatório ainda sem código cadastrado nas atas. **Somente leitura** em relação ao Fiorilli, que continua sendo o razão oficial.
- Novo campo **código Fiorilli/CADPRO** no cadastro de item da ata (chave de casamento com o relatório oficial).

## [0.30.3] — 2026-07-20

### Alterado
- **Lote 4 da auditoria de design**: fim do fallback de brasão nos documentos (buscava um `brasao.png` local) — sem brasão configurado em Configurações, o documento sai sem imagem, como no SGEA. Instalações com brasão configurado não mudam. Token `--violet` e regras de fronteira novas no `base.css`/`DESIGN.md` compartilhados.

## [0.30.2] — 2026-07-20

### Alterado
- **Legibilidade do modo escuro**: novo token `--brand-text` — textos na cor da marca (números, links, metadados de cards) agora clareiam automaticamente no tema escuro (antes: navy sobre fundo escuro, quase ilegível). Aplicado via troca global `color: var(--brand)` → `var(--brand-text)`.
- **Componentes canônicos novos no `base.css`** (auditoria de design 2026-07-20): tabela de listagem (`.list-table`, com cabeçalho, zebra e hover) e variantes de badge (`badge-ok/warn/danger/neutral`). `DESIGN.md` atualizado (token, tabela e regra do acento esquerdo nos stat-cards).
- **Filtros de Contratos e Atas estilizados** — busca e selects usavam controles nativos do navegador; agora seguem o padrão `.filters` (mesmo visual da tela de Fornecedores).
- Cosmético: rodapé da sidebar mostra **"Administrador"** para admins sem cargo cadastrado; linha do órgão oculta até ser configurado; respiro após "Ignorar SSL" nos blocos SMTP.

## [0.30.1] — 2026-07-20

### Alterado
- **"Meu E-mail (SMTP)" movido para a aba Segurança** de Configurações (ao lado de "Alterar Minha Senha" — é uma credencial pessoal), separando a config pessoal da config do sistema; mesmo arranjo do SGDP. A aba **Comunicação** (config do sistema) agora aparece só para administradores, com uma nota apontando para a aba Segurança.

### Removido
- **Seção de SMTP no modal de edição de usuário** — cada usuário configura a própria conta na aba Segurança; a config inclui a senha do e-mail pessoal, que não cabe ao administrador digitar. (Endpoints do servidor mantidos; `GET /api/usuarios/{id}/smtp` segue em uso pelo próprio usuário.)

## [0.30.0] — 2026-07-19

### Adicionado
- **Config de e-mail (SMTP) por usuário** — 8 colunas `smtp_*` em `usuarios` (migração aditiva) + seção **"Meu E-mail (SMTP)"** em Configurações → Comunicação, disponível a todos os usuários. O envio manual do **Resumo da Agenda** estando logado sai pela conta do usuário (`get_user_smtp(user_id)` com **fallback** para a config do sistema). Botão "Copiar do sistema" (host/porta/segurança, sem a senha). Admin edita a config de qualquer usuário no modal de Usuários. Novo endpoint `GET /api/usuarios/{id}/smtp` (self ou admin); `PUT /api/usuarios/{id}` aceita os campos `smtp_*` (não-admin só no próprio registro). O **resumo diário automático** (e os avisos ao fiscal) continuam usando a config do sistema.

### Alterado
- **Config SMTP migrada do navegador para o servidor** (mesma mudança do SGCD v2.35.0): fim da cópia por navegador em `localStorage` com senha cifrada; `/send-email` resolve a config server-side e **a senha nunca passa pelo navegador** — o modo antigo ficou restrito ao "Testar conexão" (testa valores digitados, sem salvar). `GET /api/settings` deixou de retornar `smtp_pass` (expõe só `smtp_pass_set`). Seção SMTP de Configurações dividida em "E-mail do sistema" (admin) e "Meu E-mail" (por usuário). Removida a cadeia de criptografia client-side; `backup.smtp` de backups antigos é ignorado na restauração.

### Migração para quem já usa
- A config do **admin** já estava no servidor (`sys_settings`) — nada a fazer. Configs que usuários não-admin tinham **por navegador** não migram: cada um reinforma a própria conta em "Meu E-mail (SMTP)".

## [0.29.3] — 2026-07-19

### Alterado
- **Motor de exportação Excel (.xlsx) movido para o `base.js` compartilhado** da família (`_exportarXlsx`/`_zipStore`/`_colLetter`/`_xlsxCellXml`/`_crc32`). Refactor interno — sem qualquer mudança de comportamento no SGCA; o objetivo foi disponibilizar o mesmo gerador de planilhas para SGCD e SGEA sem duplicar código.

## [0.29.2] — 2026-07-19

### Corrigido
- **Fornecedores pessoa física eram sinalizados com "CNPJ inválido" indevidamente** — o campo `cnpj` do cadastro guarda tanto CNPJ (14 dígitos) quanto CPF (11 dígitos) de pessoas físicas, mas o Diagnóstico de Integridade e a coloração de cards em Fornecedores sempre validavam com o algoritmo de dígito verificador do CNPJ, que rejeita qualquer número de 11 dígitos. Agora documentos de 11 dígitos são validados com o algoritmo oficial de CPF (nova função `validarCpf`); um CPF malformado passa a aparecer como "CPF inválido" (em vez de "CNPJ inválido"), e duplicidade de documento entre dois cadastros de 11 dígitos aparece como "CPF duplicado"

## [0.29.1] — 2026-07-19

### Adicionado
- **Avisos/erros de fornecedor no Diagnóstico de Integridade agora são clicáveis** — clicar num item de "CNPJ duplicado" ou "CNPJ inválido" na lista do diagnóstico (Configurações → Diagnóstico) leva direto ao cadastro daquele fornecedor, já aberto para edição. Limpa busca/filtro da tela de Fornecedores antes de abrir, para garantir que o card apareça mesmo se Ativos/Inativos estivesse selecionado numa visita anterior

### Corrigido
- **`<title>` do MANUAL.html ficou defasado por 3 versões** (`v0.27.15` enquanto o resto do manual já estava em `v0.29.0`) — os bumps de versão anteriores não alcançavam essa linha porque o `sed` só substitui o valor esperado da versão anterior, não "o que estiver desatualizado"

## [0.29.0] — 2026-07-19

### Adicionado
- **Marca d'água "MINUTA"** nos documentos de contrato (Extrato, Termos de Aditivo/Apostilamento, Matriz de Risco, Termo de Recebimento, Termo de Rescisão) enquanto o contrato **ainda não tem um PDF assinado anexado** ao registro. Assim que um PDF assinado é anexado, os documentos passam a ser gerados sem a marca. Os relatórios gerenciais (Auditoria, Contratos, Atas, Fornecedores etc.) nunca recebem a marca. Alinha o comportamento ao do SGCD.

## [0.28.1] — 2026-07-18

### Alterado
- **Helper de exportação consolidado no `base.js` compartilhado** (`_salvarArquivoComo`) e o download do **modelo de importação de fornecedores** passou a usar o diálogo "Salvar como" como os demais exports.

## [0.28.0] — 2026-07-18

### Removido
- **Assinatura digital ICP-Brasil.** A assinatura de anexos de Contrato e Ata com certificado A1 (`.pfx`) foi removida por completo: botão/modal de assinar, a página pública de verificação (`/verificar/<código>`), o registro de assinaturas, a dependência opcional `pyhanko` (o SGCA volta a rodar 100% com a biblioteca padrão do Python) e o script `Instalar Assinatura ICP-Brasil.bat`. A tabela `signatures` e seus dados são descartados na inicialização; backups antigos que ainda tragam esse bloco são aceitos e o bloco é ignorado. **O bloco de assinatura manuscrita nos documentos gerados permanece.** A reanexação de documentos gerados (Extrato, Termos, etc.) continua funcionando — apenas sem a etapa de assinatura digital.

## [0.27.15] — 2026-07-18

### Corrigido
- **Nome do arquivo exportado de Fornecedores não diferenciava o filtro ativo** — CSV e Excel de Ativos/Inativos/Pendências saíam todos com o mesmo nome (`SGCA_fornecedores_DATA`). Agora o nome leva o sufixo do filtro: `SGCA_fornecedores_Ativos_DATA`, `_Inativos_`, `_Pendencias_` (Todos continua sem sufixo)

## [0.27.14] — 2026-07-18

### Alterado
- **Exportar CSV/Excel de Fornecedores agora respeita os filtros ativos na tela** (busca + botões Todos/Ativos/Inativos/Pendências) — antes exportava sempre o cadastro inteiro (só a busca por texto era aplicada). Reaproveita a mesma checagem de filtro usada pelos botões
- **Todos os botões Exportar CSV/Excel (Contratos, Atas, Fornecedores, Auditoria) abrem o diálogo nativo do navegador para escolher onde salvar** (File System Access API, Chrome/Edge), em vez de sempre cair na pasta Downloads padrão — mesmo mecanismo já usado na Exportação PNCP desde a v0.23.2; navegadores sem suporte continuam com o download tradicional. Cancelar o diálogo não gera evento de auditoria nem toast de sucesso

## [0.27.13] — 2026-07-18

### Adicionado
- **Botões de filtro em Fornecedores** (Todos/Ativos/Inativos/Pendências), abaixo da busca. Ativos = situação "ATIVA"; Inativos = "BAIXADA"/"INAPTA"/"CANCELADA"; Pendências = CNPJ inválido ou duplicado (mesma checagem que já colore os cards) OU pelo menos uma certidão vencida

## [0.27.12] — 2026-07-18

### Alterado
- **Ordenação de Fornecedores simplificada** — removidas as opções "Situação (Ativa primeiro)" e "Certidões vencidas"; adicionada "↑ Mais antigo". Restam: Mais recente, Mais antigo, A → Z, Z → A

### Corrigido
- **Ordenação "Mais recente" nunca funcionava de verdade** — `updatedAt`/`addedAt` do fornecedor vêm ora como epoch numérico (gravado pelo frontend), ora como string ISO (gravado pelo `_now()` do server.py); a comparação `a.updatedAt - b.updatedAt` entre duas strings sempre resulta em `NaN`, então o `sort()` não reordenava nada — a lista ficava na ordem que a API retornava. Corrigido normalizando os dois formatos para epoch antes de comparar. Bug pré-existente, encontrado ao implementar a opção "Mais antigo" acima (mesma comparação quebrada)

## [0.27.11] — 2026-07-18

### Adicionado
- **Coloração dos cards de Fornecedores conforme o Diagnóstico de Integridade** — o cadastro de Fornecedores passa a colorir cada card de acordo com as mesmas checagens do Diagnóstico (Configurações → Diagnóstico): card avermelhado com borda esquerda vermelha para CNPJ duplicado (erro crítico), amarelado para CNPJ inválido (aviso), com um selinho indicando o motivo. Reutiliza as mesmas checagens do `runDiagnostico()`, sem duplicar a lógica de validação

## [0.27.10] — 2026-07-18

### Corrigido (acessibilidade — WCAG 2.1 AA)
- **`alt` na prévia do brasão** (WCAG 1.1.1) — a imagem de pré-visualização do brasão nas Configurações passou a ter texto alternativo, igualando SGCD/SGDP.

## [0.27.9] — 2026-07-18

### Corrigido
- **Parsing de valores (`_float`) mais robusto** — aceita moeda no formato brasileiro com separador de milhar (`1.234,56` deixou de virar nulo) e número puro; entradas inválidas continuam retornando nulo sem quebrar. Mesma correção aplicada em SGCD e SGEA. (O off-by-one de datas corrigido no SGCD não ocorria aqui — o SGCA já usava parsing de data seguro.)

## [0.27.8] — 2026-07-18

### Alterado
- **Rótulos de "Cor de destaque" (Institucional/Azul/Verde/Roxo) agora em caixa normal**, alinhados ao SGDP — antes vinham em MAIÚSCULAS/negrito por causa do wrapper `.info-field`. Removido o wrapper apenas desse seletor. Verificado no navegador.

## [0.27.7] — 2026-07-18

### Corrigido
- **Bolinhas de cor em "Cor de destaque" apareciam como finos palitos verticais** (o quadradinho de cor era espremido de 14px para ~2px pelo `.info-field input{width:100%}` no label flex). Adicionado `flex-shrink:0` às amostras, que voltam a ser círculos de 14px. Mesmo ajuste em SGCD e SGEA.

## [0.27.6] — 2026-07-18

### Corrigido
- **Itens de menu `admin-only` (ex.: Auditoria) não apareciam nem para administradores.** Eram revelados com `style.display = ''`, que caía na regra `.admin-only { display:none }` do estilo compartilhado e mantinha o item oculto mesmo para admins. Agora, para administradores, a classe `.admin-only` é removida (o elemento volta ao display natural); para não-admins continua oculto. Mesma correção aplicada em SGCD e SGDP.

## [0.27.5] — 2026-07-17

### Removido
- **Banner de alerta de backup morto** — o `#backup-alert-banner` nunca era exibido (a função `checkBackupAlert()` era vazia; os backups são automáticos no servidor). Removidos markup, função e chamada.
- **Resíduos de skeleton** — keyframes órfãos (`skeleton-pulse`, `shimmer`) e constantes JS não usadas, deixados após a remoção do CSS morto na v0.27.4.

## [0.27.4] — 2026-07-17

### Removido
- **Limpeza de CSS morto** — removidas 241 regras de estilo (~551 linhas) que definiam classes nunca usadas no HTML/JS (estilos órfãos de componentes que não chegaram a ser construídos ou foram renomeados: timeline de etapas, tabela de processos, painéis de fracionamento, cartões de proposta, upload zone, skeletons, entre muitas outras). Três regras que misturavam classes vivas e mortas foram aparadas para manter só as vivas. Sem qualquer efeito visual. Verificado com lint, testes unitários e E2E.

## [0.27.3] — 2026-07-17

### Alterado
- **Ícones da barra lateral agora são emoji** (📊 Dashboard, 📄 Contratos, 📑 Atas de RP, 🏢 Fornecedores, 📅 Agenda, 🗑️ Lixeira, 🕘 Auditoria, ⚙️ Configurações), no mesmo estilo do SGEA — substituindo os ícones SVG de linha.
- **Notificações movidas para o bloco de usuário** — o sino (🔔, com o mesmo contador) saiu da lista de menu e passou a ficar no rodapé da barra lateral, ao lado do botão de sair, num layout mais compacto igual ao do SGEA. O painel de notificações e seu comportamento continuam idênticos.

## [0.27.2] — 2026-07-15

### Corrigido
- **Card "Valor Total Vigente" do Dashboard ainda ficava com o dobro de largura na correção anterior (v0.27.1)** — a tela de Dashboard tem mais cards que Contratos/Atas, então a coluna calculada pelo grid fica mais estreita ali, e a margem que sobrava para o valor caber numa linha só (com a fonte de 1,3rem usada até então) era mínima o bastante para variar por navegador/monitor. Reduzida a fonte do valor de 1,3rem para 1,1rem nos três cards, dando folga real para o caso comum caber na largura padrão; o mecanismo de expansão automática (v0.27.1) continua como reforço para valores realmente grandes
- **README.md desatualizado desde a v0.27.0** — a lista de funcionalidades não mencionava Termo de Rescisão, Execução Financeira, Consulta CEIS/CNEP nem Exportação Excel, e ainda trazia uma nota de "fora de escopo" para controle de pagamentos que a Execução Financeira tornou incorreta

## [0.27.1] — 2026-07-15

### Corrigido
- **Card "Valor Total Vigente/Registrado" sempre com o dobro de largura** (Dashboard, Contratos e Atas), mesmo quando o valor cabia tranquilamente na largura padrão dos outros cards. Agora ele começa com a mesma largura dos demais e só expande para 2 colunas quando o valor formatado realmente não couber numa linha só — medido dinamicamente após cada renderização

## [0.27.0] — 2026-07-15

### Adicionado
- **Termo de Rescisão** — novo campo "Motivo/Fundamentação da Rescisão" no Contrato (visível quando o status é "Rescindido") e botão "📄 Termo de Rescisão" no rodapé, que gera o documento formal com fundamento nos arts. 137 a 139 da Lei nº 14.133/2021, no mesmo padrão dos demais documentos gerados
- **Consulta CEIS/CNEP automatizada** — botão "🔍 Consultar CEIS/CNEP" no cadastro de Fornecedores, complementando os links manuais já existentes. Consulta a API do Portal da Transparência/CGU via proxy do servidor, usando chave de API própria (gratuita) configurada em Configurações → Organização → Integrações
- **Execução Financeira do Contrato e da Ata** — novo registro de pagamentos (data, valor, nº de empenho/NF, observações) com saldo calculado automaticamente contra o valor global do contrato ou o valor total registrado da ata, no mesmo padrão de sub-registro já usado em Fiscalização Mensal/Matriz de Risco/Subcontratação
- **Exportação em Excel (.xlsx)** — botão "Exportar Excel" ao lado do "Exportar CSV" em Contratos, Atas, Fornecedores e Auditoria. Gera um arquivo `.xlsx` real (planilha nativa, valores numéricos, sem necessidade de abrir/converter), usando um writer OOXML mínimo próprio (ZIP sem compressão + XML), sem dependências externas

### Removido
- **~180 linhas de código morto** (`STEPS`, `FIELD_LABELS`, `DATE_FIELDS`, `MONEY_FIELDS`, `SELECT_FIELDS`) — o checklist de 18 etapas de dispensa de licitação, herdado do fork original do SGCD, nunca chegou a ser referenciado em nenhuma tela do SGCA

## [0.26.0] — 2026-07-15

### Adicionado
- **Exclusão de Contratos e Atas** — botão "🗑️ Excluir" no rodapé do modal de edição (contrato/ata existente), seguindo o mesmo rigor de segurança do Factory Reset: (1) aviso geral com alerta informativo se houver fornecedor(es) vinculado(s) — não bloqueia, apenas avisa; (2) confirmação digitando `EXCLUIR <número>`; (3) contagem regressiva de 5s antes de habilitar o botão final. A exclusão move o registro para a Lixeira (soft-delete já existente no backend), com restauração disponível por 30 dias. Novos eventos de auditoria: `CONTRATO_EXCLUIDO` e `ATA_EXCLUIDA`

## [0.25.8] — 2026-07-14

### Removido
- **`create_session`/`delete_session`/`renew_session`/`active_sessions` reimplementadas localmente**, mecanicamente idênticas ao esqueleto compartilhado (`_esqueleto/sgx_base.py`) — agora delegam pro `sgx_base`, mantendo a mesma assinatura local. `get_session()` permanece local (SELECT de colunas explícito por segurança, colunas divergem por sistema)

## [0.25.7] — 2026-07-14

### Corrigido
- **Classe `.dash-top` (cabeçalho de título + ações de cada tela) não estava definida no esqueleto compartilhado (`_esqueleto/base.css`)** — só a classe morta `.view-top` (nunca usada em nenhum dos 4 sistemas) existia lá. Sem efeito visível aqui porque SGCD/SGCA/SGDP definiam `.dash-top` localmente (byte-idêntico entre os 3), mas deixava o SGEA sem nenhum estilo no cabeçalho de cada tela. Corrigido movendo `.dash-top` para `base.css` e removendo a cópia local agora redundante

## [0.25.6] — 2026-07-14

### Removido
- **Handlers locais de Tab-trap e Enter/Espaço em `role="button"`, duplicados dos listeners genéricos do esqueleto compartilhado (`base.js`)** — o handler local de Enter/Espaço era um listener delegado próprio; o de Tab-trap ficava dentro da IIFE de foco automático dos modais (que continua local, pois gerencia o retorno de foco). Mesmo padrão já adotado pelo SGDP ao migrar para o esqueleto

## [0.25.5] — 2026-07-14

### Corrigido
- **`customConfirm()` travava para sempre ao fechar por Esc ou clique fora do overlay** — os dois atalhos de fechamento globais do esqueleto compartilhado (`base.js`) só escondiam `#confirm-overlay` sem resolver a Promise nem remover os listeners dos botões OK/Cancelar, deixando qualquer `await customConfirm(...)` pendurado e vazando listeners a cada abertura. Corrigido para clicar no botão Cancelar (que sempre resolve corretamente e limpa os listeners) em vez de só esconder o overlay. Corrigido na fonte compartilhada (`_esqueleto/base.js`) e propagado aos 4 sistemas via `sync.py`

## [0.25.4] — 2026-07-13

### Alterado
- **Migração para o esqueleto compartilhado da família** (`_esqueleto/base.css`/`base.js`/`sgx_base.py`, vendorizados via `sync.py`) — remove duplicação de CSS/JS/backend entre SGCD/SGCA/SGDP/SGEA (tokens, tema de cor, sidebar, modal, tela de login, toast, busca global, notificações, `get_db`, hashing, sessões, watchdog, e-mail). Sem mudança de comportamento visível; funções com divergência genuína (segurança de sessão, e-mail, configurações) continuam locais a cada sistema.

## [0.25.3] — 2026-07-13

### Adicionado
- **Relatório de Backup e Integridade** — novo botão na aba Dados de Configurações gera um documento imprimível com status do backup automático, tamanhos em disco, contagens gerais do sistema (contratos, atas, fornecedores, arquivos, usuários, etiquetas, assinaturas) e os eventos recentes de backup/restauração/reset, no mesmo padrão do SGDP
- **Auditoria de restauração e reset de fábrica** — restaurar um backup (JSON ou .db) e o reset de fábrica agora registram um evento na trilha de auditoria, o que antes não acontecia

## [0.25.2] — 2026-07-13

### Alterado
- **Modal de "Novo Usuário"/"Editar Usuário" sincronizado com o padrão do SGDP** — largura ampliada de 420px para 560px, e a opção "Ativo" agora fica escondida ao criar um usuário novo (só aparece ao editar), igual aos demais sistemas da família

## [0.25.1] — 2026-07-13

### Corrigido — Auditoria de consistência visual (P3)
- **Seletor de tema "Roxo" com anel de foco/check navy** — o `accent-color` do radio button apontava para o azul institucional (`#1a3a6b`) em vez do roxo (`#5E2750`) mostrado na amostra ao lado. Mesmo bug corrigido também no SGCD
- **Token `--gray-500` no lugar de `--text-secondary`** (indefinido) no rótulo de "ignorar validação SSL" das Configurações

## [0.25.0] — 2026-07-13

### Corrigido — Auditoria de consistência visual (P1)
- **Texto ilegível no modo escuro** — `--gray-600` (11 usos) e `--gray-800` (2 usos) não tinham sobrescrita no `body.dark` e renderizavam a ~1,9:1 de contraste sobre o fundo escuro; adicionadas as mesmas sobrescritas já aplicadas ao SGCD
- **Anel de foco no campo de confirmação do factory reset** (`#_wipe-input`) — ganhou a classe `.wipe-confirm-inp` com o mesmo anel visível do SGCD/SGDP
- **Seções do menu lateral** (`.nav-section`) com opacidade .5 → .65, alinhando o contraste ao padrão dos irmãos (correção de a11y que não tinha sido portada)
- **Resquícios do laranja da marca antiga removidos** — 7 pontos usavam `rgba(233,84,32,…)` (identidade anterior) em anéis de foco e brilhos; agora derivam do brand via `color-mix` e acompanham o tema de cor

## [0.24.2] — 2026-07-11

### Alterado
- **Card "Valor Total Vigente/Registrado" com o dobro de largura** no Dashboard geral, na tela de Contratos e na tela de Atas — evita que valores maiores fiquem espremidos no espaço de uma coluna só de indicador

---

## [0.24.1] — 2026-07-11

### Alterado
- **Modais de Contrato e Ata mais largos** (de 760px/680px para 820px em ambos) — dá mais espaço aos campos de classificação CMMET do item da Ata (Natureza/Classe/Grupo/Subgrupo, Apresentação Comercial) e mantém os dois modais com a mesma largura

---

## [0.24.0] — 2026-07-11

### Adicionado
- **Campos CMMET no item da Ata** — nome padronizado, descrição técnica padronizada, código CMMET, código SCPI, classificação (natureza, classe, grupo, subgrupo), unidade SCPI e apresentação comercial, alinhados à estrutura da Carga Setorial do Catálogo Municipal de Materiais e Especificações Técnicas (CMMET) do órgão. Campos de governança do próprio catálogo (status, versão, responsável pela validação etc.) ficaram de fora por decisão do usuário — pertencem ao ciclo de vida do CMMET, não ao registro do item na ata

---

## [0.23.2] — 2026-07-11

### Corrigido
- **Painel de "Histórico do Registro" transparente** — usava `background: var(--bg-card)`, uma variável CSS nunca definida em nenhum tema; o painel ficava sem cor de fundo, deixando o conteúdo por trás visível através dele. Corrigido definindo `--bg-card` no tema claro e no escuro (também corrige o mesmo problema, até então despercebido, na lista de itens da Agenda de Vencimentos)
- **Campo de Fornecedor espremido no cadastro de item da ARP** — dividia a largura do modal em 4 colunas iguais (Unidade/Qtd./Preço/Fornecedor); nomes de fornecedor reais não cabiam. Fornecedor passa a ocupar a linha inteira, abaixo de Unidade/Qtd./Preço (3 colunas)

### Adicionado
- **"Salvar como" ao exportar PNCP** — Contrato e Ata agora abrem o diálogo nativo do navegador para escolher onde salvar o arquivo (File System Access API, Chrome/Edge), em vez de sempre cair na pasta Downloads padrão; navegadores sem suporte à API continuam com o download tradicional

### Alterado
- **Órgão Gerenciador da Ata pré-preenchido** — ao cadastrar uma nova Ata de Registro de Preços, o campo já vem preenchido com o nome do órgão configurado em Configurações → Organização (permanece editável, para os casos de registro de uma ARP de outro órgão gerenciador). Atas já existentes continuam mostrando o valor salvo, não o padrão

---

## [0.23.0] — 2026-07-10

### Adicionado — Acessibilidade (WCAG 2.1 AA)
Correções de uma auditoria de acessibilidade dedicada (leitura de código + cálculo de contraste, 8 frentes: contraste de cor, texto alternativo, associação de rótulos, teclado, foco, alvo de toque, modais, landmarks).

- **Navegação por teclado** — cards de estatística, itens de notificação, linhas de agenda, cards de kanban, itens de lista de fornecedor/busca global e outros elementos que usavam `<div onclick>` agora têm `role="button"` + `tabindex="0"`, ativados por Enter/Espaço via um único listener delegado
- **Rótulos de formulário associados** — `<label for>` adicionado em mais de 60 campos que dependiam só de proximidade visual: modais de Fornecedor, Usuário, Contrato, Ata, Certidão, Sanção, painel de edição de fornecedor (endereço, contato, QSA), abas de Configurações (Organização, Backup, Segurança, SMTP), overlay de troca de senha obrigatória e modal de assinatura ICP-Brasil
- **Contraste de texto corrigido** — `--gray-400` (usado como cor de texto em vários pontos: ícones de estatística, subtítulos, botão de editar título) tinha 2,54:1 de contraste sobre branco; unificado com `--gray-500` (4,83:1) no modo claro, preservando o valor original no modo escuro (já passava). Badge de estatística no modo escuro também ajustado (3,99:1 → 6,69:1)
- **Indicador de foco visível** — adicionado `box-shadow` de foco nos campos que só trocavam a cor da borda (etapas do checklist, campos de informação, busca de fornecedor, filtros de auditoria, campos em modo escuro)
- **Modais com semântica de diálogo** — `role="dialog"` + `aria-modal="true"` + `aria-labelledby` nos 9 modais do sistema; foco automático no primeiro campo ao abrir; Tab preso dentro do modal enquanto aberto; foco devolvido a quem acionou o modal ao fechar — via `MutationObserver` genérico, sem alterar as 9 funções de abrir/fechar existentes
- **Alt text e área de toque** — botões de ícone (fechar, editar efeito de fundo, mostrar/ocultar senha) com área clicável ampliada sem alterar o tamanho visual; região de conteúdo principal (`#app`) agora é um landmark `<main>`

## [0.22.0] — 2026-07-10

### Corrigido
- **Servidor podia encerrar sozinho no meio do uso (Modo Pessoal)** — `_check_shutdown()` chamava `os._exit(0)` quando a última sessão ativa expirava; uma aba em segundo plano (ex. ao gerar um documento, que abre popup e tira o foco da aba principal) sofria throttling do navegador no `setInterval` do ping, a sessão expirava sem ninguém ter saído de propósito, e o servidor se autodestruía no meio do uso. Corrigido removendo esse caminho inteiramente — o servidor agora só encerra via Ctrl+C no terminal.
- **`SESSION_TTL` aumentado de 15s para 60s** — 15s era propositalmente curto para o antigo modo "Pessoal" detectar rápido que o navegador tinha fechado; sem esse motivo, virou uma margem perigosamente curta para o uso normal (chamadas de API concorrentes no login, aba perdendo foco ao abrir popup de documento).
- **Menu inicial simplificado** — em vez de escolher entre "Pessoal" e "Servidor", agora são só 2 opções: Diagnóstico ou Iniciar Servidor. Iniciar sempre abre o navegador automaticamente e o sistema fica sempre disponível. Removido o botão "Fechar Sistema", que prometia um encerramento que não existe mais.
- **4 pontos de vazamento de conexão SQLite** nos caminhos de backup/restore — `sqlite3.connect()` chamado sem a factory que fecha a conexão automaticamente (mesma classe de bug já corrigida em outros pontos do sistema).
- **Watchdog podia morrer para sempre com valor não-numérico em `auto_backup_keep`** — `_get_backup_cfg()` agora ignora o valor inválido em vez de derrubar a thread.
- **`handle_error` nunca era chamado de verdade** (é método de `socketserver.BaseServer`, não do request handler — exceções não tratadas em qualquer `do_GET/POST/PUT/DELETE` derrubavam a conexão sem log nem resposta ao cliente). Substituído por um `_safe_dispatch` que envolve os 4 handlers, loga o erro e responde 500 em vez de deixar a conexão cair silenciosamente.

## [0.21.0] — 2026-07-10

### Adicionado
- **Suíte de testes E2E (`tests/e2e/`)**, usando Playwright — sobe o servidor real (`SGCA_PORT`/`SGCA_DATA_DIR` isolam porta e banco/uploads/backups dos de produção) e dirige um Chromium de verdade pelo login com troca de senha obrigatória e criação de contrato. Mesma implementação do SGCD

## [0.20.0] — 2026-07-10

### Adicionado
- **`Instalar Assinatura ICP-Brasil.bat`** (opcional) — habilita o pip via `get-pip.py` (incluído) e instala o `pyhanko` quando o servidor usa o Python embarcável, que não vem com pip. `Iniciar SGCA.bat` agora também habilita o módulo `site` na extração do Python embarcável (pré-requisito para o script funcionar depois). Mesma implementação do SGCD

## [0.19.0] — 2026-07-10

### Adicionado
- **Exportar CSV em Fornecedores e Auditoria** — as duas telas ganham o mesmo botão "Exportar CSV" que já existia em Contratos/Atas, respeitando a busca/filtros ativos na tela. Mesma implementação do SGCD

## [0.18.0] — 2026-07-09

### Adicionado
- **Troca de senha obrigatória no primeiro acesso** — o admin padrão (criado com `admin`/`admin123`) é obrigado a definir uma nova senha antes de acessar o sistema, em vez de depender só do aviso impresso no terminal. Nova coluna `usuarios.must_change_password` (migração automática, instalações existentes não são afetadas). Mesma implementação do SGCD

## [0.17.2] — 2026-07-09

### Corrigido
- **Clicar fora de um modal fechava a janela e descartava os dados digitados** — no cadastro de Contrato/Ata em especial, um clique acidental fora da janela apagava tudo o que já tinha sido preenchido. Removido o fechamento por clique fora em todos os overlays (Contrato, Ata, Fornecedor, Usuário, Certidão, Busca Global, CSV, Assinatura); agora só fecham pelo botão Cancelar/✕ ou pela tecla Esc

## [0.17.1] — 2026-07-09

### Corrigido
- **Aviso de vencimento duplicado quando fiscal e gestor são a mesma pessoa** — o e-mail automático de vencimento e o de fiscalização mensal pendente listavam o mesmo contrato duas vezes quando o e-mail do fiscal e o do gestor eram idênticos

### Alterado
- **Capa do Manual Operacional** — removido o parágrafo extenso "Sobre esta versão" (conteúdo já coberto em detalhe nas seções do manual); no lugar, uma referência legal curta à Lei Federal nº 14.133/2021, no mesmo padrão limpo já usado na capa do SGCD

---

## [0.17.0] — 2026-07-09

### Removido
- **Fiscal Substituto** — removido do Contrato (campo e lógica de e-mail); o órgão não usa essa figura

### Adicionado
- **E-mail do Gestor** — o Gestor do Contrato ganha um campo de e-mail e passa a receber os mesmos avisos automáticos que o fiscal (vencimento de contrato e fiscalização mensal pendente), no lugar do papel que era do fiscal substituto

### Alterado
- **Layout dos campos de Fiscal/Gestor** — "Fiscal do Contrato" e "E-mail do Fiscal" em uma linha, "Gestor do Contrato" e "E-mail do Gestor" na linha seguinte

---

## [0.16.0] — 2026-07-09

### Adicionado
- **ARP de Adesão externa** — dois novos campos no Contrato, "Nº da ARP de Adesão" e "Órgão Gerenciador de Origem", para contratos que decorrem de adesão a uma Ata de Registro de Preços de outro órgão gerenciador (não cadastrada no nosso módulo de Atas). O campo "Ata de Origem" (dropdown) continua existindo para o caso de vínculo com uma ARP nossa — os dois são vínculos alternativos, um aviso impede salvar com os dois preenchidos ao mesmo tempo. Exportação PNCP e Extrato de Contrato passam a reconhecer também esse vínculo externo (antes só reconheciam Ata de Origem interna)

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

## [0.5.1] — 2026-07-07

### Corrigido
- **`openContratoModal`/`openAtaModal` exibiam dados desatualizados quando o registro já estava em cache local** (`_contratos`/`_atas`) — o fallback para buscar da API só era acionado quando o item não existia no cache; se existia porém estava desatualizado (ex.: alterado em outra aba, ou reaberto pela Agenda logo após uma edição feita por outro caminho), o modal mostrava os valores antigos. Agora sempre busca da API ao abrir o modal, e mantém o cache local sincronizado com o resultado
- **Remover o anexo do contrato assinado não funcionava** — `delete contrato.anexoContrato` seguido de `PUT` não removia o campo no servidor, pois `_update_contrato` faz um merge raso (`dict.update()`) que só sobrescreve chaves presentes no payload, nunca remove as ausentes. Corrigido enviando `anexoContrato: null` explicitamente em vez de apagar a chave

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

## [0.3.3] — 2026-07-06

### Corrigido
- **Tipo de evento malformado ao restaurar/excluir da lixeira** — `restoreLixeiraItem()`/`purgeLixeiraItem()` geravam o tipo do evento a partir do rótulo de exibição (`cfg.label.toUpperCase()`); para "Ata de RP" isso produzia `"ATA DE RP_RESTAURADO"`, com espaço embutido no tipo. Corrigido com um campo `codigo` estável em `_LIXEIRA_TIPOS`, independente do texto de exibição
- Completados os 6 rótulos que faltavam: `CONTRATO_RESTAURADO`/`CONTRATO_EXPURGADO`, `ATA_RESTAURADO`/`ATA_EXPURGADO`, `FORNECEDOR_RESTAURADO`/`FORNECEDOR_EXPURGADO`

Verificação sistemática (script comparando eventos emitidos no código vs mapa de rótulos) confirmou que SGDP e SGCD já estavam 100% cobertos após as correções da v0.3.2 — só o SGCA tinha esse gap adicional.

---

## [0.3.2] — 2026-07-06

### Corrigido
- **Vocabulário de eventos de auditoria era o do SGCD, não o de contratos/atas** — mapa de rótulos (`_AUDIT_EVENT_LABELS`) tinha só eventos herdados do clone (ETAPA_*, PROCESSO_*, CERTIDAO_* etc.), nenhum deles emitido de fato pelo SGCA; eventos reais (`CONTRATO_CRIADO`, `CONTRATO_EDITADO`, `CONTRATO_ADITIVO`, `ATA_CRIADA`, `ATA_EDITADA`, `FORNECEDOR_EXCLUIDO`, `SYNC_BACKUP`) apareciam crus na tabela. Corrigido trocando pelo vocabulário correto

### Alterado
- Dropdown "Tipo" trocado de lista fixa no HTML para geração dinâmica a partir do mapa de rótulos, evitando desincronia futura
- Coluna "Tipo" renomeada para "Ação", alinhando com o SGDP

---

## [0.3.1] — 2026-07-06

### Alterado
- **Trilha de Auditoria** — timeline agrupada por dia (buscava até 2000 registros de uma vez, filtro 100% no cliente) substituída por tabela com filtros server-side (busca, tipo, período) e paginação via servidor, igual ao SGDP
  - Menu "Auditoria" agora só aparece para administradores
  - `/api/audit` ganhou filtros (q/tipo/de/ate), mas continua sem restrição de admin — usado também pelo histórico de alterações por campo, aberto a qualquer usuário logado

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

## [0.2.1] — 2026-07-06

### Adicionado
- **Atalho Ctrl+K** — foca o campo de busca da seção visível (Contratos ou Atas), no padrão da família SGCD/SGDP

### Corrigido
- **Badge de versão** — o fallback do badge na sidebar mostrava "1.17.0" (resquício do SGCD); corrigido para acompanhar a versão real

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
