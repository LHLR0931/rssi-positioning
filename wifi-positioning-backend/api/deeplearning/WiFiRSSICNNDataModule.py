import os
import json
from collections import defaultdict
import torch
from torch.utils.data import Dataset, DataLoader
from pytorch_lightning import LightningDataModule
import sqlite3

class WiFiRSSICNNDataModule(LightningDataModule):
    def __init__(self, batch_size=32, num_workers=4,db_path='path_to_your_database.db'):
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.db_path = db_path
        print("当前 DataModule 使用的数据库路径:", db_path)


        self.setup()

    def setup(self, stage=None):
        #  data type 0 = training, 1 = validation, 2 = test
        # Load and preprocess data
        self.train_dataset = self.get_dateset(data_type= 0)
        self.val_dataset = self.get_dateset(data_type = 1)
        self.test_dataset = self.get_dateset(data_type = 2)
        print("Train dataset size: ", len(self.train_dataset))
        print("Validation dataset size: ", len(self.val_dataset))
        print("Test dataset size: ", len(self.test_dataset))


    def get_dateset(self,data_type):
        if data_type not in [0,1,2]:
            raise ValueError('dataType should be 0 or 1 or 2')
        data = self.fetch_wifi_data(data_type)
        print(len(data))
        average_rssi = self.calculate_average_rssi(data)
        fingerprint_vectors = self.generate_fingerprint_vector(data, average_rssi)
        unique_bssids = self.fetch_unique_bssids()
        print('unique_bssids',len(unique_bssids))
        self.dataset = self.fingerprint_vectors_to_dataset(fingerprint_vectors, unique_bssids)
        return self.dataset
    
    def fetch_wifi_data(self,data_type):
        
        conn = sqlite3.connect(self.db_path)
        print(self.db_path)
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT bssid, rssi, x, y FROM api_wifidata WHERE data_type=?
        ''', (data_type,))
        
        rows = cursor.fetchall()
        data = [dict(row) for row in rows] 
        
        cursor.close()
        conn.close()
        
        # 返回结果
        return rows
    
    def fetch_unique_bssids(self, min_coverage=0.3):
        """Return BSSIDs that appear in at least min_coverage fraction of all locations."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT bssid, x, y FROM api_wifidata')
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()

        locations = set((r['x'], r['y']) for r in rows)
        n_locations = len(locations)
        if n_locations == 0:
            return []

        bssid_locs = defaultdict(set)
        for r in rows:
            bssid_locs[(r['bssid'] or '').strip()].add((r['x'], r['y']))

        min_count = max(1, int(n_locations * min_coverage))
        stable = sorted(b for b, locs in bssid_locs.items() if len(locs) >= min_count)

        if not stable:
            stable = sorted(bssid_locs.keys())

        print(f'[CNN AP Filter] {len(bssid_locs)} BSSIDs → {len(stable)} stable '
              f'(>= {min_coverage*100:.0f}% of {n_locations} locations)')
        return stable



    def read_json_file(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)

    def calculate_average_rssi(self,data):
        # Collect all rssi values for the same bssid at the same location using (bssid, x, y) as the key
        rssi_values = defaultdict(list)
        for entry in data:
            key = (entry['bssid'], entry['x'], entry['y'])
            rssi_values[key].append(entry['rssi'])
        # calculate average
        average_rssi = {key: sum(values)/len(values) for key, values in rssi_values.items()}
        return average_rssi

    def generate_fingerprint_vector(self,data, average_rssi):
        # Get all unique BSSIDs and sort them
        unique_bssids = sorted({entry['bssid'] for entry in data})
        # prepare mappings of locations and corresponding fingerprint vectors
        fingerprint_vectors = defaultdict(lambda: [0] * len(unique_bssids))
        # fill vectors
        for key, rssi in average_rssi.items():
            bssid, x, y = key
            index = unique_bssids.index(bssid)
            fingerprint_vectors[(x, y)][index] = rssi
        return fingerprint_vectors

    def fingerprint_vectors_to_dataset(self, fingerprint_vectors, unique_bssids):
        # Convert fingerprint vectors to PyTorch Dataset
        data_rows = []
        for position, rssi_vector in fingerprint_vectors.items():
            x, y = position
            row = [x, y] + rssi_vector
            data_rows.append(row)

        dataset = WiFiRSSIDataset(data_rows, unique_bssids)
        return dataset



    def train_dataloader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size, num_workers=self.num_workers, shuffle=True,persistent_workers=True)

    def val_dataloader(self):
        return DataLoader(self.val_dataset, batch_size=self.batch_size, num_workers=self.num_workers, shuffle=False,persistent_workers=True)

    def test_dataloader(self):
        return DataLoader(self.test_dataset, batch_size=self.batch_size, num_workers=self.num_workers, shuffle=False,persistent_workers=True)
    

    

class WiFiRSSIDataset(Dataset):
    def __init__(self, data_rows, unique_bssids):
        self.data = torch.tensor([row for row in data_rows], dtype=torch.float32)
        self.unique_bssids = unique_bssids

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        x = self.data[idx, 2:].clone()
        y = self.data[idx, :2].clone()
        return x, y