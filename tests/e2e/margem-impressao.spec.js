import { test, expect } from '@playwright/test';

// Os modelos de documento usam padding no body para a janela de prévia não ficar
// com o texto colado na borda. Esse recuo SOMAVA com a margem do @page no papel
// (20mm + 20~25mm), e em documento de várias páginas só valia na primeira e na
// última. O @media print do esqueleto zera o padding na impressão — este teste
// trava as duas pontas: prévia confortável, papel governado só pelo @page.
test('margem do documento vem só do @page (padding zera na impressão)', async ({ page, context }) => {
  await page.goto('/SGCA.html');
  const css = await page.evaluate(() => _DOC_CSS);
  expect(css).toContain('@page');

  const doc = await context.newPage();
  await doc.setContent(`<style>${css}</style><body><p>conteúdo</p></body>`);

  await doc.emulateMedia({ media: 'screen' });
  const naTela = await doc.evaluate(() => getComputedStyle(document.body).padding);

  await doc.emulateMedia({ media: 'print' });
  const noPapel = await doc.evaluate(() => getComputedStyle(document.body).padding);

  console.log('padding na tela :', naTela);
  console.log('padding no papel:', noPapel);
  expect(naTela).not.toBe('0px');          // prévia continua confortável
  expect(noPapel).toBe('0px');             // no papel, só a margem do @page
});
