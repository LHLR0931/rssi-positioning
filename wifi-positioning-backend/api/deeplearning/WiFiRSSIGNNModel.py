import torch, torch.nn as nn, torch.nn.functional as F
from pytorch_lightning import LightningModule
from torch_geometric.nn import GCNConv, TAGConv, GraphConv

def dist2d(a, b):
    return torch.linalg.norm(a - b, dim=-1)

class GNNModule(LightningModule):
    def __init__(self, out_dim=2, modeType='GCNConv', in_features=20,
                 conv_out=(128, 64), learning_rate=1e-3, weight_decay=1e-4, drop=0.1,
                 y_mean=None, y_std=None):
        super().__init__()
        self.save_hyperparameters()
        conv_map = {'GCNConv': GCNConv, 'TAGConv': TAGConv, 'GraphConv': GraphConv}
        if modeType not in conv_map: raise ValueError(f"modeType must be {list(conv_map)}")
        C = conv_map[modeType]

        # Variable-depth: build as many conv+BN layers as len(conv_out)
        layers, bns, ch = [], [], in_features
        for out_ch in conv_out:
            layers.append(C(ch, out_ch))
            bns.append(nn.BatchNorm1d(out_ch))
            ch = out_ch
        self.convs = nn.ModuleList(layers)
        self.bns   = nn.ModuleList(bns)
        self.drop  = nn.Dropout(drop)
        self.fc    = nn.Linear(ch, out_dim)
        self.loss_fn = nn.SmoothL1Loss()

    def forward(self, batch):
        x, ei = batch.x, batch.edge_index
        for conv, bn in zip(self.convs, self.bns):
            x = F.relu(bn(conv(x, ei)))
        x = self.drop(x)
        return self.fc(x)              # [N,2]

    # ---- steps with useful metrics ----
    def _step(self, batch, stage):
        pred = self(batch)
        y = batch.y
        loss = self.loss_fn(pred, y)

        # Denormalize to meters for interpretable distance metrics
        if self.hparams.y_std is not None:
            y_std = pred.new_tensor(self.hparams.y_std)
            y_mean = pred.new_tensor(self.hparams.y_mean)
            pred_m = pred * y_std + y_mean
            y_m    = y    * y_std + y_mean
        else:
            pred_m, y_m = pred, y

        e2d = dist2d(pred_m, y_m)                     # [N], in meters
        p2m = (e2d <= 2.0).float().mean()              # P@2m
        self.log(f'{stage}_loss', loss, on_epoch=True, prog_bar=True)
        self.log(f'{stage}_mae2d', e2d.mean(), on_epoch=True, prog_bar=(stage!='train'))
        self.log(f'{stage}_p@2m', p2m, on_epoch=True, prog_bar=(stage!='train'))
        return loss

    def training_step(self, batch, _):   return self._step(batch, 'train')
    def validation_step(self, batch, _): self._step(batch, 'val')
    def test_step(self, batch, _):       self._step(batch, 'test')

    def configure_optimizers(self):
        opt = torch.optim.Adam(self.parameters(), lr=self.hparams.learning_rate,
                               weight_decay=self.hparams.weight_decay)
        sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=0.5, patience=10)
        return {'optimizer': opt, 'lr_scheduler': {'scheduler': sch, 'monitor': 'val_loss'}}
