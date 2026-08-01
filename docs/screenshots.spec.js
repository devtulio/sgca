// Capturas do README. Não é teste: monta um cenário de demonstração e fotografa.
// Roda fora do CI, por configuração própria:
//
//     npx playwright test -c docs/screenshots.config.js
//
// Todo dado aqui é fictício, por decisão: as imagens vão para um repositório
// público e nada que saia daqui pode ser de um contrato, fornecedor ou servidor
// real. O órgão é "Município de Exemplo/SP"; não há brasão (upload em
// Configurações, nunca embutido).
import { test, expect } from '@playwright/test';

const SHOTS = 'docs/screenshots';

const ORG = {
  orgao: 'Prefeitura Municipal de Exemplo',
  municipio: 'Município de Exemplo',
  uf: 'SP',
  aut_nome: 'Maria Aparecida Silva',
  aut_cargo: 'Prefeita Municipal',
  nome: 'Ana Beatriz Moraes',
  cargo: 'Gestora de Contratos',
  matricula: '2087',
};

const hoje = new Date();
const emDias = n => {
  const d = new Date(hoje);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const CONTRATOS = [
  { numero: '041/2026', objeto: 'Prestação de serviços de limpeza e conservação predial', valorGlobal: 148000, status: 'vigente',
    vigenciaInicial: emDias(-210), vigenciaFinal: emDias(155), fiscalNome: 'Carlos Eduardo Nunes' },
  { numero: '038/2026', objeto: 'Manutenção preventiva e corretiva da frota municipal', valorGlobal: 96500, status: 'vigente',
    vigenciaInicial: emDias(-180), vigenciaFinal: emDias(25), fiscalNome: 'Patrícia Lima Souza' },
  { numero: '032/2026', objeto: 'Fornecimento de combustível para os veículos oficiais', valorGlobal: 212000, status: 'em_prorrogacao',
    vigenciaInicial: emDias(-330), vigenciaFinal: emDias(12), fiscalNome: 'Rodrigo Alves Teixeira' },
  { numero: '027/2026', objeto: 'Locação de impressoras com franquia mensal de cópias', valorGlobal: 43800, status: 'vigente',
    vigenciaInicial: emDias(-150), vigenciaFinal: emDias(210), fiscalNome: 'Ana Beatriz Moraes' },
  { numero: '019/2025', objeto: 'Serviço de coleta de resíduos sólidos domiciliares', valorGlobal: 305000, status: 'encerrado',
    vigenciaInicial: emDias(-700), vigenciaFinal: emDias(-40), fiscalNome: 'Carlos Eduardo Nunes' },
];

const ATA = {
  numero: '012/2026',
  processoOrigem: '2026/0087',
  orgaoGerenciador: 'Prefeitura Municipal de Exemplo',
  dataAssinatura: emDias(-120),
  vigenciaFinal: emDias(245),
  status: 'vigente',
  itens: [
    { descricao: 'Papel sulfite A4 75g — resma 500 folhas', unidade: 'RESMA', quantidadeRegistrada: 1200, quantidadeUtilizada: 980, precoUnitario: 24.9 },
    { descricao: 'Caneta esferográfica azul — caixa com 50', unidade: 'CX', quantidadeRegistrada: 300, quantidadeUtilizada: 115, precoUnitario: 42.5 },
    { descricao: 'Cartucho de toner preto compatível', unidade: 'UN', quantidadeRegistrada: 180, quantidadeUtilizada: 60, precoUnitario: 118.0 },
    { descricao: 'Pasta suspensa kraft com grampo', unidade: 'UN', quantidadeRegistrada: 900, quantidadeUtilizada: 240, precoUnitario: 3.75 },
  ],
};

test('capturas do README', async ({ page }) => {
  page.on('dialog', d => d.accept());

  await page.goto('/SGCA.html');
  await page.fill('#pin-username', 'admin');
  await page.fill('#pin-input', 'admin123');
  await page.click('#overlay-pin button[onclick="verificarSenha()"]');
  await expect(page.locator('#overlay-force-pwd')).toBeVisible();
  await page.fill('#fp-nova', 'demoSGCA2026');
  await page.fill('#fp-confirma', 'demoSGCA2026');
  await page.click('#overlay-force-pwd button');
  await expect(page.locator('#overlay-pin')).toBeHidden();

  // O nome do usuário logado aparece na barra lateral: também fictício.
  await page.evaluate(async org => {
    const lista = await API.json(await API.get('/api/usuarios'));
    const eu = lista.find(u => u.username === 'admin');
    await API.put(`/api/usuarios/${eu.id}`, { nome: org.nome, cargo: org.cargo, matricula: org.matricula });
  }, ORG);

  await page.evaluate(org => {
    localStorage.setItem('sgca-user', JSON.stringify(org));
  }, ORG);

  await page.evaluate(async ({ contratos, ata }) => {
    for (const c of contratos) await API.post('/api/contratos', c);
    await API.post('/api/atas', ata);
  }, { contratos: CONTRATOS, ata: ATA });

  await page.reload();
  await expect(page.locator('#overlay-pin')).toBeHidden();

  // ── 1. Contratos em Kanban ────────────────────────────────────────────────
  await page.click('#nav-contratos');
  await expect(page.locator('.kanban-card').first()).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${SHOTS}/contratos.png` });

  // ── 2. Ata com saldo por item ─────────────────────────────────────────────
  // O controle de saldo (utilizado vs. registrado, com alerta de esgotamento) é
  // o que distingue a tela de Atas de uma lista qualquer.
  await page.click('#nav-atas');
  const cardAta = page.locator('.kanban-card, .ata-card, tr', { hasText: '012/2026' }).first();
  await expect(cardAta).toBeVisible();
  await cardAta.click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${SHOTS}/ata-saldo.png` });
  await page.keyboard.press('Escape');

  // ── 3. Agenda de vencimentos ──────────────────────────────────────────────
  await page.click('#nav-agenda');
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${SHOTS}/agenda.png` });
});
