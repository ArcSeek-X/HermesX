#!/usr/bin/env bash
#
# =============================================================
# __ROUTE__ 前端走查脚本（模板骨架，由 scaffold_wt.sh 生成）
# =============================================================
# 覆盖：接口契约(vitest mock) + 组件渲染 + 真实页面走查 + ESLint + tsc
# 退出码：0=通过(含良性SKIP) 1=失败 2=环境/依赖未就绪
# 参数：$1="lint" 开启 ESLint
#
# 生成后请补全：
#   - PAGE_FILE / API_FILE 路径（默认按约定推断，如不一致请改）
#   - 内联 INLINE_TEST 中的 api 契约用例（mock apiClient 验证请求拼装与解析）
#   - 组件渲染断言（render(<Page/>) 关键结构）
#   - 人工走查清单（按本模块实际交互/边界补充）
# ---------------------------------------------------------

cd "$(dirname "$0")/../../.." || { echo "无法切换到 apps/hrs-web 根目录"; exit 1; }
APP_ROOT="$(pwd)"

# 步骤 -1：加载 Node 环境
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$HOME/.nvm/nvm.sh" >/dev/null 2>&1
  nvm use default >/dev/null 2>&1 || true
fi

green()  { printf '\033[32m%s\033[0m\n' "$1"; }
red()    { printf '\033[31m%s\033[0m\n' "$1"; }
cyan()   { printf '\033[36m%s\033[0m\n' "$1"; }
check_cmd() { command -v "$1" >/dev/null 2>&1 && return 0 || return 1; }

RUN_LINT=0
[ "${1:-}" = "lint" ] && RUN_LINT=1

RESULT=0
ENV_ISSUE=0
mark_fail() { RESULT=1; red "✗ $1"; }
mark_pass() { green "✓ $1"; }
mark_skip() { printf '\033[33m%s\033[0m\n' "△ $1"; }
mark_unavailable() { ENV_ISSUE=1; printf '\033[33m%s\033[0m\n' "⚠ $1（环境/依赖缺失，检查未执行）"; }

ROUTE="__ROUTE__"
FE_ROOT="$APP_ROOT"
WT_DIR="$FE_ROOT/scripts/test_wt/$ROUTE"
INLINE_TEST="$WT_DIR/__${ROUTE}_walkthrough.test.tsx"

# 步骤 0：环境预检（按实际路径调整 PAGE_FILE / API_FILE）
cyan "===== [前端走查] 步骤 0：环境预检 ====="
PAGE_FILE="$FE_ROOT/src/pages/__ROUTE__Page.tsx"   # TODO: 改为真实页面文件名
API_FILE="$FE_ROOT/src/api/__ROUTE__Data.ts"        # TODO: 改为真实 api 文件名
[ -f "$PAGE_FILE" ] && mark_pass "找到页面：$PAGE_FILE" || mark_fail "未找到页面：$PAGE_FILE"
[ -f "$API_FILE" ]  && mark_pass "找到 API 层：$API_FILE" || mark_fail "未找到 API 层：$API_FILE"

# 步骤 1：内联 vitest 测试（接口契约 + 组件渲染）
cyan "===== [前端走查] 步骤 1：接口契约 + 组件渲染测试 ====="
cat > "$INLINE_TEST" <<'VITEST'
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

// 1) 接口契约：mock apiClient，验证前端请求拼装与返回解析
const getMock = vi.fn();
vi.mock('../src/api/index', () => ({
  default: { get: (...args: any[]) => getMock(...args) },
}));

// TODO: 改为本模块真实 api 函数与调用
import { fetchList } from '../src/api/__ROUTE__Data';

describe('__ROUTE__ API 契约', () => {
  beforeEach(() => { getMock.mockReset(); });
  it('fetchList 正确拼装请求并解析返回', async () => {
    getMock.mockResolvedValue({ data: { items: [], total: 0 } });
    const r = await fetchList();
    // TODO: 替换为真实路径与参数断言
    expect(getMock).toHaveBeenCalledWith('/api/v1/__ROUTE__/list', { params: {} });
    expect(Array.isArray(r.items)).toBe(true);
  });
});

// 2) 组件渲染
vi.mock('../src/api/__ROUTE__Data', async () => {
  const actual = await vi.importActual('../src/api/__ROUTE__Data');
  return {
    ...(actual as any),
    fetchList: vi.fn().mockResolvedValue({ items: [{ id: 1, name: '示例' }], total: 1 }),
  };
});
// TODO: 改为真实页面组件路径
import Page from '../src/pages/__ROUTE__Page';
describe('__ROUTE__ 页面渲染', () => {
  it('页面可挂载并渲染关键结构', async () => {
    render(React.createElement(Page));
    await waitFor(() => { expect(screen.getByText(/示例|列表|__ROUTE__/)).toBeTruthy(); });
  });
});
VITEST

