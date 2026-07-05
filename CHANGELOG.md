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

## Próximos passos

- Modelagem de dados de Contratos Administrativos e Atas de Registro de Preços (vigências, aditivos, apostilamentos, prorrogações, fiscais/gestores)
- Documentos gerados do novo domínio
- Alertas de vencimento de vigência/prazo
- Kanban por status do contrato/ata
