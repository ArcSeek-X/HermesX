#!/usr/bin/env bash
#
# =============================================================
# 全功能模块前后端走查统一入口（test_wt 主调度脚本）
# =============================================================
#
# 功能概括：
#   遍历本目录（test_wt/）下所有「以功能菜单路由名称命名」的子目录（如
#   kline、AAA 等），逐个功能模块执行其内部的测试脚本：
#     - 后端测试：子目录内的 *.py 文件（如 test_wt_xxx_backend.py）
#     - 前端测试：子目录内的 *.sh 文件（如 test_wt_xxx_frontend.sh）
#   每个模块的前后端测试执行完毕后，统一汇总生成走查报告，按时间戳归档到
#   .test_record/ 下的子目录（位于 apps/hrs-web 根下），目录内包含：
#     test_wt_report_<TS>/test_wt_report_<TS>.md        # 总体报告（覆盖全部模块）
#     test_wt_report_<TS>/test_wt_<Mod>_report_<TS>.md  # 各功能模块独立报告（Mod 即模块目录名，如 kline）
#
# 设计原则（解耦、可扩展）：
#   - 本脚本只负责「遍历 + 调度 + 汇总 + 生成报告」，不内嵌任何具体功能
#     的测试逻辑；各功能模块的具体测试实现都放在其同名子目录内。
#   - 新增一个功能模块的走查，只需在 test_wt/ 下新建同名子目录并放入
#     后端 .py 与前端 .sh 即可，无需改动本入口脚本。
#   - 每个子脚本自行决定退出码；本脚本遵循约定：
#       0 = 通过（SKIP 视为非阻断），1 = 失败，2 = 用法/环境错误。
#   - 任一模块 FAIL 都会向上冒泡，最终退出码反映整体结论。
#
# 子脚本输出约定（供本脚本解析汇总）：
#   - 后端 .py 在结尾打印一行：[RESULT] PASS|FAIL|SKIP（取最后一条）
#   - 后端 .py 可另打印：[SUMMARY] PASS=x FAIL=y SKIP=z（统计汇总）
#   - 前端 .sh 通过退出码表达结论：0=通过/SKIP，1=失败
#
# 用法：
#   cd apps/hrs-web/scripts/test_wt
#   ./test_wt.sh                 # 遍历全部功能模块
#   ./test_wt.sh kline           # 仅执行指定功能模块（如 kline）
#   ./test_wt.sh --list          # 仅列出将要执行的功能模块，不实际执行
#   ./test_wt.sh --lint          # 开启前端 ESLint 检查（默认关闭；开启后透传给各前端 .sh）
#   ./test_wt.sh --lint kline    # 仅对 kline 模块开启 ESLint 检查
#
# 报告产物：
#   本次走查的报告统一落在 apps/hrs-web/.test_record/test_wt_report_<TS>/ 目录下：
#     - test_wt_report_<TS>.md        # 总体报告（模板见 sum_template.md：基本信息/环境/一汇总/二各模块/三结论）
#     - test_wt_<Mod>_report_<TS>.md  # 各功能模块独立报告（模板见 class_template.md：基本信息/环境/一范围/二介绍/三汇总/四明细/五人工/六问题/七结论）
#
# 说明：
#   --lint 仅控制「前端 ESLint 代码规范检查」是否执行（默认关闭以提升走查速度）；
#   其余前端检查（单测、契约、tsc 类型检查、页面走查）不受影响。
#
# 退出码：
#   0 = 全部模块通过（任一端 SKIP 视为非阻断）
#   1 = 存在模块失败
#   2 = 用法错误 / 无可执行模块

# 严格模式：
#   -u  引用未定义变量即报错，避免拼写错误的变量被静默当作空串；
#   -o pipefail  管道中任意阶段非零退出时，整条管道返回最右非零码，
#                防止「后端 py 失败但 tee 成功」导致失败被掩盖。
# 注意：此处**未**开启 -e，因为本脚本需在子命令失败时继续走查其余模块，
#       并以最终汇总结果统一决定退出码，不宜中途因单点失败而中止。
set -uo pipefail

# 定位本入口所在目录（.../scripts/test_wt）
# 用 BASH_SOURCE 而非 $0，保证脚本被 source 或经符号链接调用时路径依然准确。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 测试资源根目录（test_wt 本身）
WT_ROOT="${SCRIPT_DIR}"

# 报告输出目录（apps/hrs-web/.test_record，置于 hrs-web 根下且以 . 隐藏）
# WT_ROOT 为 scripts/test_wt，需上溯两级到达 apps/hrs-web：
#   scripts/test_wt → scripts → hrs-web
REPORT_DIR="$(cd "${WT_ROOT}/../.." && pwd)/.test_record"

# ---- 颜色与输出工具函数 ----
# 仅用于终端可视化提示，不影响报告文件内容（报告由下方 { ... } > 重定向生成）。
green()  { printf '\033[32m%s\033[0m\n' "$1"; }   # 成功/通过
red()    { printf '\033[31m%s\033[0m\n' "$1"; }   # 失败
cyan()   { printf '\033[36m%s\033[0m\n' "$1"; }   # 章节标题
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }   # 警告/跳过/环境未就绪
section(){ cyan "##################################################"; cyan "$1"; cyan "##################################################"; }

# ---- 参数解析 ----
MODE="all"
TARGET_MODULE=""
RUN_LINT=0               # 是否开启前端 ESLint 检查（默认关闭）
for arg in "$@"; do
  case "$arg" in
    --list)
      MODE="list"
      ;;
    --lint)
      # 开启前端 ESLint 检查（默认关闭，开启后透传给各前端 .sh）
      RUN_LINT=1
      ;;
    ""|all)
      MODE="all"
      ;;
    *)
      # 非 -- 开头的参数视为「指定功能模块名」
      MODE="module"
      TARGET_MODULE="$arg"
      ;;
  esac
done
# 当同时出现 --list 与模块名时，--list 优先（仅列出不执行）
[ "${MODE}" = "list" ] && TARGET_MODULE=""

# 确保报告目录存在
mkdir -p "${REPORT_DIR}"

# ---- 收集功能模块目录 ----
# 遍历 test_wt/ 下所有一级子目录（按功能菜单路由命名），忽略报告目录与隐藏目录。
# 使用 find -print0 | sort -z 配合 read -d '' 读取：
#   -print0 / -d '' 以 NUL 分隔，可安全处理含空格或特殊字符的目录名；
#   sort -z 按 NUL 排序，保证模块执行顺序稳定可预期。
declare -a MODULES=()
while IFS= read -r -d '' dir; do
  name="$(basename "$dir")"
  # 跳过测试产物目录、模板脚手架目录与任何隐藏目录（以 . 开头），避免被误当作功能模块
  [ "$name" = "test_record" ] && continue
  [ "$name" = "__template__" ] && continue
  case "$name" in
    .*) continue ;;
  esac
  MODULES+=("$name")
