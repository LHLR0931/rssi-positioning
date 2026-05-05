param(
  [int]$BatchSize = 2,
  [int]$NumWorkers = 1,
  [int]$MaxEpochs = 500,
  [string]$LearningRate = "2e-4"
)

# 切到项目根目录
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $Root

# 使用 Django 实际数据库 db_new.sqlite3
$DB = Join-Path $Root "db_new.sqlite3"
if (-not (Test-Path $DB)) {
    Write-Error "db_new.sqlite3 not found at $DB. Make sure the Django server has been run at least once."
    exit 1
}

# 确保 checkpoint 目录存在（views.py 从 wifi-positioning-backend/cnn_checkpoints/ 加载）
New-Item -ItemType Directory -Force -Path "$Root\cnn_checkpoints" | Out-Null

# 进入训练脚本目录运行（CNNTrain.py 使用本地 import）
$PyDir = Join-Path $Root "api\deeplearning"
Set-Location $PyDir

python .\CNNTrain.py `
  --db_path "$DB" `
  --batch_size $BatchSize `
  --num_workers $NumWorkers `
  --max_epochs $MaxEpochs `
  --learning_rate $LearningRate

# 训练完成后把 checkpoint 复制到 views.py 查找的位置
Write-Host "Copying cnn_checkpoints to project root..."
$CkptSrc = Join-Path $PyDir "cnn_checkpoints"
$CkptDst = Join-Path $Root "cnn_checkpoints"
if (Test-Path $CkptSrc) {
    Copy-Item "$CkptSrc\last*.ckpt" "$CkptDst\" -Force
    Write-Host "Done. Checkpoints copied to $CkptDst"
} else {
    Write-Warning "No cnn_checkpoints found in $CkptSrc"
}
