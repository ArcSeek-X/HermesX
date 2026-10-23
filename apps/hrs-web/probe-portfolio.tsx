/**
 * 临时验证页：用「真实 Table + 真实 AnimCard」复现持仓页高度链，
 * 验证表格贴底填充、随窗口变高，且内容超高时 Main 仍可滚动、非填充面板不被压缩裁剪。
 * 验证完成后可整体删除。
 */
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import './src/style/index.css';
import AnimCard from './src/components/common/Card/AnimCard';
import { Table } from './src/components/basic/Table';

interface Row { id: string; account: string; symbol: string; qty: string; cost: string; price: string; mv: string }

const columns = [
  { key: 'account', title: '账户', minWidth: 100, defaultWidth: '10%', isRowHeader: true, cellClassName: 'text-xs' },
  { key: 'symbol', title: '代码', minWidth: 80, defaultWidth: '8%', cellClassName: 'text-xs' },
  { key: 'qty', title: '数量', minWidth: 80, defaultWidth: '8%', cellClassName: 'text-xs text-right' },
  { key: 'cost', title: '成本价', minWidth: 80, defaultWidth: '8%', cellClassName: 'text-xs text-right' },
  { key: 'price', title: '现价', minWidth: 150, defaultWidth: '13%', cellClassName: 'text-xs text-right' },
  { key: 'mv', title: '市值', minWidth: 110, defaultWidth: '11%', cellClassName: 'text-xs text-right' },
];

const rows: Row[] = Array.from({ length: 3 }, (_, i) => ({
  id: String(i),
  account: '主账户',
  symbol: `60058${i}`,
  qty: '1000.00',
  cost: '22.5000',
  price: '23.18',
  mv: '23,180.00',
}));

const params = new URLSearchParams(location.search);
const tallAlerts = Number(params.get('alerts') || 0);

const app = document.getElementById('app')!;
app.style.cssText = 'height:100vh;display:flex;flex-direction:column;';

const col = document.createElement('div');
col.style.cssText = 'display:flex;flex-direction:column;flex:1;min-height:0;';
const header = document.createElement('div');
header.style.cssText = 'height:56px;flex:none;border-bottom:1px solid #262a31;';
// Main：flex-1 min-h-0 overflow-y-auto，内边距与真实 Main 一致（pt-4 pb-3 sm:px-4）
const main = document.createElement('div');
main.id = 'main';
main.style.cssText = 'flex:1;min-height:0;overflow-y:auto;padding:16px 16px 12px;';
col.append(header, main);
app.append(col);

// ===== PortfolioPage 根：flex min-h-full flex-col gap-4 p-4 =====
const pageRoot = document.createElement('div');
pageRoot.className = 'flex min-h-full flex-col gap-4 p-4';
main.append(pageRoot);

// PageHeader（近似 84px）
const pageHeader = document.createElement('div');
pageHeader.style.cssText = 'height:84px;flex:none;background:#14171c;border-radius:8px;display:flex;align-items:center;padding:0 12px;';
pageHeader.textContent = 'PageHeader';
pageRoot.append(pageHeader);

// 多个 InlineAlert（压测：alerts>0 时灌入，验证内容超高仍可滚动）
for (let i = 0; i < tallAlerts; i++) {
  const a = document.createElement('div');
  a.style.cssText = 'height:44px;flex:none;background:#3a2f14;border-radius:8px;display:flex;align-items:center;padding:0 12px;font-size:12px;';
  a.textContent = `InlineAlert #${i + 1}`;
  pageRoot.append(a);
}

// ===== grid：items-stretch flex-1 min-h-0 =====
const grid = document.createElement('div');
grid.className = 'grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)] gap-4 items-stretch flex-1 min-h-0';
pageRoot.append(grid);

// 左栏（AnimCard h-full，与 PortfolioAccountViewPanel 一致）
const leftBox = document.createElement('div');
leftBox.id = 'left-box';
grid.append(leftBox);
createRoot(leftBox).render(
  <AnimCard className="flex-col p-4 h-full">左栏账户面板（AnimCard h-full）</AnimCard>,
);

// ===== 右栏 section：flex h-full min-h-0 flex-col =====
const section = document.createElement('div');
section.className = 'flex h-full min-h-0 flex-col space-y-3';
section.id = 'section';
grid.append(section);

// TabNav（近似 42px，shrink-0）
const tabnav = document.createElement('div');
tabnav.style.cssText = 'height:42px;flex:none;background:#14171c;border-radius:8px;display:flex;align-items:center;padding:0 12px;';
tabnav.textContent = 'TabNav（shrink-0）';
section.append(tabnav);

// ===== 持仓表格面板：flex flex-1 min-h-0 flex-col → AnimCard flex-1 min-h-0 flex-col → Table fillHeight =====
const panel = document.createElement('div');
panel.className = 'flex flex-1 min-h-0 flex-col gap-3';
panel.id = 'panel';
section.append(panel);
const cardRoot = createRoot(panel);
cardRoot.render(
  <MemoryRouter>
    <AnimCard className="flex-1 min-h-0 flex-col p-4 min-h-[320px]">
      <div className="flex items-center justify-between mb-3" style={{ flex: 'none' }}>
        <h2 style={{ fontSize: 14, fontWeight: 600 }}>持仓明细</h2>
      </div>
      <Table columns={columns} rows={rows} fillHeight className="text-xs" />
    </AnimCard>
  </MemoryRouter>,
);
