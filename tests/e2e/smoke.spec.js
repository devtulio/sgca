// Caminho feliz de ponta a ponta: login (com troca de senha obrigatória, já que
// o banco é novo a cada run) → criar contrato.
import { test, expect } from '@playwright/test';

test('login força troca de senha e cria contrato', async ({ page }) => {
  await page.goto('/SGCA.html');

  await page.fill('#pin-username', 'admin');
  await page.fill('#pin-input', 'admin123');
  await page.click('#overlay-pin button[onclick="verificarSenha()"]');

  // Banco novo → admin padrão nasce com troca de senha obrigatória
  await expect(page.locator('#overlay-force-pwd')).toBeVisible();
  await page.fill('#fp-nova', 'novaSenhaE2E123');
  await page.fill('#fp-confirma', 'novaSenhaE2E123');
  await page.click('#overlay-force-pwd button');

  await expect(page.locator('#overlay-pin')).toBeHidden();

  await page.click('#nav-contratos');
  await page.click('button:has-text("Novo Contrato")');
  await page.fill('#c-objeto', 'Prestação de serviços de teste E2E');
  await page.click('.modal-footer button:has-text("Salvar Contrato")');

  const card = page.locator('.kanban-card', { hasText: 'Prestação de serviços de teste E2E' });
  await expect(card).toBeVisible();
});

// "Alimentar do Fiorilli": cria uma ata com item que tem codigoFiorilli, importa
// um CSV mínimo no formato do relatório 07.05.02 e confere que o preview computa a
// pedida líquida (QTD − QTDANU), sinaliza saldo negativo e a worklist de não-casados.
test('Alimentar do Fiorilli preenche a quantidade utilizada das atas', async ({ page }) => {
  // Login resiliente: o DB é compartilhado entre os testes da suíte, então a senha
  // do admin pode já ter sido trocada por um teste anterior — trata os dois casos.
  await page.goto('/SGCA.html');
  await page.fill('#pin-username', 'admin');
  await page.fill('#pin-input', 'admin123');
  await page.click('#overlay-pin button[onclick="verificarSenha()"]');
  await page.waitForTimeout(800);
  if (await page.locator('#overlay-force-pwd').isVisible()) {
    await page.fill('#fp-nova', 'novaSenhaE2E123');
    await page.fill('#fp-confirma', 'novaSenhaE2E123');
    await page.click('#overlay-force-pwd button');
  } else if (await page.locator('#overlay-pin').isVisible()) {
    await page.fill('#pin-input', 'novaSenhaE2E123');
    await page.click('#overlay-pin button[onclick="verificarSenha()"]');
  }
  await expect(page.locator('#overlay-pin')).toBeHidden();

  // ata do processo 7/2025 com 1 item casável (registrada 100, ficará negativa) via API
  await page.evaluate(async () => {
    const gid = () => crypto.randomUUID();
    await API.post('/api/atas', {
      numero: '099/2025', processoOrigem: '7/2025', status: 'vigente', objeto: 'RP teste Fiorilli',
      itens: [{ id: gid(), descricao: 'Item casável', unidade: 'UN', codigoFiorilli: '041.001.988', quantidadeRegistrada: 100, quantidadeUtilizada: 0, precoUnitario: 1 }],
    });
  });

  // CSV mínimo: item casável (QTD 120, anulado 20 → líquida 100... registrada 100 → saldo 0)
  // + um segundo pedido do mesmo item (QTD 30) → líquida total 130 → saldo -30 (negativo)
  // + item sem cadastro (worklist)
  const csv = [
    'NUMLIC;EMPRESA;PROCLIC;NUMPED;CODIF;NOME;DESTI;NCCUSTO;CADPRO;DISC1;UNID1;TPCONTROLE_SALDO;CONTROLE_SALDO;QTD;PRCTOT;QTDENT;PRCTOTENT;QTDSAID;ESTOQUE;SALDO;SALDOPRCTOT;PROCESSO;QTDANU;PRCTOTANU;NCCUSTO_ORIGEM',
    '2364;1;000007/25;00020/26;9757;FORN;FMS;;041.001.988;Item casavel;UN;T;Valor Total;120;120,00;0;0;0;0;0;0;7;20;20,00;',
    '2364;1;000007/25;01560/26;9757;FORN;FMS;;041.001.988;Item casavel;UN;T;Valor Total;30;30,00;0;0;0;0;0;0;7;0;0;',
    '2364;1;000007/25;00020/26;9757;FORN;FMS;;099.999.999;Item sem cadastro;UN;T;Valor Total;5;5,00;0;0;0;0;0;0;7;0;0;',
  ].join('\r\n');

  await page.click('#nav-atas, .nav-item:has-text("Atas")').catch(() => page.locator('.nav-item:has-text("Atas")').first().click());
  await page.click('button:has-text("Alimentar do Fiorilli")');
  await page.setInputFiles('#fio-file-input', { name: 'fiorilli.csv', mimeType: 'text/csv', buffer: Buffer.from('﻿' + csv, 'utf-8') });

  const cards = page.locator('#fio-cards');
  await expect(cards).toContainText('1'); // 1 item a gravar
  await expect(cards).toContainText('saldo ficará negativo');
  await expect(page.locator('#fio-preview-body')).toContainText('0 → 130'); // pedida líquida 100+30
  await expect(page.locator('#fio-preview-body')).toContainText('099.999.999'); // worklist

  await page.click('#fio-btn-aplicar');
  await expect(page.locator('#fio-step-done')).toBeVisible();

  const utilizada = await page.evaluate(async () => {
    const d = await API.json(await API.get('/api/atas?per=100'));
    const ata = (d.items || d).find(a => a.numero === '099/2025');
    return ata.itens[0].quantidadeUtilizada;
  });
  expect(utilizada).toBe(130);
});