done < <(find "${WT_ROOT}" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

if [ "${#MODULES[@]}" -eq 0 ]; then
  red "未找到任何功能模块目录（${WT_ROOT} 下应存在以功能路由命名的子目录）"
  exit 2
fi

# 若指定了单一模块，校验其存在
if [ "${MODE}" = "module" ]; then
  found=0
  for m in "${MODULES[@]}"; do
    [ "$m" = "${TARGET_MODULE}" ] && found=1 && break
  done
  if [ "$found" -ne 1 ]; then
    red "未找到指定功能模块: ${TARGET_MODULE}"
    echo "可用模块: ${MODULES[*]}"
    exit 2
  fi
  MODULES=("${TARGET_MODULE}")
fi

# ---- --list 模式：仅列出，不执行 ----
# 用于预检本次将走查哪些模块及其测试文件，便于 CI/本地快速确认范围，不触发任何测试。
if [ "${MODE}" = "list" ]; then
  section "将要执行的功能模块"
  for m in "${MODULES[@]}"; do
    mdir="${WT_ROOT}/${m}"
    backs=$(find "${mdir}" -maxdepth 1 -name '*.py' -type f | sort)
    fronts=$(find "${mdir}" -maxdepth 1 -name '*.sh' -type f | sort)
    echo "• ${m}"
    [ -n "${backs}" ] && echo "    后端: $(echo "${backs}" | xargs -n1 basename | tr '\n' ' ')"
    [ -n "${fronts}" ] && echo "    前端: $(echo "${fronts}" | xargs -n1 basename | tr '\n' ' ')"
    [ -z "${backs}" ] && [ -z "${fronts}" ] && echo "    （无 .py / .sh 测试文件）"
  done
  exit 0
fi

# 整体结果标志（0=通过，1=失败，2=环境/依赖未就绪即部分未执行）
OVERALL_RESULT=0
# 环境未就绪标志：任一模块因环境/依赖缺失导致检查未执行时置 1（非失败但需关注）
OVERALL_ENV=0

# 报告用的模块结果累加器。
# 选用临时文件而非关联数组：run_module 在循环中被多次调用，需跨调用累积结构化
# 多字段数据（模块名 | 状态 | 明细 | 失败原因）。以 TAB 分隔的四列写入临时文件，
# 便于后续报告阶段用 awk 稳定解析，避免在子 shell 中丢失数组状态。
SUMMARY_FILE="$(mktemp)"
: > "${SUMMARY_FILE}"

# 仓库根：WT_ROOT(=.../apps/hrs-web/scripts/test_wt) 上溯四级到仓库根。
REPO_ROOT="${WT_ROOT}/../../../.."
REPO_ROOT="$(cd "${REPO_ROOT}" && pwd)"
# 选择 Python 解释器：
# 1) 若用户已通过环境变量 PY_BIN 显式指定，则优先使用（便于指定已装依赖的 venv）。
# 2) 否则在候选解释器列表中，逐个探测能否成功 import server（即依赖已装全），
#    命中第一个即用；避免硬钉某个未装依赖的解释器导致后端整段 SKIP。
#    探测时需把仓库根加入 sys.path，否则非仓库根 cwd 下 import server 会失败。
# 3) 若候选均不可用，则 PY_BIN 为空，由 run_module 标记为 SKIP 并给出清晰提示。
PY_BIN="${PY_BIN:-}"
if [ -z "${PY_BIN}" ]; then
  PY_BIN=""
  # 优先项目本地 venv（若存在），其次常见 3.11 解释器，最后回退 PATH 中的 python3
  candidates="${REPO_ROOT}/.venv/bin/python3 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11 python3.11 python3"
  for cand in ${candidates}; do
    if command -v "${cand}" >/dev/null 2>&1; then
      if "${cand}" -c "import sys; sys.path.insert(0, '${REPO_ROOT}'); import server" >/dev/null 2>&1; then
        PY_BIN="${cand}"
        break
      fi
    fi
  done
fi
if [ -z "${PY_BIN}" ]; then
  echo "⚠ 未找到已安装项目依赖的 Python 解释器（import server 失败）。"
  echo "  请先安装依赖：pip install -r ${REPO_ROOT}/requirements.txt，或显式指定：PY_BIN=/path/to/venv/bin/python3 bash scripts/test_wt/test_wt.sh"
fi

# ---------------------------------------------------------
# 执行单个功能模块：先后端 .py、再前端 .sh
# 参数：$1 = 模块名
# 副作用：向 SUMMARY_FILE 追加一行（模块名 | 状态 | 明细 | 失败原因）
# ---------------------------------------------------------
run_module() {
  local mod="$1"
  local mdir="${WT_ROOT}/${mod}"
  local mod_result=0          # 0=通过/SKIP，1=失败
  local mod_env=0             # 0=正常，1=环境/依赖未就绪（检查未执行，非失败但需关注）
  local mod_detail=""         # 该模块的明细行（用于报告）
  local mod_fails=""          # 该模块的「失败原因穷举」累加器（每行一条，用于报告失败章节）

  section "功能模块：${mod}"

  # ---- 1) 后端测试（子目录内的 *.py）----
  # 明细与失败原因统一以「字面 \n + Markdown 表格行」形式累积到变量中：
  #   变量内的 \n 是反斜杠转义的换行（便于变量整体传递），报告阶段再由 awk 还原为真实换行。
  local back_files
  back_files=$(find "${mdir}" -maxdepth 1 -name '*.py' -type f | sort)
  if [ -z "${back_files}" ]; then
    yellow "△ ${mod}：无后端测试文件（.py），跳过"
    mod_detail="${mod_detail}\n| 后端 | — | 无 .py 文件 | SKIP |"
  else
    while IFS= read -r pyf; do
      [ -z "$pyf" ] && continue
      echo "--- 后端：${mod}/$(basename "$pyf") ---"
      if [ -z "${PY_BIN}" ]; then
        yellow "△ 后端 SKIP：未找到 Python 解释器"
        mod_detail="${mod_detail}\n| 后端 | $(basename "$pyf") | 无 Python 解释器 | SKIP |"
        continue
      fi
      local logf
      logf="/tmp/wt_${mod}_backend_$$.log"
      # 依赖就绪性：已由上方 PY_BIN 选择阶段确认——能 import server 即视为依赖就绪。
      # 此处直接用 PY_BIN 是否为空来判断，避免重复探测、也不误伤可选依赖。
      if [ -z "${PY_BIN}" ]; then
        yellow "△ 后端 SKIP（ENV）：未找到已安装项目依赖的 Python 解释器"
        yellow "  请先安装依赖：pip install -r ${REPO_ROOT}/requirements.txt"
        yellow "  或显式指定：PY_BIN=/path/to/venv/bin/python3 bash scripts/test_wt/test_wt.sh"
        mod_detail="${mod_detail}\n| 后端 | $(basename "$pyf") | 无可用 Python（需 pip install -r requirements.txt） | SKIP |"
        OVERALL_ENV=1
        continue
      fi
      # 双路输出：tee 既把 py 的标准输出/错误实时打印到终端，又完整写入 logf，
      # 以便下方用 grep 解析结论、穷举失败原因，且不丢失现场信息。
      # 关键：在子 shell 中切到仓库根目录再运行 py，并通过 PYTHONPATH 注入仓库根，
      # 确保无论脚本以绝对/相对路径运行，import api / server 都能从仓库根解析，
      # 避免「No module named 'api' / 'server'」等导入链失败。
      ( cd "${REPO_ROOT}" && PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" "${PY_BIN}" "$pyf" ) 2>&1 | tee "${logf}"

      # 解析 [RESULT]（取最后一条，容忍多轮输出）、[SUMMARY]（取最后一条，获取统计汇总）
      local rline
      rline=$(grep -E "^\[RESULT\]" "${logf}" | tail -1 | sed 's/^\[RESULT\] *//')
      local sline
      sline=$(grep -E "^\[SUMMARY\]" "${logf}" | tail -1 | sed 's/^\[SUMMARY\] *//')

      # 解析后端「按接口分组的检查项明细」，用于报告四、集成测试明细（4.1）：
      # 从后端脚本的 [INFO] === 接口分组名 === 提取分组，再从各 [PASS]/[FAIL]/[SKIP] 行
      # 提取逐条具体测试条件（如 search q=600519（code）：32 条结果、kline daily/1/limit=None：245 根），
      # 严格按脚本真实输出展开，不写死任何模块。
      # 输出格式：
      #   BEINTF|<接口分组名>          —— 标记一个新的接口分组（4.1.x 小节标题）
      #   BECOND|<条件描述>|<PASS|FAIL|SKIP>   —— 该分组下的逐条测试条件
      local be_detail_block
      # 注意：SUMMARY_FILE 列3 以「字面 \n」保存多行，避免真实换行破坏 TAB 四列结构。
      # 因此 be_detail_block 需为字面 \n 连接的多行（而非真实换行），下方用
      # awk 给每行补一个字面 \n（即 printf "%s\\n"），再由报告阶段 gsub(/\\n/,"\n") 还原。
      be_detail_block=$(awk '
        function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
        # [INFO] === 接口分组名 === 作为明细分组标题（无 === 包裹的 [INFO] 视为普通日志，忽略）
        /^\[INFO\]/ && /===/ {
          raw=$0
          sub(/^\[INFO\][ \t]*/, "", raw)          # 去掉 [INFO] 前缀
          if (match(raw, /===.*===/)) {            # 提取首尾 === 之间的接口分组名
            intf=substr(raw, RSTART+3, RLENGTH-6)
            gsub(/^[ \t]+|[ \t]+$/, "", intf)
            if (intf!="") printf "BEINTF|%s\\n", intf
          }
          next
        }
        /^\[PASS\]|^\[FAIL\]|^\[SKIP\]/ {
          st=$0; sub(/^\[/,"",st); sub(/\].*/,"",st)
          rest=$0; sub(/^\[[A-Z]+\][ \t]*/,"",rest)
          printf "BECOND|%s|%s\\n", trim(rest), st
        }
      ' "${logf}")

      case "${rline}" in
        PASS)
          green "✓ 后端通过（${sline}）"
          mod_detail="${mod_detail}\n| 后端 | 后端集成测试（真实调用接口） | ${sline:-通过} | PASS |"
          [ -n "${be_detail_block}" ] && mod_detail="${mod_detail}\nDETAILBLOCK<<后端\n${be_detail_block}\n>>"
          ;;
        FAIL)
          red "✗ 后端失败（${sline}）"
          mod_detail="${mod_detail}\n| 后端 | 后端集成测试（真实调用接口） | ${sline:-失败} | FAIL |"
          [ -n "${be_detail_block}" ] && mod_detail="${mod_detail}\nDETAILBLOCK<<后端\n${be_detail_block}\n>>"
          mod_result=1
          # 穷举失败原因：抓出日志中所有以 [FAIL] 开头的明细行，逐条记录到失败清单。
          # 对双引号做转义，避免写入临时文件后被 awk 误解析；sed 仅处理内容，不改变语义。
          local fail_lines
          fail_lines=$(grep -E "^\[FAIL\]" "${logf}" | sed 's/^\[FAIL\] *//' | sed 's/"/\\"/g')
          if [ -n "${fail_lines}" ]; then
            while IFS= read -r fl; do
              [ -z "$fl" ] && continue
              mod_fails="${mod_fails}\n- [${mod}/后端/$(basename "$pyf")] ${fl}"
            done <<< "${fail_lines}"
          else
            # 日志无 [FAIL] 行时（如异常中断），退而记录汇总信息与最后 20 行日志片段，保证可溯源
            mod_fails="${mod_fails}\n- [${mod}/后端/$(basename "$pyf")] 后端整体失败（${sline:-无明细}），关键日志："
            local tail_lines
            tail_lines=$(tail -n 20 "${logf}" | sed 's/"/\\"/g' | sed 's/^/    /')
            mod_fails="${mod_fails}\n${tail_lines}"
          fi
          ;;
        *)
          # rline 为空（后端脚本仅输出 [SUMMARY]、未输出 [RESULT]）时，回退到 sline 判定：
          # 若最后一条 [SUMMARY] 含 |PASS 则视为通过，|FAIL 视为失败，否则才标记 SKIP（环境/依赖未就绪）。
          if echo "${sline}" | grep -qE "\|PASS$"; then
            green "✓ 后端通过（${sline}）"
            mod_detail="${mod_detail}\n| 后端 | 后端集成测试（真实调用接口） | ${sline:-通过} | PASS |"
            [ -n "${be_detail_block}" ] && mod_detail="${mod_detail}\nDETAILBLOCK<<后端\n${be_detail_block}\n>>"
          elif echo "${sline}" | grep -qE "\|FAIL$"; then
            red "✗ 后端失败（${sline}）"
            mod_detail="${mod_detail}\n| 后端 | 后端集成测试（真实调用接口） | ${sline:-失败} | FAIL |"
            [ -n "${be_detail_block}" ] && mod_detail="${mod_detail}\nDETAILBLOCK<<后端\n${be_detail_block}\n>>"
            mod_result=1
            local fail_lines
            fail_lines=$(grep -E "^\[FAIL\]" "${logf}" | sed 's/^\[FAIL\] *//' | sed 's/"/\\"/g')
            if [ -n "${fail_lines}" ]; then
              while IFS= read -r fl; do
                [ -z "$fl" ] && continue
                mod_fails="${mod_fails}\n- [${mod}/后端/$(basename "$pyf")] ${fl}"
              done <<< "${fail_lines}"
            else
              mod_fails="${mod_fails}\n- [${mod}/后端/$(basename "$pyf")] 后端整体失败（${sline:-无明细}），关键日志："
              local tail_lines
              tail_lines=$(tail -n 20 "${logf}" | sed 's/"/\\"/g' | sed 's/^/    /')
              mod_fails="${mod_fails}\n${tail_lines}"
            fi
          else
            yellow "△ 后端 SKIP（${sline}）—— 依赖缺失或不可联网，未执行"
            mod_detail="${mod_detail}\n| 后端 | 后端集成测试（真实调用接口） | ${sline:-SKIP} | SKIP |"
            [ -n "${be_detail_block}" ] && mod_detail="${mod_detail}\nDETAILBLOCK<<后端\n${be_detail_block}\n>>"
            mod_env=1
            mod_fails="${mod_fails}\n- [${mod}/后端/$(basename "$pyf")] 未执行（环境/依赖缺失）：${sline:-SKIP}"
          fi
          ;;
      esac
    done <<< "${back_files}"
  fi

  # ---- 2) 前端测试（子目录内的 *.sh）----
  local front_files
  front_files=$(find "${mdir}" -maxdepth 1 -name '*.sh' -type f | sort)
  if [ -z "${front_files}" ]; then
    yellow "△ ${mod}：无前端测试文件（.sh），跳过"
    mod_detail="${mod_detail}\n| 前端 | — | 无 .sh 文件 | SKIP |"
  else
    while IFS= read -r shf; do
      [ -z "$shf" ] && continue
      echo "--- 前端：${mod}/$(basename "$shf") ---"
      local shlogf="/tmp/wt_${mod}_frontend_$$.log"
      # 捕获前端 sh 的完整输出，便于失败原因穷举。
      # 前端 sh 退出码语义（约定）：0=通过/SKIP，1=失败，2=环境/依赖未就绪（未执行）。
      # 透传 lint 开关：RUN_LINT=1 时向后端 .sh 传入 "lint" 作为首个参数，告知其执行 ESLint。
      local lint_arg=""
      [ "${RUN_LINT}" -eq 1 ] && lint_arg="lint"
      if [ "${RUN_LINT}" -eq 1 ]; then
        yellow "（本次已开启前端 ESLint 检查）"
      fi
      # 注：${lint_arg} 在为空时不传参；在 shell 中写为裸变量展开以避免产生空参数。
      if bash "$shf" ${lint_arg} 2>&1 | tee "${shlogf}"; then
        green "✓ 前端通过（含良性 SKIP 视为非阻断）"
      else
        # PIPESTATUS[0] 取管道中首个命令（bash "$shf"）的真实退出码；
        # 因管道整体受 tee 影响，必须读 PIPESTATUS 而非 $?，否则拿到的只是 tee 的退出码。
        local shrc=${PIPESTATUS[0]}
        if [ "${shrc}" -eq 2 ]; then
          # 环境/依赖未就绪（如 npm 不可用）：非失败但需关注，标记 mod_env
          yellow "⚠ 前端环境未就绪（退出码 2），检查未执行"
          mod_env=1
          mod_fails="${mod_fails}\n- [${mod}/前端/$(basename "$shf")] 环境/依赖未就绪，检查未执行（退出码 2）"
        else
          red "✗ 前端失败（退出码 ${shrc}）"
          mod_result=1
          # 穷举失败原因：前端 sh 一般通过 mark_fail 标红失败项，抓取含 ✗ / FAIL / Error 的行，
          # 限前 30 条，避免单模块海量报错撑爆报告；无匹配时退化为记录尾部日志片段。
          local sh_fail_lines
          sh_fail_lines=$(grep -E "✗|FAIL|Error|error:" "${shlogf}" | sed 's/"/\\"/g' | head -n 30)
          if [ -n "${sh_fail_lines}" ]; then
            while IFS= read -r sfl; do
              [ -z "$sfl" ] && continue
              mod_fails="${mod_fails}\n- [${mod}/前端/$(basename "$shf")] ${sfl}"
            done <<< "${sh_fail_lines}"
          else
            mod_fails="${mod_fails}\n- [${mod}/前端/$(basename "$shf")] 前端整体失败（退出码 ${shrc}），关键日志："
            local sh_tail
            sh_tail=$(tail -n 20 "${shlogf}" | sed 's/"/\\"/g' | sed 's/^/    /')
            mod_fails="${mod_fails}\n${sh_tail}"
          fi
        fi
      fi
      # 从前端日志解析结构化 [CHECK] 行，生成「检查项级」汇总行与明细块（供报告三/四节使用）
      # fe_checks 同样需为字面 \n 连接（与后端 be_detail_block 同理，避免破坏 SUMMARY 列结构）
      local fe_checks
      fe_checks=$(grep -E '^\[CHECK\] 前端\|' "${shlogf}" | sed 's/^\[CHECK\] 前端|//' | awk '{printf "%s\\n", $0}')
      if [ -n "${fe_checks}" ]; then
        while IFS='|' read -r cname cstatus cdetail; do
          [ -z "$cname" ] && continue
          mod_detail="${mod_detail}\n| 前端 | ${cname} | ${cdetail} | ${cstatus} |"
        done <<< "$(printf '%s' "${fe_checks}" | sed 's/\\n/\n/g')"
        mod_detail="${mod_detail}\nDETAILBLOCK<<前端\n${fe_checks}\n>>"
      else
        # 前端脚本未输出 [CHECK]（极旧脚本或异常）：保留文件级兜底行，确保报告不缺项
        mod_detail="${mod_detail}\n| 前端 | $(basename "$shf") | 退出码 ${shrc:-0} | $([ "${shrc:-0}" -eq 0 ] && echo PASS || echo FAIL) |"
      fi
    done <<< "${front_files}"
  fi

  # 模块级结论（三态优先级：失败 > 环境未就绪 > 通过）
  # 失败优先于环境未就绪，确保任一真实失败不被环境告警掩盖。
  local mod_status=0
  if [ "${mod_result}" -ne 0 ]; then
    mod_status=1
    red "✗ 模块「${mod}」存在失败项"
    OVERALL_RESULT=1
  elif [ "${mod_env}" -ne 0 ]; then
    mod_status=2
    yellow "⚠ 模块「${mod}」环境/依赖未就绪，部分检查未执行"
    OVERALL_ENV=1
  else
    green "✓ 模块「${mod}」前后端走查完成"
  fi

  # 写入汇总（TAB 分隔四列，与报告解析约定一致）：
  #   列1 模块名 | 列2 状态(0/1/2) | 列3 明细(含字面 \n 的表格行) | 列4 失败原因穷举(含字面 \n)
  printf '%s\t%s\t%s\t%s\n' "${mod}" "${mod_status}" "${mod_detail}" "${mod_fails}" >> "${SUMMARY_FILE}"
}

