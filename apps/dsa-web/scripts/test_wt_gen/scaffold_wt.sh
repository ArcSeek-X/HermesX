#!/usr/bin/env bash
#
# scaffold_wt.sh —— 走查脚本脚手架生成器
# =============================================================
# 用法：
#   bash scaffold_wt.sh <route> [page_basename]
#
# 示例：
#   bash scaffold_wt.sh sector-analysis
#   bash scaffold_wt.sh my-module MyModulePage
#
# 作用：
#   基于 gen-wt-skill 下的模板，在 scripts/test_wt/<route>/ 生成一对走查脚本：
#     - test_wt_<route>_backend.py
#     - test_wt_<route>_frontend.sh
#   并将占位符 __ROUTE__ 替换为模块路由名（小写 + 连字符）。
#   生成后由 scripts/test_wt/test_wt.sh 自动发现、编排、跑测。
#
# 注意：生成的脚本是「骨架」，需按本模块真实接口/页面补全 TODO 标注处。

set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WT_ROOT="$(cd "$SKILL_DIR/../test_wt" && pwd)"   # apps/dsa-web/scripts/test_wt

ROUTE="${1:-}"
PAGE_BASENAME="${2:-}"

if [ -z "$ROUTE" ]; then
  echo "用法: bash scaffold_wt.sh <route> [page_basename]"
  echo "示例: bash scaffold_wt.sh sector-analysis"
  exit 1
fi

# 路由名规范化：小写、空格转连字符
ROUTE="$(printf '%s' "$ROUTE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"

DEST_DIR="$WT_ROOT/$ROUTE"
mkdir -p "$DEST_DIR"

BE_TPL="$SKILL_DIR/backend_template.py"
FE_TPL="$SKILL_DIR/frontend_template.sh"
BE_OUT="$DEST_DIR/test_wt_${ROUTE}_backend.py"
FE_OUT="$DEST_DIR/test_wt_${ROUTE}_frontend.sh"

if [ ! -f "$BE_TPL" ] || [ ! -f "$FE_TPL" ]; then
  echo "错误：未找到模板文件（$BE_TPL / $FE_TPL）"
  exit 1
fi

# 替换占位符 __ROUTE__，并按 page_basename 推断页面/API 文件名
PAGE_BASENAME="${PAGE_BASENAME:-${ROUTE^}}"   # 默认首字母大写作为页面名（可覆盖）
# 页面文件名：约定 <Basename>Page.tsx；路由连字符转驼峰
CAMEL="$(printf '%s' "$ROUTE" | awk -F'-' '{for(i=1;i<=NF;i++){s=s toupper(substr($i,1,1)) substr($i,2)} print s}')"
PAGE_FILE="${CAMEL}Page.tsx"
API_FILE="$(printf '%s' "$ROUTE" | tr '-' '_')Data.ts"

sed "s/__ROUTE__/$ROUTE/g" "$BE_TPL" > "$BE_OUT"
sed -e "s/__ROUTE__/$ROUTE/g" \
    -e "s#src/pages/__ROUTE__Page.tsx#src/pages/$PAGE_FILE#g" \
    -e "s#src/api/__ROUTE__Data.ts#src/api/$API_FILE#g" \
    "$FE_TPL" > "$FE_OUT"

chmod +x "$FE_OUT"
echo "已生成："
echo "  $BE_OUT"
echo "  $FE_OUT"
echo ""
echo "下一步："
echo "  1. 编辑 $BE_OUT 的 main() 补全真实接口用例（替换 TODO）"
echo "  2. 编辑 $FE_OUT 的内联 INLINE_TEST 补全 api 契约与组件渲染断言"
echo "  3. 编辑 $FE_OUT 步骤 4 的人工走查清单：基于页面实际代码/交互/边界逐项补充（供报告人工清单章节引用）"
echo "  4. 校验：cd apps/dsa-web/scripts/test_wt && bash test_wt.sh --list"
echo "  5. 运行：bash test_wt.sh $ROUTE [--lint]"
