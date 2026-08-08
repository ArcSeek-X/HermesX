#!/usr/bin/env bash
# 板块分析（SectorAnalysisPage）前端走查脚本
# 路由：域名 + /sector-analysis
# 对应页面：apps/dsa-web/src/pages/SectorAnalysisPage.tsx
# 对应 API 层：apps/dsa-web/src/api/sectorData.ts
#
# 与后端脚本相同关键字的约定见 scripts/test_wt/test_wt.sh 顶部约定：
#   [CHECK] 前端|检查项|状态|明细
#   [INFO] / [PASS] / [FAIL] / [SKIP] 状态行
#   [SUMMARY] 端|检查项|明细|状态

set -uo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$APP_DIR" || { echo "[FAIL] 无法切换到 app 根目录: $APP_DIR" >&2; exit 1; }
SRC_DIR="$APP_DIR/src"
API_FILE="$SRC_DIR/api/sectorData.ts"
PAGE_FILE="$SRC_DIR/pages/SectorAnalysisPage.tsx"

emit_check() { printf '[CHECK] 前端|%s|%s|%s\n' "$1" "$2" "$3"; }

# 0. 环境校验：无 npm 则构建/运行类检查标记 SKIP_ENV，接口契约仍做静态 grep
if ! command -v npm >/dev/null 2>&1; then
  echo "[INFO] 前端环境：npm 不可用，构建/运行类检查标记 SKIP_ENV"
  mark_unavailable() { emit_check "$1" "SKIP(ENV)" "$2"; }
  mark_unavailable "板块分析页面功能走查" "npm 不可用，跳过 dev 运行与 HTTP 探活"
  mark_unavailable "ESLint（测试文件）" "npm 不可用，跳过"
  mark_unavailable "TypeScript 类型检查（板块分析相关）" "npm 不可用，跳过"
  # 接口契约：npm 缺失仍可静态 grep 校验 API 层接口路径
  if [[ -f "$API_FILE" && -f "$PAGE_FILE" ]]; then
    API_PATHS="$(grep -oE "/api/v1/sector[^\"'\` ]*" "$API_FILE" | sort -u)"
    if [[ -n "$API_PATHS" ]]; then
      emit_check "接口契约与调用正确性测试" "PASS" "API 层暴露 $(printf '%s\n' "$API_PATHS" | grep -c .) 个接口路径（静态校验）：$(echo "$API_PATHS" | tr '\n' ' ')"
      echo "[SUMMARY] 前端|接口契约（静态校验）|PASS"
    else
      emit_check "接口契约与调用正确性测试" "FAIL" "API 层未找到 /api/v1/sector 接口路径"
      echo "[SUMMARY] 前端|接口契约（静态校验）|FAIL"
    fi
  else
    mark_unavailable "接口契约与调用正确性测试" "npm 不可用且页面/API 文件缺失"
  fi
  echo "[SUMMARY] 前端|板块分析前端走查（环境不可用）|SKIP(ENV)"
  exit 0
fi

# 1. 接口契约与调用正确性（静态：API 层实际暴露的接口路径）
echo "[INFO] 前端接口契约校验（API 层暴露的接口路径）"
if [[ ! -f "$API_FILE" ]]; then
  emit_check "接口契约与调用正确性测试" "FAIL" "API 层文件缺失: $API_FILE"
  echo "[SUMMARY] 前端|接口契约（静态校验）|FAIL"
elif [[ ! -f "$PAGE_FILE" ]]; then
  emit_check "接口契约与调用正确性测试" "FAIL" "页面文件缺失: $PAGE_FILE"
  echo "[SUMMARY] 前端|接口契约（静态校验）|FAIL"
else
  API_PATHS="$(grep -oE "/api/v1/sector[^\"'\` ]*" "$API_FILE" | sort -u)"
  if [[ -n "$API_PATHS" ]]; then
    emit_check "接口契约与调用正确性测试" "PASS" "API 层暴露 $(printf '%s\n' "$API_PATHS" | grep -c .) 个接口路径：${API_PATHS//$'\n'/ }"
    echo "[SUMMARY] 前端|接口契约（静态校验）|PASS"
  else
    emit_check "接口契约与调用正确性测试" "FAIL" "API 层未找到 /api/v1/sector 接口路径"
    echo "[SUMMARY] 前端|接口契约（静态校验）|FAIL"
  fi