# ---------------------------------------------------------
# 逐模块执行
# ---------------------------------------------------------
for m in "${MODULES[@]}"; do
  run_module "$m"
done

# ---------------------------------------------------------
# 生成走查报告
# 说明：SUMMARY_FILE 中累积的明细/失败原因以「字面 \n」保存（变量内为反斜杠转义换行），
# 报告阶段用 awk 的 gsub(/\\n/,"\n") 还原为真实换行后再渲染表格，保证 Markdown 结构正确。
#
# 报告输出结构：在 .test_record/ 下新建一个以时间戳命名的子目录
#   .test_record/test_wt_report_<TS>/
#     ├── test_wt_report_<TS>.md        # 总体报告（覆盖全部模块）
#     └── test_wt_<Mod>_report_<TS>.md  # 各功能模块独立报告（Mod 即模块目录名）
# 采用「时间戳文件夹」而非单文件，便于一次走查的产物集中归档、对比与回溯。
#
# 报告模板（两个，结构严格遵守）：
#   - 板块功能报告：scripts/test_wt/__template__/class_template.md
#       结构：标题 / 基本信息 / 环境信息 / 一走查范围 / 二执行介绍 / 三执行结果汇总
#             / 四集成测试明细 / 五人工UI走查清单 / 六问题边界 / 七结论
#   - 整体报告：    scripts/test_wt/__template__/sum_template.md
#       结构：标题 / 基本信息 / 环境信息 / 一执行结果汇总 / 二各模块执行结果 / 三结论
# 模板内使用 __XXX__ 命名占位符（如 __TITLE__ / __MODULE__ / __SUMMARY_TABLE__ 等），
# 由下方报告生成函数按模块/整体分别填充，保证输出与模板结构完全一致。
# ---------------------------------------------------------
TS="$(date +%Y_%m_%d_%H_%M_%S)"