if check_cmd npm; then
  npm run test -- --run "$INLINE_TEST" \
    && mark_pass "接口契约 + 组件渲染测试通过" \
    || mark_fail "接口契约 + 组件渲染测试失败"
else
  mark_unavailable "npm 不可用，无法执行接口契约 + 组件渲染测试"
fi

# 步骤 2：真实页面走查（端口文件缺失则跳过，非阻断）
cyan "===== [前端走查] 步骤 2：真实页面走查 ====="
PORT_FILE="$FE_ROOT/.${ROUTE}-walkthrough-port"
if [ -f "$PORT_FILE" ]; then
  RPORT=$(cat "$PORT_FILE"); mark_pass "读到监听端口：$RPORT"
  if command -v curl >/dev/null 2>&1; then
    curl -s "http://localhost:${RPORT}/${ROUTE}" -o /tmp/${ROUTE}_page.html \
      && grep -q "$ROUTE" /tmp/${ROUTE}_page.html \
      && mark_pass "页面渲染正常（HTTP 可访问）" \
      || mark_skip "页面走查失败或未部署（非阻断）"
  else
    mark_skip "curl 不可用，跳过页面 HTTP 走查（非阻断）"
  fi
else
  mark_skip "未检测到端口文件 $PORT_FILE，跳过页面走查（非阻断）"
fi

# 步骤 3：ESLint + tsc
cyan "===== [前端走查] 步骤 3：ESLint + TypeScript 类型检查 ====="
if check_cmd npm; then
  if [ "${RUN_LINT}" -eq 1 ]; then
    npm run lint && mark_pass "ESLint 通过" || mark_fail "ESLint 存在错误"
  else
    mark_skip "ESLint 未开启（需 --lint），跳过"
  fi
  npx tsc --noEmit && mark_pass "TypeScript 类型检查通过" || mark_fail "TypeScript 类型检查错误"
else
  mark_unavailable "npm 不可用，无法执行 ESLint / tsc"
fi

# 步骤 4：人工走查清单（内联，供 test_wt.sh 报告"五、人工 UI 走查清单"读取）
# 注意：本段内容必须基于 __ROUTE__ 对应页面真实代码 / 注释 / 交互 / 边界手写，不得套用通用模板。
# test_wt.sh 生成报告时会提取 BEGIN/END 标记区间填入报告章节。
cyan "===== [前端走查] 步骤 4：人工走查清单（需人工确认，不阻断） ====="
gen_manual_checklist() {
cat <<'CHECKLIST'
### 人工UI走查清单 __ROUTE__
<!--BEGIN_MANUAL_CHECKLIST-->
#### 5.1 接口·调用
- [ ] 页面加载时是否正确发起对应接口请求并解析出数据
- [ ] 请求是否正确携带关键参数（按真实接口补全：time / period / limit / page / sector_type 等）
- [ ] 后端返回字段与前端读取一致

#### 5.2 结构
- [ ] 核心可视化容器按预期渲染（默认尺寸与自定义尺寸生效）
- [ ] 关键区块 / 图表出现（TODO：列出本模块特有区块，如 treemap / 列表 / 指数卡片 / 图表）
- [ ] 图例、坐标轴、刻度清晰可读；鼠标悬停显示 tooltip

#### 5.3 样式
- [ ] 亮色主题：背景、文字、涨跌色符合预期
- [ ] 暗色主题（html.dark）：文字、坐标轴、分割线适配
- [ ] 小屏自适应、无溢出

#### 5.4 功能
- [ ] 各 tab / 周期 / 类型切换正常（TODO：列出本模块实际切换项）
- [ ] 时间快照 / 筛选器切换时数据正确刷新
- [ ] 边界交互（拖拽 / 缩放 / resize）自适应、不白屏
- [ ] 切换时不重复创建实例 / 内存泄漏

#### 5.5 边界
- [ ] 空数据：容器渲染、无崩溃、无报错
- [ ] 超大数据量：不卡死、无报错
- [ ] 字段为 null：不崩溃
- [ ] 组件卸载：定时器 / 轮询 / 事件监听正确清理
<!--END_MANUAL_CHECKLIST-->
CHECKLIST
}
gen_manual_checklist
echo "(人工清单仅展示，不计入自动判定；报告生成时由 test_wt.sh 提取标记区间)"

# 收尾
cyan "===== [前端走查] 结论 ====="
rm -f "$INLINE_TEST"
if [ "$RESULT" -ne 0 ]; then
  red "前端走查存在失败项，请查看上方失败明细"; exit 1
elif [ "$ENV_ISSUE" -ne 0 ]; then
  printf '\033[33m%s\033[0m\n' "前端走查环境/依赖未就绪（部分未执行），需关注但不视为失败"; exit 2
else
  green "前端走查自动化检查完成（含良性 SKIP 视为非阻断）"; exit 0
fi
