$ErrorActionPreference = 'Stop'

Write-Host 'Building React UI (static assets)...'
Push-Location 'apps\hrs-web'
if (!(Test-Path 'node_modules')) {
  npm install
}
npm run build
Pop-Location

$pythonBin = $env:PYTHON_BIN
if ([string]::IsNullOrWhiteSpace($pythonBin)) {
  $pythonBin = 'python'
}

Write-Host "Using Python: $pythonBin"

Write-Host 'Verifying static asset references (source)...'
& $pythonBin "${PSScriptRoot}\check_static_assets.py" 'dist-web'
if ($LASTEXITCODE -ne 0) {
  throw "Static asset sanity check failed for source dist-web/. See GitHub #1064."
}

function Test-PythonCode {
  param(
    [string]$Python,
    [string]$Code
  )

  try {
    & $Python -c $Code *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}

Write-Host 'Building backend executable...'
if (-not (Test-PythonCode -Python $pythonBin -Code "import PyInstaller")) {
  & $pythonBin -m pip install pyinstaller
}

Write-Host 'Installing backend dependencies...'
& $pythonBin -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  throw "pip install -r requirements.txt failed with exit code $LASTEXITCODE."
}

Write-Host 'Checking python-multipart availability...'
if (-not (Test-PythonCode -Python $pythonBin -Code "import multipart, multipart.multipart")) {
  throw 'python-multipart is not importable in the selected Python environment.'
}

Write-Host 'Checking AlphaSift adapter availability...'
if (-not (Test-PythonCode -Python $pythonBin -Code "import alphasift.dsa_adapter")) {
  throw 'alphasift.dsa_adapter is not importable after installing requirements.'
}

Write-Host 'Checking Futu SDK availability...'
if (-not (Test-PythonCode -Python $pythonBin -Code "import futu")) {
  throw 'futu is not importable after installing requirements.'
}

Write-Host 'Checking orjson availability...'
if (-not (Test-PythonCode -Python $pythonBin -Code "import orjson")) {
  throw 'orjson is not importable after installing requirements.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# 桌面端产物统一收纳到 dist-desktop\：backend 为 PyInstaller 最终产物，.work\.specs 为中间产物（隐藏目录）。
# 仅清理 backend\.work\.specs 三项，不触碰 dist-desktop\frontend（由 build-desktop 脚本生成）。
if (-not (Test-Path 'dist-desktop')) {
  New-Item -ItemType Directory -Path 'dist-desktop' | Out-Null
}
foreach ($stale in @('backend', '.work', '.specs')) {
  $stalePath = Join-Path 'dist-desktop' $stale
  if (Test-Path $stalePath) {
    Remove-Item -Recurse -Force $stalePath
  }
}

$hiddenImports = @(
  'multipart',
  'multipart.multipart',
  'json_repair',
  'orjson',
  'tiktoken',
  'tiktoken_ext',
  'tiktoken_ext.openai_public',
  'api',
  'api.app',
  'api.deps',
  'api.v1',
  'api.v1.router',
  'api.v1.endpoints',
  'api.v1.endpoints.analysis',
  'api.v1.endpoints.history',
  'api.v1.endpoints.stocks',
  'api.v1.endpoints.health',
  'api.v1.endpoints.alphasift',
  'alphasift',
  'alphasift.dsa_adapter',
  'api.v1.schemas',
  'api.v1.schemas.analysis',
  'api.v1.schemas.history',
  'api.v1.schemas.stocks',
  'api.v1.schemas.common',
  'api.middlewares',
  'api.middlewares.error_handler',
  'src.services',
  'src.application.runtime.task_queue',
  'src.application.analysis.analysis_service',
  'src.application.history.read_model',
  'src.application.analysis.alphasift_service',
  'src.bootstrap',
  'src.bootstrap.environment',
  'src.bootstrap.logging_setup',
  'src.bootstrap.scheduling',
  'src.bootstrap.api_lifecycle',
  'src.bootstrap.serve',
  'uvicorn.logging',
  'uvicorn.loops',
  'uvicorn.loops.auto',
  'uvicorn.protocols',
  'uvicorn.protocols.http',
  'uvicorn.protocols.http.auto',
  'uvicorn.protocols.websockets',
  'uvicorn.protocols.websockets.auto',
  'uvicorn.lifespan',
  'uvicorn.lifespan.on'
)
$hiddenImportArgs = $hiddenImports | ForEach-Object { "--hidden-import=$_" }

$pyInstallerArgs = @(
  '-m', 'PyInstaller',
  '--name', 'stock_analysis',
  '--onedir',
  '--noconfirm',
  '--noconsole',
  # --distpath：最终产物落到 dist-desktop\backend\stock_analysis。
  # --workpath/--specpath：中间产物收纳到 dist-desktop\.work 与 dist-desktop\.specs（隐藏目录，不被 extraResources 取用）。
  # 前端不再烤入包：桌面 frontend 由 build-desktop 从 dist-web 复制到 dist-desktop\frontend，经 Electron extraResources 外置。
  # 注：PyInstaller 6.x 在 --specpath 下会按 spec 目录解析 --add-data 的相对源路径，故此处必须用绝对路径。
  '--distpath', 'dist-desktop\backend',
  '--workpath', 'dist-desktop\.work',
  '--specpath', 'dist-desktop\.specs',
  '--add-data', "$repoRoot\strategies;strategies",
  '--collect-data', 'litellm',
  '--collect-data', 'tiktoken',
  '--collect-data', 'akshare',
  '--collect-all', 'alphasift',
  '--collect-all', 'futu'
)
$pyInstallerArgs += $hiddenImportArgs
$pyInstallerArgs += 'main.py'

Write-Host "Running: $pythonBin $($pyInstallerArgs -join ' ')"
& $pythonBin @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE."
}