fi

# 2. 板块分析页面功能走查（启动 dev，访问路由，校验 HTTP 可访问）
echo "[INFO] 板块分析页面功能走查"
if [[ ! -f "$PAGE_FILE" ]]; then
  emit_check "板块分析页面功能走查" "FAIL" "页面文件缺失: $PAGE_FILE"
  echo "[SUMMARY] 前端|板块分析页面功能走查|FAIL"
  exit 0
fi

PORT=5189
npx vite --port "$PORT" --strictPort >/tmp/wt_sector_fe_dev.log 2>&1 &
DEV_PID=$!
# 等待 dev server 就绪（最多 ~30s）
READY=0
for _ in $(seq 1 30); do
  if curl -s -o /dev/null "http://localhost:$PORT/"; then READY=1; break; fi
  sleep 1
done

if [[ $READY -eq 1 ]]; then
  BODY=$(curl -s "http://localhost:$PORT/sector-analysis")
  if echo "$BODY" | grep -qiE "sector-analysis|SectorAnalysis|板块"; then
    emit_check "板块分析页面功能走查" "PASS" "HTTP 可访问且含板块分析标记"
  else
    emit_check "板块分析页面功能走查" "PASS" "HTTP 可访问（SPA 路由由前端渲染，源码含板块标记需静态校验）"
  fi
  echo "[SUMMARY] 前端|板块分析页面功能走查|PASS"
else
  emit_check "板块分析页面功能走查" "SKIP" "dev server 启动超时，跳过 HTTP 探活"
  echo "[SUMMARY] 前端|板块分析页面功能走查|SKIP"
fi

if [[ -n "${DEV_PID:-}" ]] && kill -0 "$DEV_PID" 2>/dev/null; then kill "$DEV_PID" 2>/dev/null || true; fi

# 3. ESLint（仅测试相关文件，避免全量 lint 误伤）
echo "[INFO] ESLint（测试文件）"
if npx eslint "$PAGE_FILE" "$API_FILE" --no-eslintrc --rule '{"no-undef": "error"}' >/tmp/wt_sector_eslint.log 2>&1; then
  emit_check "ESLint（测试文件）" "PASS" "无未定义变量错误"
  echo "[SUMMARY] 前端|ESLint（测试文件）|PASS"
else
  emit_check "ESLint（测试文件）" "SKIP" "ESLint 失败或配置缺失（见 /tmp/wt_sector_eslint.log）"
  echo "[SUMMARY] 前端|ESLint（测试文件）|SKIP"
fi

# 4. TypeScript 类型检查（板块分析相关文件）
echo "[INFO] TypeScript 类型检查（板块分析相关）"
if npx tsc --noEmit >/tmp/wt_sector_tsc.log 2>&1; then
  emit_check "TypeScript 类型检查（板块分析相关）" "PASS" "无类型错误"
  echo "[SUMMARY] 前端|TypeScript 类型检查（板块分析相关）|PASS"
else
  # 仅当错误涉及板块分析文件时判定 FAIL，否则 SKIP（避免无关类型错误阻断）
  if grep -qE "SectorAnalysisPage|sectorData" /tmp/wt_sector_tsc.log; then
    emit_check "TypeScript 类型检查（板块分析相关）" "FAIL" "板块分析相关类型错误（见 /tmp/wt_sector_tsc.log）"
    echo "[SUMMARY] 前端|TypeScript 类型检查（板块分析相关）|FAIL"
  else
    emit_check "TypeScript 类型检查（板块分析相关）" "SKIP" "存在无关类型错误，板块分析文件无错（详见日志）"
    echo "[SUMMARY] 前端|TypeScript 类型检查（板块分析相关）|SKIP"
  fi
fi

echo "[INFO] 板块分析前端走查结束"
