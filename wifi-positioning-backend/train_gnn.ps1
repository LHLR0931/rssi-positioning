param(
  [int]$MaxEpochs = 200,
  [string]$LearningRate = "2e-3",
  [int]$BatchSize = 4,
  [float]$DistanceThreshold = 6.0,
  [string]$ModeType = "TAGConv"
)

$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location $Root

$DB = Join-Path $Root "db_new.sqlite3"
if (-not (Test-Path $DB)) {
    Write-Error "db_new.sqlite3 not found at $DB."
    exit 1
}

New-Item -ItemType Directory -Force -Path "$Root\gnn_checkpoints" | Out-Null

Write-Host "Starting GNN training..."
Write-Host "  DB: $DB"
Write-Host "  Epochs: $MaxEpochs  LR: $LearningRate  Mode: $ModeType"

python -c "
import sys, os
sys.path.insert(0, r'$Root')
os.chdir(r'$Root')
from api.deeplearning.GNNTrain import train_gnn
train_gnn(
    max_epochs=$MaxEpochs,
    lr=$LearningRate,
    batch_size=$BatchSize,
    distance_threshold=$DistanceThreshold,
    modeType='$ModeType',
    db_path=r'$DB',
)
"

Write-Host "GNN training complete. Checkpoint saved to gnn_checkpoints\last.ckpt"