// Anexo baixado tem de passar pelo seletor "Salvar como" do navegador, nao cair
// direto na pasta de downloads (mesmo relato que originou a correcao no SGCD).
// Stuba window.showSaveFilePicker porque o dialogo nativo e do sistema
// operacional e o Playwright nao o enxerga - o que importa provar e que
// baixarAnexo() consulta a API de gravacao em vez de usar um <a download>.
test('baixar anexo abre o seletor de destino em vez de baixar direto', async ({ page }) => {
  await page.goto('/SGCA.html');
  await page.fill('#pin-username', 'admin');
  // Senha ja trocada pelo primeiro teste (servidor/banco compartilhados na suite).
  await page.fill('#pin-input', 'novaSenhaE2E123');
  await page.click('#overlay-pin button[onclick="verificarSenha()"]');
  await expect(page.locator('#overlay-pin')).toBeHidden();

  const arquivoId = await page.evaluate(async () => {
    const r = await API.post('/api/arquivos', {
      nome: 'contrato assinado.pdf',
      mime: 'application/pdf',
      data_b64: btoa('%PDF-1.4 assinado'),
    });
    return (await r.json()).id;
  });
  expect(arquivoId).toBeTruthy();

  const salvo = await page.evaluate(async (id) => {
    const chamado = { picker: false, nome: null, bytes: 0 };
    window.showSaveFilePicker = async (opts) => {
      chamado.picker = true;
      chamado.nome = opts.suggestedName;
      return {
        createWritable: async () => ({
          write: async (blob) => { chamado.bytes = blob.size; },
          close: async () => {},
        }),
      };
    };
    await baixarAnexo(id, 'contrato assinado.pdf');
    return chamado;
  }, arquivoId);

  expect(salvo.picker, 'baixarAnexo nao consultou showSaveFilePicker').toBe(true);
  expect(salvo.nome).toBe('contrato assinado.pdf');
  expect(salvo.bytes).toBeGreaterThan(0);
});

// Ata assinada em 1o de janeiro caia no ANO ANTERIOR: new Date('2026-01-01')
// e lido como UTC e, no nosso fuso, vira 31/12/2025 — e o ano da ata alimenta
// numeracao e exportacao para o PNCP.
// timezoneId fixo: em UTC o defeito e invisivel, entao sem isto o teste
// passaria no CI mesmo com o bug de volta.
test.describe('datas em fuso brasileiro', () => {
  test.use({ timezoneId: 'America/Sao_Paulo' });

  test('ano da ata nao volta na virada do ano', async ({ page }) => {
  await page.goto('/SGCA.html');
  await page.fill('#pin-username', 'admin');
  await page.fill('#pin-input', 'novaSenhaE2E123');
  await page.click('#overlay-pin button[onclick="verificarSenha()"]');
  await expect(page.locator('#overlay-pin')).toBeHidden();

  const r = await page.evaluate(() => ({
    ano: new Date('2026-01-01T00:00:00').getFullYear(),
    fmt: fmtDate('2026-01-01'),
  }));
  // independente de fuso: vale aqui (UTC-3) e no runner do CI (UTC)
  expect(r.ano, 'ano da ata voltou um ano').toBe(2026);
  expect(r.fmt).toBe('01/01/2026');
  });
});

