import json
import csv
from collections import defaultdict
import os
import pandas as pd
from api.models import WiFiData

MIN_AP_COVERAGE = 0.3  # AP must appear in at least 30% of all locations to be kept


def filter_stable_aps(data, min_coverage=MIN_AP_COVERAGE):
    """
    Returns sorted list of BSSIDs that appear in at least min_coverage fraction
    of all distinct (x, y) locations. Drops roaming / rare APs.
    """
    locations = set((d['x'], d['y']) for d in data)
    n_locations = len(locations)
    if n_locations == 0:
        return []

    bssid_locs = defaultdict(set)
    for d in data:
        bssid = (d['bssid'] or '').lower().strip()
        bssid_locs[bssid].add((d['x'], d['y']))

    min_count = max(1, int(n_locations * min_coverage))
    return sorted(b for b, locs in bssid_locs.items() if len(locs) >= min_count)
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def calculate_average_rssi(data):
    # Collect all rssi values for the same bssid at the same location using (bssid, x, y) as the key
    rssi_values = defaultdict(list)
    for entry in data:
        key = (entry['bssid'], entry['x'], entry['y'])
        rssi_values[key].append(entry['rssi'])
    # calculate average
    average_rssi = {key: sum(values)/len(values) for key, values in rssi_values.items()}
    return average_rssi

def generate_fingerprint_vector(unique_bssids, average_rssi):
    bssid_to_index = {bssid: index for index, bssid in enumerate(unique_bssids)}
    # prepare mappings of locations and corresponding fingerprint vectors
    fingerprint_vectors = defaultdict(lambda: [0] * len(unique_bssids))
    # fill vectors
    for key, rssi in average_rssi.items():
        bssid, x, y = key
        index = bssid_to_index[bssid]
        fingerprint_vectors[(x, y)][index] = rssi
    return fingerprint_vectors

def write_to_csv(fingerprint_vectors, unique_bssids):
    with open(os.getcwd()+'/dataset/wifi_fingerprint.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # write the header
        writer.writerow(['x', 'y'] + unique_bssids)
       # Write the data for each row
        for position, vector in fingerprint_vectors.items():
            writer.writerow([position[0], position[1]] + vector)

def fingerprint_vectors_to_dataframe(fingerprint_vectors, unique_bssids):
    data_rows = []
    for position, rssi_vector in fingerprint_vectors.items():
        x, y = position
        row = [x, y] + rssi_vector
        data_rows.append(row)
    columns = ['x', 'y'] + unique_bssids
    df = pd.DataFrame(data_rows, columns=columns)
    
    return df

def main():
    data = get_fingerprint(0)
    average_rssi = calculate_average_rssi(data)
     # Get all unique BSSIDs and sort them
    all_unique_bssids = sorted(WiFiData.objects.values_list('bssid', flat=True).distinct())

    fingerprint_vectors = generate_fingerprint_vector(all_unique_bssids, average_rssi)
    write_to_csv(fingerprint_vectors, all_unique_bssids)
    print('A CSV file has been generated')

def get_fingerprint(data_type=0, min_ap_coverage=MIN_AP_COVERAGE):
    """data_type: 0=train, 1=val, 2=test. Returns (DataFrame, stable_bssids)."""
    if data_type not in [0, 1, 2]:
        raise ValueError('data_type must be 0, 1, or 2')

    data = WiFiData.objects.filter(data_type=data_type).values('bssid', 'rssi', 'x', 'y')
    print('data_size', len(data))

    # Determine stable APs from the full dataset (all data_types)
    all_data = list(WiFiData.objects.values('bssid', 'x', 'y'))
    stable_bssids = filter_stable_aps(all_data, min_coverage=min_ap_coverage)

    if not stable_bssids:
        # Fallback: keep everything
        stable_bssids = sorted(set(
            (b or "").lower().strip()
            for b in WiFiData.objects.values_list('bssid', flat=True).distinct()
        ))

    total_bssids = WiFiData.objects.values_list('bssid', flat=True).distinct().count()
    print(f'[AP Filter] {total_bssids} total BSSIDs → {len(stable_bssids)} stable '
          f'(coverage >= {min_ap_coverage*100:.0f}% of locations)')

    average_rssi = calculate_average_rssi(data)
    fingerprint_vectors = generate_fingerprint_vector(stable_bssids, average_rssi)
    df = fingerprint_vectors_to_dataframe(fingerprint_vectors, stable_bssids)
    print('df shape', df.shape)

    return df, stable_bssids

def create_prediction_vector(averaged_wifi_data, unique_bssids):
    '''Create a prediction vector from the averaged WiFi data and unique BSSIDs'''
    # Create a dictionary with BSSID as key and RSSI as value
    rssi_dict = {str(data['bssid']): data['rssi'] for data in averaged_wifi_data}

    # Extract the RSSI value from rssi_dict using the order unique_bssids and fill it with 0 if a certain BSSID doesn't exist
    rssi_values = [rssi_dict.get(str(bssid), 0) for bssid in unique_bssids]

    # Create a new DataFrame with the rssi_values
    X_pred = pd.DataFrame([rssi_values], columns=[str(bssid) for bssid in unique_bssids])
    print('----------------------', X_pred)

    return X_pred


if __name__ == '__main__':
    get_fingerprint()
    # main()