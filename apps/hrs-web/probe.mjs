import { chromium } from 'playwright-core';
import { writeFileSync } from 'node:fs';
const browser = await chromium.launch({ channel: 'chrome' });
const out = [];
const cases = [
  { h: 900,  alerts: 0, tag: '普通窗口 900' },
  { h: 1080, alerts: 0, tag: '全屏 1080' },
  { h: 720,  alerts: 0, tag: '小窗 720' },
  { h: 900,  alerts: 6, tag: '900 + 6条提示(内容超高)' },
];
for (const c of cases) {
  const page = await browser.newPage({ viewport: { width: 1440, height: c.h }, deviceScaleFactor: 1 });
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  await page.goto(`http://127.0.0.1:5189/probe-portfolio.html?alerts=${c.alerts}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1600);
  const r = await page.evaluate(() => {
    const hh = (s) => { const el = document.querySelector(s); return el ? Math.round(el.getBoundingClientRect().height) : null; };
    const table = document.querySelector('.hrs-table');
    const panel = document.querySelector('#panel');
    const section = document.querySelector('#section');
    const main = document.querySelector('#main');
    const pageRoot = main.firstElementChild;
    const leftCard = document.querySelector('#left-box > *');
    const leftInner = leftCard?.firstElementChild;
    return {
      main: hh('#main'),
      pageRoot: pageRoot ? Math.round(pageRoot.getBoundingClientRect().height) : null,
      section: section ? Math.round(section.getBoundingClientRect().height) : null,
      panel: panel ? Math.round(panel.getBoundingClientRect().height) : null,
      table: table ? Math.round(table.getBoundingClientRect().height) : null,
      bottomGap: panel && table ? Math.round(panel.getBoundingClientRect().bottom - table.getBoundingClientRect().bottom) : null,
      tableInlineH: table ? table.style.height : null,
      tableClass: table ? table.className : null,
      leftCardH: leftCard ? Math.round(leftCard.getBoundingClientRect().height) : null,
      // 左栏文本内容是否可见（未被 overflow-hidden 裁剪）
      leftTextVisible: leftInner ? leftInner.getBoundingClientRect().height > 0 : null,
      mainScrollH: main.scrollHeight, mainClientH: main.clientHeight,
      tableInnerScroll: (() => { const el = document.querySelector('.hrs-table__root'); return el ? el.scrollHeight > el.clientHeight : null; })(),
    };
  });
  const scrolled = await page.evaluate(() => { const m = document.querySelector('#main'); m.scrollTop = 300; return m.scrollTop; });
  out.push(`【${c.tag}】`);
  out.push(`  main=${r.main} pageRoot=${r.pageRoot} section=${r.section} panel=${r.panel} table=${r.table} 表格-面板底部空隙=${r.bottomGap}`);
  out.push(`  表格内联height="${r.tableInlineH}" class="${r.tableClass}"`);
  out.push(`  左栏AnimCard=${r.leftCardH} 文本可见=${r.leftTextVisible} ｜ Main可滚=${r.mainScrollH > r.mainClientH}(${r.mainScrollH}/${r.mainClientH}) 实滚=${scrolled} ｜ 表内滚动=${r.tableInnerScroll}`);
  if (errs.length) out.push('  页面错误: ' + errs.slice(0, 2).join(' | '));
  await page.close();
}
writeFileSync('/tmp/pf.txt', out.join('\n'));
await browser.close();
