import sys
from pathlib import Path
from typing import Iterable
import torch
import pytorch_lightning as pl
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import TensorBoardLogger
import numpy as np

# ---------- Bootstrap: 把项目根目录（包含 api/ ）加入 sys.path ----------
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
except Exception:
    PROJECT_ROOT = Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ---------------------------------------------------------------------

from api.deeplearning.WiFiRSSIGNNDataModule import WiFiRSSIGNNDataModule
from api.deeplearning.WiFiRSSIGNNModel import GNNModule


def train_gnn(
    batch_size: int = 4,
    num_workers: int = 0,              # Windows/CPU 建议 0；若是 Linux/GPU 可调大
    lr: float = 1e-3,
    max_epochs: int = 300,
    db_path: str = "db_new.sqlite3",
    distance_threshold: float = 1.0,   # 只连直接相邻点(1m)，避免全连接导致 over-smoothing
    modeType: str = "GCNConv",         # 1-hop/layer，比 TAGConv(2-hop) 扩散慢
    out_dim: int = 2,
    weight_decay: float = 1e-4,
    drop: float = 0.1,                 # 数据量少，dropout 不宜过大
    conv_out: tuple = (128, 64),       # 2 层，减少 over-smoothing
):
    # 1) 随机种子
    pl.seed_everything(42, workers=True)

    # 2) DataModule
    print("Using database:", db_path)

    dm = WiFiRSSIGNNDataModule(
        batch_size=batch_size,
        num_workers=num_workers,
        db_path=db_path,
        distance_threshold=distance_threshold,
    )
    # Lightning 会在 fit/test 内自动调用 setup，这里显式调用让属性（如 num_aps）可用
    dm.setup("fit")

    # 验证集是否有独立数据：若 val = train 则用 train_loss 做监控，避免过早停止
    val_is_train = dm.val_dataset is dm.train_dataset
    monitor_metric = "train_loss_epoch" if val_is_train else "val_loss"
    if val_is_train:
        print("[WARNING] val dataset empty — monitoring train_loss_epoch for early stopping. "
              "Run /api/wifidata/splitdata/ before training for better results.")

    # 3) Model
    model = GNNModule(
        out_dim=out_dim,
        modeType=modeType,
        in_features=dm.num_aps,
        conv_out=conv_out,
        learning_rate=lr,
        weight_decay=weight_decay,
        drop=drop,
        y_mean=dm.y_mean.tolist(),
        y_std=dm.y_std.tolist(),
    )

    # 4) 日志与回调
    Path("./gnn_checkpoints").mkdir(parents=True, exist_ok=True)
    Path("./logs").mkdir(parents=True, exist_ok=True)
    Path("./runs/gnn").mkdir(parents=True, exist_ok=True)

    ckpt = ModelCheckpoint(
        monitor=monitor_metric,
        mode="min",
        save_top_k=-1,
        dirpath="./gnn_checkpoints",
        filename="wifi-gnn-{epoch:02d}-{val_loss:.4f}",
        auto_insert_metric_name=False,
        save_last=True,
    )
    es = EarlyStopping(monitor=monitor_metric, mode="min", patience=15)
    lrm = LearningRateMonitor(logging_interval="epoch")
    logger = TensorBoardLogger(save_dir="./logs", name="wifi-rssi-gnn")

    # 5) 设备配置（Lightning 2.x 写法）
    accelerator = "cpu"
    devices = 1

    trainer = Trainer(
        accelerator=accelerator,
        devices=devices,
        default_root_dir="./runs/gnn",
        max_epochs=max_epochs,
        callbacks=[ckpt, es, lrm],
        gradient_clip_val=1.0,
        deterministic=True,
        logger=logger,
        log_every_n_steps=10,
        enable_progress_bar=True,
        # precision="16-mixed"  # 若需混合精度并且 GPU 支持，可取消注释
    )

    # 6) 训练与评测
    trainer.fit(model, datamodule=dm)

    # 尝试用最佳权重评测；若找不到 best.ckpt，回退为当前权重
    best_ckpt = ckpt.best_model_path if ckpt.best_model_path else "last"
    test_result = trainer.test(ckpt_path=best_ckpt, datamodule=dm)
    print("TEST:", test_result)

    return ckpt.best_model_path or ""


def resolve_compatible_checkpoint(model_path: str | Path) -> Path:
    candidate = Path(model_path)
    checkpoint_paths = [candidate]

    if candidate.parent.exists():
        checkpoint_paths.extend(
            sorted(
                candidate.parent.glob("last-v*.ckpt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        )

    seen = set()
    for ckpt_path in checkpoint_paths:
        ckpt_path = ckpt_path.resolve()
        if ckpt_path in seen or not ckpt_path.exists():
            continue
        seen.add(ckpt_path)

        checkpoint = torch.load(ckpt_path, map_location="cpu")
        hyper_parameters = checkpoint.get("hyper_parameters", {})
        state_dict = checkpoint.get("state_dict", {})
        # Support both old layout (bn1.*) and new ModuleList layout (bns.0.*)
        has_batch_norm = any(
            key.startswith("bn1.") or key.startswith("bns.") for key in state_dict
        )
        if hyper_parameters.get("in_features") and has_batch_norm:
            return ckpt_path

    raise FileNotFoundError(
        f"No compatible GNN checkpoint found near {candidate}. "
        "Expected a checkpoint with saved hyper_parameters and batch norm weights."
    )


def predict(model_path: str, rows: Iterable[dict], db_path: str | None = None) -> np.ndarray:
    if not rows:
        raise ValueError("rows must not be empty")

    resolved_db_path = Path(db_path) if db_path else (PROJECT_ROOT / "db_new.sqlite3")
    resolved_model_path = resolve_compatible_checkpoint(model_path)
    device = torch.device("cpu")

    dm = WiFiRSSIGNNDataModule(
        batch_size=1,
        num_workers=0,
        db_path=str(resolved_db_path),
    )
    predict_loader = dm.predict_dataloader_from_rows(rows)

    model = GNNModule.load_from_checkpoint(str(resolved_model_path), map_location=device)
    model.to(device)
    model.eval()

    # Retrieve normalization stats saved in the checkpoint
    y_mean = np.array(model.hparams.y_mean or [0.0, 0.0], dtype=np.float32)
    y_std  = np.array(model.hparams.y_std  or [1.0, 1.0], dtype=np.float32)

    outputs = []
    with torch.no_grad():
        for batch in predict_loader:
            batch = batch.to(device)
            pred = model(batch)          # [N_nodes, 2] — in normalized coordinate space
            outputs.append(pred[batch.query_mask].detach().cpu().numpy())

    if not outputs:
        return np.empty((0, 2), dtype=float)

    pred_norm = np.concatenate(outputs, axis=0)
    return pred_norm * y_std + y_mean  # denormalize back to meters


if __name__ == "__main__":
    # 若需要命令行参数，可用 argparse；此处保留默认值即可直接运行
    # train_gnn()
    train_gnn(db_path=str(PROJECT_ROOT / "db_new.sqlite3"))