# 报告输出根目录（时间戳子目录）：将全部报告集中归档，避免与历史报告混淆。
REPORT_SUBDIR="${REPORT_DIR}/test_wt_report_${TS}"
mkdir -p "${REPORT_SUBDIR}"

# 总体报告路径（位于时间戳文件夹内）
REPORT_FILE="${REPORT_SUBDIR}/test_wt_report_${TS}.md"

# 模板文件（与本脚本同目录）
TEMPLATE_DIR="${SCRIPT_DIR}"
CLASS_TEMPLATE="${TEMPLATE_DIR}/__template__/class_template.md"
SUM_TEMPLATE="${TEMPLATE_DIR}/__template__/sum_template.md"

# 说明：模块名（Mod）直接取自 test_wt/ 下的子目录名（如 kline、AAA），
# 报告文件名与标题均使用原始模块名，与目录名保持完全一致，便于对应溯源。

# 文案映射辅助函数（供板块报告与整体报告共用，避免重复三态映射逻辑）：
#   - mapres            ：把后端 PASS/SKIP/SKIP(ENV)/FAIL 映射为三态中文文案（与模板一致）
#   - mod_result_text   ：模块级结果文案（三态）
#   - overall_result_text：整体结果文案（三态，结合 OVERALL_RESULT / OVERALL_ENV）
# 注：SUMMARY_FILE 中某模块的明细列（列3）以「字面 \n」保存，报告阶段用 awk 的
#     gsub(/\\n/,"\n") 还原为真实换行后再拆出「| 端 | 文件 | 明细 | 结果 |」表格行。