// Duas correções portadas do SGCD, no mesmo lugar (o formulário de subcontratação
// e os campos de data que nascem com "hoje").
test.describe('data local e CNPJ na subcontratacao', () => {
  test.use({ timezoneId: 'America/Sao_Paulo' });

  // toISOString() devolve a data em UTC: depois das 21h, o campo que nasce com
  // "hoje" já vinha com a data de amanhã.
  test('campo de data nasce com o dia local, nao com o de UTC', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-08-01T23:30:00-03:00'));
    await page.goto('/SGCA.html');
    await page.fill('#pin-username', 'admin');
    await page.fill('#pin-input', 'novaSenhaE2E123');
    await page.click('#overlay-pin button[onclick="verificarSenha()"]');
    await expect(page.locator('#overlay-pin')).toBeHidden();

    expect(await page.evaluate(() => _isoLocal()), 'data local saiu em UTC').toBe('2026-08-01');

    await page.evaluate(async () => {
      await renderContratos();
      await openContratoModal(_contratos[0].id);
      showNovaFiscalizacaoForm();
    });
    await expect(page.locator('#fz-data'), 'campo de data nasceu no dia seguinte')
      .toHaveValue('2026-08-01');
  });

  // CNPJ da subcontratação resolve contra o cadastro compartilhado (SGCD/SGEA)
  // em vez de exigir a razão social digitada à mão. Cadastro pré-existente: não
  // depende da Receita Federal estar no ar durante o teste.
  test('CNPJ da subcontratacao puxa do cadastro e recusa numero invalido', async ({ page }) => {
    await page.goto('/SGCA.html');
    await page.fill('#pin-username', 'admin');
    await page.fill('#pin-input', 'novaSenhaE2E123');
    await page.click('#overlay-pin button[onclick="verificarSenha()"]');
    await expect(page.locator('#overlay-pin')).toBeHidden();

    const antes = await page.evaluate(async () => {
      const cnpj = '12.908.073/0001-65';
      await saveFornecedor({ id: '12908073000165', cnpj, cnpj_digits: '12908073000165',
                             razao_social: 'SUBCONTRATADA DE TESTE LTDA' }, null);
      await renderContratos();
      await openContratoModal(_contratos[0].id);
      showNovaSubcontratacaoForm();
      return (await listarFornecedores()).length;
    });

    // 1) CNPJ ja cadastrado: puxa a razao social sem ir a Receita
    await page.fill('#sc-cnpj', '12.908.073/0001-65');
    await page.locator('#sc-percentual').click();          // dispara o onchange
    await expect(page.locator('#sc-razao')).toHaveValue('SUBCONTRATADA DE TESTE LTDA');

    // 2) invalido: nao cadastra nada e nao apaga o que foi digitado
    await page.fill('#sc-razao', '');
    await page.fill('#sc-cnpj', '11.111.111/1111-11');
    await page.locator('#sc-percentual').click();
    await expect(page.locator('#sc-razao')).toHaveValue('');
    await expect(page.locator('#sc-cnpj')).toHaveValue('11.111.111/1111-11');
    expect(await page.evaluate(() => listarFornecedores().then(l => l.length)),
           'CNPJ invalido acabou cadastrado').toBe(antes);
  });
});

// fmtExtenso subiu para o esqueleto: o fecho "local, data" de todo documento da
// familia passa por ele. Este teste garante que o Extrato continua fechando por
// extenso — e que a funcao esta mesmo vindo do base.js, nao de uma copia local.
test.describe('data por extenso no fecho dos documentos', () => {
  test.use({ timezoneId: 'America/Sao_Paulo' });

  test('extrato de contrato fecha por extenso, com a data local', async ({ page, context }) => {
    page.on('dialog', d => d.accept());
    await page.clock.setFixedTime(new Date('2026-08-01T23:30:00-03:00'));
    await page.goto('/SGCA.html');
    await page.fill('#pin-username', 'admin');
    await page.fill('#pin-input', 'novaSenhaE2E123');
    await page.click('#overlay-pin button[onclick="verificarSenha()"]');
    await expect(page.locator('#overlay-pin')).toBeHidden();

    const r = await page.evaluate(() => ({
      hoje: fmtExtenso(),
      comData: fmtExtenso('2026-01-01'),          // virada de ano, string so-data
      doEsqueleto: !document.documentElement.innerHTML.includes('function fmtExtenso'),
    }));
    expect(r.hoje, 'o fecho saiu na data de UTC').toBe('1 de agosto de 2026');
    expect(r.comData, 'string so-data voltou um dia').toBe('1 de janeiro de 2026');
    expect(r.doEsqueleto, 'ainda existe uma copia local de fmtExtenso no HTML').toBe(true);

    await page.evaluate(async () => {
      await renderContratos();
      await openContratoModal(_contratos[0].id);
    });
    const [doc] = await Promise.all([
      context.waitForEvent('page'),
      page.click('button[onclick="gerarExtratoContrato()"]'),
    ]);
    await doc.waitForLoadState();
    await expect(doc.locator('.city-date')).toContainText('1 de agosto de 2026');
    await doc.close();
  });
});
