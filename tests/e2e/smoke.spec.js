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