# mapres：把后端 PASS/SKIP/SKIP(ENV)/FAIL 映射为三态中文文案（与模板一致）。
mapres() {
  case "$1" in
    PASS|SKIP)     echo "✅ 通过（含良性 SKIP）" ;;
    SKIP\(ENV\))   echo "⚠️ 环境未就绪" ;;
    FAIL)          echo "❌ 失败" ;;
    *)             echo "$1" ;;
  esac
}

# 模块级结果文案（三态）
mod_result_text() {
  case "$1" in
    0) echo "✅ 通过（含良性 SKIP）" ;;
    1) echo "❌ 失败（需修复）" ;;
    2) echo "⚠️ 环境未就绪（部分未执行）" ;;
  esac
}

# 整体结果文案（三态）
overall_result_text() {
  if [ "${OVERALL_RESULT}" -ne 0 ]; then
    echo "❌ 失败（需修复）"
  elif [ "${OVERALL_ENV}" -ne 0 ]; then
    echo "⚠️ 环境未就绪（部分未执行）"
  else
    echo "✅ 通过（含良性 SKIP）"
  fi
}

# ---------------------------------------------------------
# 生成「各功能模块独立报告」（落于时间戳文件夹内，命名 test_wt_<Mod>_report_<TS>.md，Mod 即模块目录名）
# 模板严格遵守 scripts/test_wt/__template__/class_template.md，章节顺序与标题完全一致：
#   基本信息 / 环境信息 / 一、走查范围 / 二、执行介绍 / 三、执行结果汇总 /
#   四、集成测试明细 / 五、人工 UI 走查清单 / 六、发现的问题与边界行为 / 七、结论
# 参数：$1=模块名 $2=模块状态(0/1/2) $3=该模块明细(含字面\n) $4=该模块失败原因(含字面\n)
# ---------------------------------------------------------
gen_module_report() {
  local mod="$1"; local st="$2"; local md="$3"; local mf="$4"
  # 文件名与标题统一使用原始模块名（与 test_wt/ 下的子目录名一致，如 kline）
  local mod_report="${REPORT_SUBDIR}/test_wt_${mod}_report_${TS}.md"
  local mod_res
  mod_res="$(mod_result_text "${st}")"

  # ---- 占位符内容：基本信息 ----
  local t_name; t_name="$(basename "${mod_report}")"
  local t_dir="${REPORT_SUBDIR}"
  local t_script="apps/hrs-web/scripts/test_wt/test_wt.sh"
  local t_time="${TS}"
  local t_mod="${mod}"
  local t_result="${mod_res}"

  # ---- 占位符内容：环境信息（固定描述，与模板一致）----
  local t_fe_env="Node（npm/npx Vitest / tsc），由 test_wt/${mod}/ 下前端走查脚本执行"
  local t_be_env="Python（FastAPI TestClient，真实调用接口，非 mock）；联网访问外部行情源"
  local t_exec_dir="apps/hrs-web"
  local t_exit_code="${st}（0=通过/良性SKIP，1=失败，2=环境未就绪）"

  # ---- 占位符内容：一、走查范围 ----
  # 从明细中区分前端/后端测试文件，列出本次执行的测试项（跳过「无 .py/.sh 文件」占位行）。
  local t_scope
  t_scope="$(awk -F'\t' -v cur="$mod" '
    function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
    {
      if ($1 != cur) next
      d=$3; gsub(/\\n/,"\n",d); n=split(d,lines,"\n")
      for (k=1;k<=n;k++){
        L=lines[k]
        if (L ~ /^\s*\|/) {
          tmp=L; sub(/^\s*\|/,"",tmp); sub(/\|[ \t]*$/,"",tmp)
          cnt=split(tmp,cols,"|")
          for (c=1;c<=cnt;c++) cols[c]=trim(cols[c])
          if (cols[2]=="—") next
          printf "- **%s**：\`%s\`\n", cols[1], cols[2]
        }
      }
    }
    ' "${SUMMARY_FILE}")"

  # ---- 占位符内容：二、执行介绍（前端 mock / 后端真实调用 通用描述）----
  # 依据本模块实际存在的前端/后端测试文件，给出通用执行介绍；与模板 2.1/2.2 层级一致。
  local t_intro=""
  t_intro="${t_intro}### 2.1 前端（mock 后端，验证请求拼装与返回解析）"
  t_intro="${t_intro}
"
  t_intro="${t_intro}
前端走查脚本 \`test_wt/${mod}/test_wt_${mod}_frontend.sh\` 在隔离环境下验证前端对后端的请求拼装与返回结构解析，覆盖："
  t_intro="${t_intro}
- 接口契约 + 调用正确性：接口 URL / Query 参数拼装，及返回结构解析"
  t_intro="${t_intro}
- 页面功能整体正确性：搜索 / 加载 / 周期切换 / 全量开关 / 错误态"
  t_intro="${t_intro}
- 组件层渲染：结构 / 样式 / 边界"
  t_intro="${t_intro}
- 代码规范（ESLint，需 --lint 开启）+ TypeScript 类型检查（tsc）"
  t_intro="${t_intro}
"
  t_intro="${t_intro}
### 2.2 后端（真实调用 FastAPI 接口，非 mock）"
  t_intro="${t_intro}
"
  t_intro="${t_intro}
后端集成测试脚本 \`test_wt/${mod}/test_wt_${mod}_backend.py\` 通过 \`FastAPI TestClient\` 真实调用对应接口端点，遍历参数组合，断言 HTTP 200 + 返回 JSON 结构与字段符合 Schema 模型定义；联网访问外部行情源。"

  # ---- 占位符内容：三、执行结果汇总（表格 + 通过/跳过/失败项统计）----
  # 汇总表的每一行对应一个「检查项」：前端按 [CHECK] 拆项（组件单测/契约/页面走查/ESLint/tsc…），
  # 后端为「后端集成测试（真实调用接口）」单行（其接口级明细在第四节展开）。
  # 注意：mod_detail 内可能含 DETAILBLOCK 块（非表格行），解析时跳过以免污染汇总表。
  local t_summary_table
  t_summary_table="$(awk -F'\t' -v cur="$mod" '
    BEGIN { nr=0; inblock=0 }
    function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
    function mapres(s){
      if (s=="PASS" || s=="SKIP") return "✅ 通过（含良性 SKIP）"
      if (s=="SKIP(ENV)") return "⚠️ 环境未就绪"
      if (s=="FAIL") return "❌ 失败"
      return s
    }
    {
      if ($1 != cur) next
      d=$3; gsub(/\\n/,"\n",d); n=split(d,lines,"\n")
      for (k=1;k<=n;k++){
        L=lines[k]
        if (L ~ /^DETAILBLOCK<</) { inblock=1; continue }
        if (L ~ /^>>$/) { inblock=0; continue }
        if (inblock) continue
        if (L ~ /^\s*\|/) {
          tmp=L; sub(/^\s*\|/,"",tmp); sub(/\|[ \t]*$/,"",tmp)
          cnt=split(tmp,cols,"|")
          for (c=1;c<=cnt;c++) cols[c]=trim(cols[c])
          if (cols[2]=="—") next
          nr++
          printf "| %d | %s | %s | %s | %s |\n", nr, cols[1], cols[2], mapres(cols[4]), cols[3]
        }
      }
    }
    ' "${SUMMARY_FILE}")"
  # 人工 UI 走查清单在汇总表内作为固定末行（与模板一致）
  local t_summary_header="| 序号 | 端  | 检查项                    | 结果             | 明细                                            |
| :- | :- | :--------------------- | :------------- | :-------------------------------------------- |"
  # 计数末行的人工 UI 行序号
  local t_summary_tail="| $(( $(echo "${t_summary_table}" | grep -c '^|') + 1 ))  | —  | 人工 UI 走查清单             | ⏳ 待人工核对        | 不在自动化范围内（见第四节）                                |"
  local t_pass_skips
  if [ "${st}" -eq 0 ]; then
    t_pass_skips="- **通过项**：见上方汇总（全部 PASS / 良性 SKIP）
- **跳过项**：见上方汇总（标 ⚠️ 环境未就绪 或 设计性 SKIP）
- **失败项**：0"
  elif [ "${st}" -eq 2 ]; then
    t_pass_skips="- **失败项**：0（无断言失败）
- **环境未就绪项**：存在（部分检查因环境/依赖缺失未执行，见问题清单与结论）"
  else
    t_pass_skips="- **失败项**：存在（见上方汇总中标 ❌ 的行与第四节问题清单）"
  fi

  # ---- 占位符内容：四、集成测试明细（4.1 后端 / 4.2 前端，通用结构）----
  local t_detail
  t_detail="### 4.1 后端集成测试明细（真实联网调用）"
  t_detail="${t_detail}
"
  t_detail="${t_detail}> 测试脚本：\`scripts/test_wt/${mod}/test_wt_${mod}_backend.py\`，通过 \`create_app()\` 构建完整 FastAPI 应用后真实调用。"
  t_detail="${t_detail}
"
  # 后端明细：从 DETAILBLOCK 后端块提取 BEINTF（接口分组）/ BECOND（条件|状态），按接口分组展开
  t_detail="${t_detail}
"
  local t_be_detail
  t_be_detail=$(awk -F'\t' -v cur="$mod" '
    function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
    function mapres(s){
      if (s=="PASS" || s=="SKIP") return "✅"
      if (s=="SKIP(ENV)") return "⚠️"
      if (s=="FAIL") return "❌"
      return s
    }
    BEGIN { sec=0 }
    function emit_intf(name){
      sec++
      printf "\n#### 4.1.%d %s\n", sec, name
    }
    {
      if ($1 != cur) next
      d=$3; gsub(/\\n/,"\n",d); n=split(d,lines,"\n")
      inbe=0
      for (k=1;k<=n;k++){
        L=lines[k]
        if (L ~ /^DETAILBLOCK<</) { inbe=(L ~ /<<后端/) }
        else if (L ~ /^>>$/) { inbe=0 }
        else if (inbe) {
          if (L ~ /^BEINTF\|/) {
            emit_intf(substr(L, index(L,"|")+1))
          } else if (L ~ /^BECOND\|/) {
            if (sec==0) emit_intf("后端集成测试")
            rest=substr(L, index(L,"|")+1)
            split(rest, p, "|")
            printf "- %s %s\n", mapres(trim(p[2])), trim(p[1])
          }
        }
      }
    }
    ' "${SUMMARY_FILE}")
  t_detail="${t_detail}${t_be_detail}
"
  t_detail="${t_detail}
### 4.2 前端测试明细"
  t_detail="${t_detail}
"
  t_detail="${t_detail}> 测试脚本：\`scripts/test_wt/${mod}/test_wt_${mod}_frontend.sh\`"
  t_detail="${t_detail}
"
  t_detail="${t_detail}
#### 4.2.1 前端各走查项明细"
  t_detail="${t_detail}
"
  t_detail="${t_detail}
$(awk -F'\t' -v cur="$mod" '
    function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
    function mapres(s){
      if (s=="PASS" || s=="SKIP") return "✅"
      if (s=="SKIP(ENV)") return "⚠️"
      if (s=="FAIL") return "❌"
      return s
    }
    {
      if ($1 != cur) next
      d=$3; gsub(/\\n/,"\n",d); n=split(d,lines,"\n")
      infe=0
      for (k=1;k<=n;k++){
        L=lines[k]
        if (L ~ /^DETAILBLOCK<</) { infe=(L ~ /<<前端/) }
        else if (L ~ /^>>$/) { infe=0 }
        else if (infe && L ~ /\|/) {
          # 行格式：检查项名|状态|明细
          split(L, p, "|")
          printf "- \`%s\`：%s %s\n", trim(p[1]), mapres(trim(p[2])), trim(p[3])
        }
      }
    }
    ' "${SUMMARY_FILE}")"

  # ---- 占位符内容：五、人工 UI 走查清单 ----
  # 设计原则：清单由各功能模块自行提供，主脚本不内嵌任何具体功能的写死清单。
  # 内容必须基于页面真实代码 / 注释 / 交互 / 边界手写，不套用模板。读取优先级：
  #   1) 优先从模块前端走查脚本 test_wt_<mod>_frontend.sh 的
  #      <!--BEGIN_MANUAL_CHECKLIST--> ... <!--END_MANUAL_CHECKLIST--> 标记区间提取
  #      （新设计：清单内联于前端脚本，由开发者基于页面实际内容填写）；
  #   2) 兼容旧机制：模块目录内 MANUAL_CHECKLIST.md（已手写模块可直接复用）；
  #   3) 缺失时回退到下方 DEFAULT_MANUAL 通用兜底清单（仅作占位）。
  local t_manual=""
  local mod_fe="${WT_ROOT}/${mod}/test_wt_${mod}_frontend.sh"
  local mod_manual="${WT_ROOT}/${mod}/MANUAL_CHECKLIST.md"
  if [ -f "${mod_fe}" ] && grep -q "BEGIN_MANUAL_CHECKLIST" "${mod_fe}"; then
    # 从前端脚本标记区间提取清单正文（跳过标记行本身）
    t_manual="$(awk '/BEGIN_MANUAL_CHECKLIST/{f=1;next} /END_MANUAL_CHECKLIST/{f=0} f' "${mod_fe}")"
  elif [ -f "${mod_manual}" ]; then
    t_manual="$(cat "${mod_manual}")"
  else
    # 通用兜底清单（非写死到具体模块；新模块请在前端脚本步骤4标记区间内基于页面补全）。
    t_manual="#### 5.1 接口·调用
- [ ] 交互是否触发了正确的接口请求并解析出预期数据
- [ ] 请求是否正确携带关键参数（如 time / period / limit / page / sector_type 等）
- [ ] 后端返回字段与前端读取一致

#### 5.2 结构
- [ ] 核心可视化容器是否按预期渲染（默认尺寸与自定义尺寸生效）
- [ ] 关键区块 / 图表是否出现
- [ ] 图例、坐标轴、刻度是否清晰可读
- [ ] 鼠标悬停是否显示 tooltip

#### 5.3 样式
- [ ] 亮色主题：背景、文字、涨跌色是否符合预期
- [ ] 暗色主题（html.dark）：文字、坐标轴、分割线是否适配
- [ ] 小屏是否自适应、无溢出

#### 5.4 功能
- [ ] 各 tab / 周期 / 类型切换正常
- [ ] 时间快照 / 筛选器切换时数据正确刷新
- [ ] 边界交互（拖拽 / 缩放 / resize）自适应、不白屏
- [ ] 切换时不重复创建实例 / 内存泄漏

#### 5.5 边界
- [ ] 空数据：容器渲染、无崩溃、无报错
- [ ] 超大数据量：不卡死、无报错
- [ ] 字段为 null：不崩溃
- [ ] 组件卸载：资源正确释放"
  fi

  # ---- 占位符内容：六、发现的问题与边界行为 ----
  local t_issues
  if [ "${st}" -eq 0 ]; then
    t_issues="本模块走查过程中未发现阻断性问题；如存在非阻断的边界行为，建议在对应模块走查脚本或 issue 中记录。"
  else
    t_issues="本模块存在需关注项（失败 / 环境未就绪），详见第四节「集成测试明细」与第七节「结论」。"
  fi

  # ---- 占位符内容：七、结论 ----
  local t_conclusion
  if [ "${st}" -eq 1 ]; then
    t_conclusion="结论：模块「${mod}」存在未通过项，自动化走查未全部通过。请查看上方问题清单修复后重试；是否可交付取决于失败项是否闭环。"
  elif [ "${st}" -eq 2 ]; then
    t_conclusion="结论：模块「${mod}」无断言失败项，但存在环境/依赖未就绪导致部分检查未执行（非失败但需关注）。请就绪环境后重跑未覆盖项；是否可交付取决于未执行项的风险评估。"
  else
    t_conclusion="结论：模块「${mod}」前后端自动化走查通过（含良性 SKIP）。是否可交付，取决于上方「人工走查清单」是否逐项核对通过。"
  fi

  # ---- 读入模板并替换占位符 ----
  local out
  out="$(cat "${CLASS_TEMPLATE}")"
  out="${out//__TITLE__/${mod} 功能模块 - 测试走查报告}"
  out="${out//__REPORT_NAME__/${t_name}}"
  out="${out//__REPORT_DIR__/${t_dir}}"
  out="${out//__SCRIPT__/${t_script}}"
  out="${out//__TIME__/${t_time}}"
  out="${out//__MODULE__/${t_mod}}"
  out="${out//__RESULT__/${t_result}}"
  out="${out//__FE_ENV__/${t_fe_env}}"
  out="${out//__BE_ENV__/${t_be_env}}"
  out="${out//__EXEC_DIR__/${t_exec_dir}}"
  out="${out//__EXIT_CODE__/${t_exit_code}}"
  out="${out//__SCOPE__/${t_scope}}"
  out="${out//__INTRO__/${t_intro}}"
  out="${out//__SUMMARY_HEADER__/${t_summary_header}}"
  out="${out//__SUMMARY_TABLE__/${t_summary_table}}"
  out="${out//__SUMMARY_TAIL__/${t_summary_tail}}"
  out="${out//__PASS_SKIPS__/${t_pass_skips}}"
  out="${out//__DETAIL__/${t_detail}}"
  out="${out//__MANUAL__/${t_manual}}"
  out="${out//__ISSUES__/${t_issues}}"
  out="${out//__CONCLUSION__/${t_conclusion}}"
  printf '%s\n' "${out}" > "${mod_report}"

  green "模块报告已生成: ${mod_report}"
}

gen_overall_report() {
  # ---- 整体报告：严格遵守 scripts/test_wt/__template__/sum_template.md 模板 ----
  # 章节顺序与标题完全一致：基本信息 / 环境信息 / 一、执行结果汇总 / 二、各模块执行结果 / 三、结论
  # 整体报告标题覆盖全部功能模块，不使用首个模块名（避免被误读为单模块报告）
  local s_title="全功能模块前后端走查报告（共 ${#MODULES[@]} 个模块）"
  local s_name; s_name="$(basename "${REPORT_FILE}")"
  local s_dir="${REPORT_SUBDIR}"
  local s_script="apps/hrs-web/scripts/test_wt/test_wt.sh"
  local s_time="${TS}"
  local s_modcount="${#MODULES[@]}（${MODULES[*]}）"
  local s_overall
  s_overall="$(overall_result_text)"
  local s_fe_env="Node（npm/npx Vitest / tsc），由 test_wt/ 下前端走查脚本执行"
  local s_be_env="Python（FastAPI TestClient，真实调用接口，非 mock）；联网访问外部行情源"
  local s_exec_dir="apps/hrs-web"
  local s_exit_code="${OVERALL_RESULT}"
  if [ "${OVERALL_RESULT}" -eq 0 ] && [ "${OVERALL_ENV}" -ne 0 ]; then
    s_exit_code="2（无失败但环境/依赖未就绪）"
  fi

  # 一、执行结果汇总（序号 | 端 | 检查项 | 结果 | 明细），跨模块连续序号
  local s_sum_header="| 序号 | 端  | 检查项                  | 结果             | 明细                            |
| -- | :- | -------------------- | -------------- | ----------------------------- |"
  local s_sum_table
  s_sum_table="$(awk -F'\t' '
  BEGIN { nr=0 }
  function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
  function mapres(s){
    if (s=="PASS" || s=="SKIP") return "✅ 通过（含良性 SKIP）"
    if (s=="SKIP(ENV)") return "⚠️ 环境未就绪"
    if (s=="FAIL") return "❌ 失败"
    return s
  }
  function checkname(f){
    if (f ~ /frontend/) return "前端走查（单测/契约/渲染/规范/类型）"
    if (f ~ /backend/)  return "后端集成测试（真实调用接口）"
    return f
  }
  {
    m=$1; d=$3
    gsub(/\\n/,"\n",d)
    n=split(d, lines, "\n")
    for (k=1;k<=n;k++){
      L=lines[k]
      if (L ~ /^\s*\|/) {
        tmp=L; sub(/^\s*\|/,"",tmp); sub(/\|[ \t]*$/,"",tmp)
        cnt=split(tmp, cols, "|")
        for (c=1;c<=cnt;c++) cols[c]=trim(cols[c])
        if (cols[2]=="—") next
        nr++
        printf "| %d  | %s | %s | %s | %s |\n", nr, cols[1], checkname(cols[2]), mapres(cols[4]), cols[3]
      }
    }
  }
  ' "${SUMMARY_FILE}")"

  # 通过/跳过/失败项统计（与模板底部一致）
  local s_pass_skips="- **通过项**：见上方汇总（全部 PASS / 良性 SKIP）
- **跳过项**：见上方汇总（标 ⚠️ 环境未就绪 或 设计性 SKIP）
- **失败项**：0"

  # 二、各模块执行结果（序号 | 功能模块 | 端 | 测试文件 | 测试明细 | 测试结果）
  local s_mod_header="| 序号 | 功能模块  | 端  | 测试文件                         | 测试明细                          | 测试结果           |
| :- | :---- | :- | :--------------------------- | :---------------------------- | :------------- |"
  local s_mod_table
  s_mod_table="$(awk -F'\t' '
  BEGIN { nr=0 }
  function trim(s){ gsub(/^[ \t]+/,"",s); gsub(/[ \t]+$/,"",s); return s }
  function mapres(s){
    if (s=="PASS" || s=="SKIP") return "✅ 通过（含良性 SKIP）"
    if (s=="SKIP(ENV)") return "⚠️ 环境未就绪"
    if (s=="FAIL") return "❌ 失败"
    return s
  }
  {
    m=$1; d=$3
    gsub(/\\n/,"\n",d)
    n=split(d, lines, "\n")
    for (k=1;k<=n;k++){
      L=lines[k]
      if (L ~ /^\s*\|/) {
        tmp=L; sub(/^\s*\|/,"",tmp); sub(/\|[ \t]*$/,"",tmp)
        cnt=split(tmp, cols, "|")
        for (c=1;c<=cnt;c++) cols[c]=trim(cols[c])
        if (cols[2]=="—") next
        nr++
        printf "| %d  | %s | %s | %s | %s | %s |\n", nr, m, cols[1], cols[2], cols[3], mapres(cols[4])
      }
    }
  }
  ' "${SUMMARY_FILE}")"

  # 三、结论
  local s_conclusion
  if [ "${OVERALL_RESULT}" -ne 0 ]; then
    s_conclusion="结论：存在未通过模块，请查看上方「问题清单」修复后重试。"
  elif [ "${OVERALL_ENV}" -ne 0 ]; then
    s_conclusion="结论：无失败项，但存在环境/依赖未就绪导致部分检查未执行（非失败但需关注）；请就绪环境后重跑以获得完整结论。"
  else
    s_conclusion="结论：全部功能模块前后端自动化走查通过（含良性 SKIP）。"
  fi

  # 读入模板并替换占位符
  local out
  out="$(cat "${SUM_TEMPLATE}")"
  out="${out//__TITLE__/${s_title}}"
  out="${out//__REPORT_NAME__/${s_name}}"
  out="${out//__REPORT_DIR__/${s_dir}}"
  out="${out//__SCRIPT__/${s_script}}"
  out="${out//__TIME__/${s_time}}"
  out="${out//__MODULE_COUNT__/${s_modcount}}"
  out="${out//__OVERALL_RESULT__/${s_overall}}"
  out="${out//__FE_ENV__/${s_fe_env}}"
  out="${out//__BE_ENV__/${s_be_env}}"
  out="${out//__EXEC_DIR__/${s_exec_dir}}"
  out="${out//__EXIT_CODE__/${s_exit_code}}"
  out="${out//__SUMMARY_HEADER__/${s_sum_header}}"
  out="${out//__SUMMARY_TABLE__/${s_sum_table}}"
  out="${out//__PASS_SKIPS__/${s_pass_skips}}"
  out="${out//__MODULES_HEADER__/${s_mod_header}}"
  out="${out//__MODULES_TABLE__/${s_mod_table}}"
  out="${out//__CONCLUSION__/${s_conclusion}}"
  printf '%s\n' "${out}" > "${REPORT_FILE}"
}

# ---------------------------------------------------------
# 逐个功能模块生成独立报告（落于同一时间戳文件夹内）
# 从 SUMMARY_FILE 逐行读取「模块名 | 状态 | 明细 | 失败原因」，
# 对每个模块调用 gen_module_report 产出 test_wt_<Mod>_report_<TS>.md。
# ---------------------------------------------------------
while IFS=$'\t' read -r _m _r _d _f; do
  gen_module_report "${_m}" "${_r}" "${_d}" "${_f}"
done < "${SUMMARY_FILE}"

# 整体报告需在 SUMMARY_FILE 删除前生成（其数据同样来自该文件）
gen_overall_report

rm -f "${SUMMARY_FILE}"

green "总体报告已生成: ${REPORT_FILE}"
green "各模块报告已生成于: ${REPORT_SUBDIR}"

# ---- 最终退出码（三态）----
# 失败优先于环境未就绪：只要有任一模块失败即返回 1（阻断，需修复）；
# 仅在无失败但存在环境未就绪时返回 2（未执行，需关注，建议就绪环境后重跑）；
# 全部通过（含良性 SKIP）返回 0。此退出码供 CI 判定走查是否通过。
#   1 = 存在失败模块（阻断，需修复）
#   2 = 无失败但存在环境/依赖未就绪（未执行，需关注，建议就绪环境后重跑）
#   0 = 全部通过
if [ "${OVERALL_RESULT}" -ne 0 ]; then
  exit 1
elif [ "${OVERALL_ENV}" -ne 0 ]; then
  exit 2
else
  exit 0
fi
