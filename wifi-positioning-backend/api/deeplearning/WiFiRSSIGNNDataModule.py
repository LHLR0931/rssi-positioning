import math
import sqlite3, torch, numpy as np
from collections import defaultdict
from pytorch_lightning import LightningDataModule
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader as GeoDataLoader
# from torch_geometric.nn import radius_graph
import torch_geometric.transforms as T
from torch_geometric.utils import add_self_loops

DEFAULT_RSSI = -100.0
_RSSI_MIN = -100.0
_RSSI_MAX = 0.0

class WiFiRSSIGNNDataModule(LightningDataModule):
    def __init__(self, batch_size=32, num_workers=4, db_path='db.sqlite3',
                 distance_threshold=6.0, transform=None, max_scans_per_location=None):
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.db_path = db_path
        self.distance_threshold = float(distance_threshold)
        self.max_scans_per_location = max_scans_per_location
        # NormalizeFeatures removed: absent APs all have DEFAULT_RSSI=-100, which dominates
        # the L1 norm and makes all location vectors look nearly identical after normalization.
        # RSSI is now normalized per-AP in fp_vector() using known physical bounds [-100, 0].
        self.transform = transform or T.Compose([
            T.ToUndirected(), T.AddSelfLoops()
        ])

        self.unique_bssids = self.fetch_unique_bssids()
        self.bssid2idx = {b: i for i, b in enumerate(self.unique_bssids)}
        self.num_aps = len(self.unique_bssids)
        self.y_mean, self.y_std = self._compute_y_stats()

    # -------- reading & preprocessing --------
    def fetch_unique_bssids(self, min_coverage=0.3):
        """Return BSSIDs that appear in at least min_coverage fraction of all locations."""
        conn = sqlite3.connect(self.db_path); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT bssid, x, y FROM api_wifidata')
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()

        locations = set((r['x'], r['y']) for r in rows)
        n_locations = len(locations)
        if n_locations == 0:
            return []

        bssid_locs = defaultdict(set)
        for r in rows:
            bssid_locs[(r['bssid'] or '').lower().strip()].add((r['x'], r['y']))

        min_count = max(1, int(n_locations * min_coverage))
        stable = sorted(b for b, locs in bssid_locs.items() if len(locs) >= min_count)

        if not stable:
            stable = sorted(bssid_locs.keys())

        print(f'[GNN AP Filter] {len(bssid_locs)} BSSIDs → {len(stable)} stable '
              f'(>= {min_coverage*100:.0f}% of {n_locations} locations)')
        return stable

    def fetch_wifi_data(self, data_type):
        conn = sqlite3.connect(self.db_path); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT rowid AS row_no, bssid, rssi, x, y FROM api_wifidata WHERE data_type=? ORDER BY rowid', (data_type,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows

    def build_scan_samples(self, rows):
        grouped = defaultdict(lambda: defaultdict(list))
        for r in rows:
            loc = (float(r['x']), float(r['y']))
            grouped[loc][(r['bssid'] or '').lower().strip()].append(float(r['rssi']))

        samples = []
        for loc, bssid_values in grouped.items():
            counts = sorted(len(values) for values in bssid_values.values())
            if not counts:
                continue

            scan_count = int(round(np.median(counts)))
            scan_count = max(scan_count, 1)
            if self.max_scans_per_location is not None:
                scan_count = min(scan_count, int(self.max_scans_per_location))

            scan_maps = [dict() for _ in range(scan_count)]
            for bssid, values in bssid_values.items():
                if len(values) <= scan_count:
                    for idx, value in enumerate(values):
                        scan_maps[idx][bssid] = value
                else:
                    chunk_size = len(values) / scan_count
                    for idx in range(scan_count):
                        start = int(math.floor(idx * chunk_size))
                        end = int(math.floor((idx + 1) * chunk_size))
                        chunk = values[start:max(end, start + 1)]
                        scan_maps[idx][bssid] = float(sum(chunk) / len(chunk))

            for scan_map in scan_maps:
                if scan_map:
                    samples.append((loc, scan_map))

        return samples

    def fp_vector(self, bssid_rssi_dict):
        v = [DEFAULT_RSSI] * self.num_aps
        for b, r in bssid_rssi_dict.items():
            key = (b or '').lower().strip()
            if key in self.bssid2idx:
                v[self.bssid2idx[key]] = r
        # Normalize RSSI to [0, 1]: absent AP (-100) → 0.0, strongest (0 dBm) → 1.0
        return [(val - _RSSI_MIN) / (_RSSI_MAX - _RSSI_MIN) for val in v]

    def _compute_y_stats(self):
        """Compute mean and std of (x, y) coordinates across all data for target normalization."""
        conn = sqlite3.connect(self.db_path); conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT x, y FROM api_wifidata')
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()

        if not rows:
            return np.array([0.0, 0.0], dtype=np.float32), np.array([1.0, 1.0], dtype=np.float32)

        coords = np.array([(float(r['x']), float(r['y'])) for r in rows], dtype=np.float32)
        mean = coords.mean(axis=0)
        std = coords.std(axis=0)
        std = np.where(std < 1e-6, 1.0, std)  # avoid division by zero if all coords identical
        print(f'[GNN y-stats] mean={mean}, std={std}')
        return mean, std

    def build_rssi_knn_edge_index(self, x: torch.Tensor, k: int) -> torch.Tensor:
        """Build k-NN graph in RSSI feature space. Training and inference use the same structure."""
        n = x.size(0)
        k = min(k, n - 1)
        if n <= 1 or k == 0:
            ei, _ = add_self_loops(torch.empty(2, 0, dtype=torch.long), num_nodes=n)
            return ei
        dists = torch.cdist(x, x, p=2)
        topk_idx = torch.topk(dists, k + 1, largest=False).indices[:, 1:]  # exclude self
        src = torch.arange(n, dtype=torch.long).repeat_interleave(k)
        dst = topk_idx.reshape(-1)
        ei = torch.stack([src, dst], dim=0)
        ei, _ = add_self_loops(ei, num_nodes=n)
        return ei

    def make_graph(self, samples, k_neighbors=7):
        if len(samples) == 0:
            print("[ERROR] Empty graph detected!")
            x = torch.zeros((1, self.num_aps), dtype=torch.float32)
            y = torch.zeros((1, 2), dtype=torch.float32)
            ei, _ = add_self_loops(torch.empty(2, 0, dtype=torch.long), num_nodes=1)
            return [Data(x=x, y=y, edge_index=ei)]

        print(f"[DEBUG] number of scan samples = {len(samples)}")
        x = torch.tensor([self.fp_vector(scan_map) for _, scan_map in samples], dtype=torch.float32)
        y_raw = torch.tensor([loc for loc, _ in samples], dtype=torch.float32)
        pos = y_raw.clone()

        # Edges in RSSI feature space — same structure as predict_dataloader_from_rows,
        # eliminating the train/inference graph mismatch that caused mean collapse.
        ei = self.build_rssi_knn_edge_index(x, k=k_neighbors)

        y_mean_t = torch.tensor(self.y_mean, dtype=torch.float32)
        y_std_t = torch.tensor(self.y_std, dtype=torch.float32)
        y = (y_raw - y_mean_t) / y_std_t

        data = Data(x=x, y=y, pos=pos, edge_index=ei)
        if self.transform: data = self.transform(data)
        return [data]

    # def get_dataset(self, data_type):
    #     raw = self.fetch_wifi_data(data_type)
    #     avg = self.calculate_average_rssi(raw)
    #     fp_map = {loc: self.fp_vector(bssid_rssi) for loc, bssid_rssi in avg.items()}
    #     return self.make_graph(fp_map)
    def get_dataset(self, data_type):
        print(f"\n[DEBUG] loading data_type = {data_type}")
    
        raw = self.fetch_wifi_data(data_type)
        print(f"[DEBUG] raw rows = {len(raw)}")

        if len(raw) > 0:
            print("[DEBUG] first row =", raw[0])
        else:
            print("[DEBUG] No rows found for this data_type")

        samples = self.build_scan_samples(raw)
        print(f"[DEBUG] reconstructed scan samples = {len(samples)}")

        if len(samples) == 0:
            return []

        return self.make_graph(samples)

    # -------- PL hooks --------
    # def setup(self, stage=None):
    #     # if stage in (None, 'fit'):
    #     #     self.train_dataset = self.get_dataset(0)
    #     #     self.val_dataset   = self.get_dataset(1)
    #     if stage in (None, 'fit'):
    #         self.train_dataset = self.get_dataset(0)

    # # 如果val没有数据，就用train代替
    #         val_data = self.get_dataset(1)
    #         if len(val_data[0].x) == 0:
    #             print("[WARNING] val dataset empty, using train dataset instead")
    #             self.val_dataset = self.train_dataset
    #         else:
    #             self.val_dataset = val_data

    #     if stage in (None, 'test'):
    #         self.test_dataset  = self.get_dataset(2)
    #     print(f"[INFO] num_workers={self.num_workers}, persistent_workers={(self.num_workers > 0)}")
    #     print("DataModule using DB:", self.db_path)

    #     if hasattr(self, "train_dataset"):
    #         print("Train size:", len(self.train_dataset))
    #     if hasattr(self, "val_dataset"):
    #         print("Val size:", len(self.val_dataset))
    #     if hasattr(self, "test_dataset"):
    #         print("Test size:", len(self.test_dataset))
    def setup(self, stage=None):
        if stage in (None, 'fit'):
            self.train_dataset = self.get_dataset(0)

            val_data = self.get_dataset(1)
            if len(val_data) == 0 or len(val_data[0].x) == 0:
                print("[WARNING] val dataset empty, using train dataset instead")
                self.val_dataset = self.train_dataset
            else:
                self.val_dataset = val_data

        if stage in (None, 'test'):
            test_data = self.get_dataset(2)
            if len(test_data) == 0 or len(test_data[0].x) == 0:
                print("[WARNING] test dataset empty, using train dataset instead")
                self.test_dataset = self.train_dataset if hasattr(self, "train_dataset") else test_data
            else:
                self.test_dataset = test_data

        print(f"[INFO] num_workers={self.num_workers}, persistent_workers={(self.num_workers > 0)}")
        print("DataModule using DB:", self.db_path)

        if hasattr(self, "train_dataset"):
            print("Train size:", len(self.train_dataset))
        if hasattr(self, "val_dataset"):
            print("Val size:", len(self.val_dataset))
        if hasattr(self, "test_dataset"):
            print("Test size:", len(self.test_dataset))
    


    def train_dataloader(self):
        return GeoDataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=True,
            persistent_workers=(self.num_workers > 0)
        )

    def val_dataloader(self):
        return GeoDataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=False,
            persistent_workers=(self.num_workers > 0)
        )

    def test_dataloader(self):
        return GeoDataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            shuffle=False,
            persistent_workers=(self.num_workers > 0)
        )


    # -------- predict pipeline --------
    def predict_dataloader_from_rows(self, rows, k_neighbors: int = 7):
        """Build a combined RSSI-k-NN graph: training nodes + query node (last node).
        All edges are in RSSI feature space — same structure as make_graph() during training."""

        # 1. Build query fingerprint vector
        rssi_dict = defaultdict(list)
        for r in rows:
            rssi_dict[r['bssid']].append(float(r['rssi']))
        mean_dict = {b: sum(v) / len(v) for b, v in rssi_dict.items()}
        query_vec = self.fp_vector(mean_dict)

        # 2. Load training fingerprints
        train_rows = self.fetch_wifi_data(0)
        if not train_rows:
            x = torch.tensor([query_vec], dtype=torch.float32)
            y = torch.zeros(1, 2, dtype=torch.float32)
            ei, _ = add_self_loops(torch.empty(2, 0, dtype=torch.long), num_nodes=1)
            data = Data(x=x, y=y, edge_index=ei, query_mask=torch.tensor([True]))
            if self.transform:
                data = self.transform(data)
            return GeoDataLoader([data], batch_size=1, num_workers=0, shuffle=False)

        train_samples = self.build_scan_samples(train_rows)
        if not train_samples:
            x = torch.tensor([query_vec], dtype=torch.float32)
            y = torch.zeros(1, 2, dtype=torch.float32)
            ei, _ = add_self_loops(torch.empty(2, 0, dtype=torch.long), num_nodes=1)
            data = Data(x=x, y=y, edge_index=ei, query_mask=torch.tensor([True]))
            if self.transform:
                data = self.transform(data)
            return GeoDataLoader([data], batch_size=1, num_workers=0, shuffle=False)

        train_vecs = [self.fp_vector(scan_map) for _, scan_map in train_samples]
        train_locs = [list(loc) for loc, _ in train_samples]
        n_train = len(train_vecs)
        query_idx = n_train  # last node

        # 3. Build combined feature matrix and labels
        all_vecs = train_vecs + [query_vec]
        x = torch.tensor(all_vecs, dtype=torch.float32)
        y_train_raw = torch.tensor(train_locs, dtype=torch.float32)
        y_mean_t = torch.tensor(self.y_mean, dtype=torch.float32)
        y_std_t = torch.tensor(self.y_std, dtype=torch.float32)
        y_train = (y_train_raw - y_mean_t) / y_std_t
        y_query = torch.zeros(1, 2, dtype=torch.float32)  # placeholder
        y = torch.cat([y_train, y_query], dim=0)

        # 4. Build unified RSSI k-NN graph over ALL nodes (training + query)
        #    This matches make_graph() — no train/inference structure mismatch.
        ei = self.build_rssi_knn_edge_index(x, k=k_neighbors)

        query_mask = torch.zeros(len(all_vecs), dtype=torch.bool)
        query_mask[query_idx] = True
        data = Data(x=x, y=y, edge_index=ei, query_mask=query_mask)
        if self.transform:
            data = self.transform(data)
        return GeoDataLoader([data], batch_size=1, num_workers=0, shuffle=False)