if (!(Test-Path 'dist-desktop\backend\stock_analysis')) {
  throw 'PyInstaller finished but dist-desktop\backend\stock_analysis was not generated.'
}

Write-Host 'Verifying packaged runtime imports...'
$packagedEntry = Join-Path 'dist-desktop\backend\stock_analysis' 'stock_analysis.exe'
if (-not (Test-Path $packagedEntry)) {
  throw "Packaged backend entrypoint not found: $packagedEntry"
}
$previousProbe = $env:HRS_PACKAGED_IMPORT_PROBE
try {
  foreach ($module in @('alphasift.dsa_adapter', 'futu', 'orjson')) {
    $env:HRS_PACKAGED_IMPORT_PROBE = $module
    $probeProcess = Start-Process -FilePath $packagedEntry -Wait -PassThru
    if ($probeProcess.ExitCode -ne 0) {
      throw "Packaged backend cannot import $module; probe exited with code $($probeProcess.ExitCode)."
    }
  }
} finally {
  if ($null -eq $previousProbe) {
    Remove-Item Env:HRS_PACKAGED_IMPORT_PROBE -ErrorAction SilentlyContinue
  } else {
    $env:HRS_PACKAGED_IMPORT_PROBE = $previousProbe
  }
}

Write-Host 'Verifying packaged AkShare calendar data...'
$packagedAkshareCalendar = Join-Path 'dist-desktop\backend\stock_analysis' '_internal\akshare\file_fold\calendar.json'
if (-not (Test-Path $packagedAkshareCalendar)) {
  $packagedAkshareCalendar = Join-Path 'dist-desktop\backend\stock_analysis' 'akshare\file_fold\calendar.json'
}
if (-not (Test-Path $packagedAkshareCalendar)) {
  throw 'Packaged AkShare calendar data not found under dist-desktop\backend\stock_analysis.'
}

Write-Host 'Verifying packaged built-in strategies...'
$sourceStrategyCount = @(Get-ChildItem -Path 'strategies' -Filter '*.yaml' -File).Count
$packagedStrategies = Join-Path 'dist-desktop\backend\stock_analysis' '_internal\strategies'
if (-not (Test-Path $packagedStrategies)) {
  $packagedStrategies = Join-Path 'dist-desktop\backend\stock_analysis' 'strategies'
}
if (-not (Test-Path $packagedStrategies)) {
  throw 'Packaged strategies directory not found under dist-desktop\backend\stock_analysis.'
}
$packagedStrategyCount = @(Get-ChildItem -Path $packagedStrategies -Filter '*.yaml' -File).Count
if ($packagedStrategyCount -ne $sourceStrategyCount) {
  throw "Packaged strategies count mismatch: expected $sourceStrategyCount, got $packagedStrategyCount."
}

Write-Host 'Backend build completed.'
