
# 📈 基于AI + skills 自动生成前后端自动测试脚本

> 🤖 前后端自动化测试脚本生成器

<br/> 

### 一、这个 skill 是做什么的
它是一个脚手架生成器：给你一个功能模块的路由名（比如 sector-analysis），它自动在 scripts/test_wt/`<route>`/ 下生成两个可执行的走查脚本骨架
- test_wt_`<route>`_backend.py —— 后端接口集成测试（FastAPI TestClient 真实调用）
- test_wt_`<route>`_frontend.sh —— 前端契约/渲染测试 + ESLint/tsc 检查
生成的是带占位符的骨架，你再按需填入具体接口和断言即可，不需要每次都消耗 AI。

<br/> 

### 🚀 二、怎么用

#### 方式1：直接运行脚手架（最常用）

```bash
cd /apps/dsa-web/scripts/gen-wt-skill
bash scaffold_wt.sh <route> [PageBasename]
```

示例：
```bash
bash scaffold_wt.sh sector-analysis SectorAnalysisPage
```

- route 必填，功能菜单路由，也是目录名和文件前缀（建议小写中划线，如 sector-analysis）。
- [PageBasename]：可选，前端页面组件基名，用于填充前端脚本里的路径占位符。
执行后会在 scripts/test_wt/`<route>`/ 下生成两个文件。

<br/> 

#### 方式2：在 AI 编码工具里触发（SKILL.md 的作用）

SKILL.md 是给 Claude Code / 类 Claude 工具看的说明。当你在对话里说"给 xxx 功能模块生成走查脚本"时，工具会读取 SKILL.md 里的触发条件、输入契约、SOP 和参考范例（kline / sector-analysis），然后自动调用 scaffold_wt.sh 并按模板填充，而不是从零手写。

提问示例：
```bash
我项目里有一些功能页面需要进行测试走查
菜单路由：域名+/sector-analysis
对应的核心代码文件：apps/dsa-web/src/pages/SectorAnalysisPage.tsx
请你基于SIKLLS：apps/dsa-web/scripts/test_wt_gen/test_wt_gen_skill.md
帮我生成对应的测试走查脚本
```

<br/> 

### ✨ 三、如何进行前后端测试走查
用生成出来的脚本做走查：生成的脚本会被主脚本 scripts/test_wt/test_wt.sh 自动发现（因为它按目录扫描 test_wt/ 下的子目录）

```bash
# 跑单个模块
./scripts/test_wt/test_wt.sh sector-analysis

# 跑单个模块并带前端 lint
./scripts/test_wt/test_wt.sh sector-analysis --lint

# 列出所有已发现的模块
./scripts/test_wt/test_wt.sh --list
```

<br/> 

### ✨ 四、测试走查脚本的重新优化生成
用生成出来的脚本做走查：生成的脚本会被主脚本 scripts/test_wt/test_wt.sh 自动发现（因为它按目录扫描 test_wt/ 下的子目录）

```bash
/apps/dsa-web/scripts/test_wt/test_wt.sh
这个执行脚本需要优化：
1、因为要生成整体测试执行报告，以及遍历文件夹后生成各个板块功能的测试执行报告，我建议你要分为2个模板，一个是全功能模块前后端走查报告的模板，一个是板块功能前后端走查报告的模板
2、“整体测试执行报告”请参考：sum_template_example.md
3、“板块功能的测试执行报告”请参考：class_template_example.md，“执行结果汇总”和“集成测试明细”需要根据所生成前后端测试脚本里面的测试内容来展开，如：需要根据“test_wt_sector-analysis_backend.py”和“test_wt_sector-analysis_frontend.sh”里面的测试内容来展开生成。
4、请你仔细分析sum_template_example.md、class_template_example.md  这2个模板文件，对于输出的结构、内容，请你严格遵守
```

