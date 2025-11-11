# Selection of 1 representative seed per cluster
# Input : CSV (id,url, url_tokens|tokens), NPZ (X, labels, centers)
# Output: JSON 

import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances_argmin_min  

if len(sys.argv) < 4:
    print("Usage: python select_representatives_git.py <data_tokens_csv> <features_npz> <out_json>")
    sys.exit(1)

csv_path = Path(sys.argv[1])
npz_path = Path(sys.argv[2])
out_path = Path(sys.argv[3])

# Load data
df = pd.read_csv(csv_path)
arr = np.load(npz_path, allow_pickle=True)
X = arr['X']             # (n_samples, n_features)
labels = arr['labels']   # (n_samples,)
centers = arr['centers'] # (k, n_features)

# Synchronize sizes if needed
if len(df) != len(labels):
    n = min(len(df), len(labels))
    df = df.iloc[:n].reset_index(drop=True)
    X = X[:n]
    labels = labels[:n]

# Tokens column 
tok_col = 'url_tokens' if 'url_tokens' in df.columns else ('tokens' if 'tokens' in df.columns else None)
if tok_col is None:
    print("[ERR] CSV must have 'url_tokens' or 'tokens'")
    sys.exit(2)

df['cluster'] = labels

# “closest-to-centroid” selection via scikit-learn
closest_idx, _ = pairwise_distances_argmin_min(centers, X)  # index du point le + proche par centroïde

# Output building
sizes = df.groupby('cluster').size().to_dict()
selected = []
for cluster_id, idx in enumerate(closest_idx):
    row = df.iloc[int(idx)]
    selected.append({
        "cluster": int(cluster_id),
        "id": int(row.get('id', -1)) if 'id' in row else None,
        "url": row.get('url', ''),
        "tokens": row.get(tok_col, ''),
        "_cluster_size": int(sizes.get(cluster_id, 0)),
    })

# JSON writing
out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", encoding="utf-8") as f:
    json.dump(selected, f, ensure_ascii=False, indent=2)

print(f"[OK] {len(selected)} representatives written in {out_path}")
