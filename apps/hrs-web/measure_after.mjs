import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

const result = await page.evaluate(() => {
  const data = [];
  const inputs = document.querySelectorAll('input');
  inputs.forEach((input, i) => {
    const r = input.getBoundingClientRect();
    const cs = getComputedStyle(input);
    const group = input.closest('[data-slot="input-group"], .input-group, .input-group-root');
    const groupR = group ? group.getBoundingClientRect() : null;
    data.push({
      idx: i,
      type: input.type,
      placeholder: input.placeholder,
      height: r.height,
      fontSize: cs.fontSize,
      lineHeight: cs.lineHeight,
      paddingTop: cs.paddingTop,
      paddingBottom: cs.paddingBottom,
      groupHeight: groupR ? groupR.height : null,
      cls: input.className.slice(0, 200),
    });
  });
  return data;
});

console.log(JSON.stringify(result, null, 2));
await browser.close();
