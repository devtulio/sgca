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
