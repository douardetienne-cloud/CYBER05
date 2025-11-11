# Vectorisation (TF-IDF)/ Reduction (SVD) /Clustering (K-means)
# Use scikit-learnpen-source

import sys
from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import MiniBatchKMeans  # scalable
# from sklearn.cluster import KMeans

def main():
    if len(sys.argv) < 4:
        print("Usage: python run_kmeans_sklearn.py <input_tokens.csv> <k> <out_features.npz>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    k = int(sys.argv[2])
    out_path = Path(sys.argv[3])

    if not csv_path.exists():
        print(f"[ERR] File not found: {csv_path}")
        sys.exit(2)

    df = pd.read_csv(csv_path)
    if "tokens" not in df.columns:
        print("[ERR] Missing 'url_tokens' column in input CSV")
        sys.exit(3)

    # TF-IDF on URL's tokens 
    texts = df["tokens"].fillna("").astype(str).tolist()
    print("[STEP] TF-IDF vectorization ...")
    vec = TfidfVectorizer(max_features=10000, ngram_range=(1,2))
    X = vec.fit_transform(texts)  # matrice sparse

    # Reduction 
    n_comp = min(100, max(2, X.shape[1] - 1))
    print(f"[STEP] TruncatedSVD to {n_comp} dims ...")
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    X_red = svd.fit_transform(X)  # dense (n_samples, n_comp)

    # Clustering (MiniBatchKMean)
    print(f"[STEP] MiniBatchKMeans with k={k} ...")
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=1024)
    labels = kmeans.fit_predict(X_red)
    centers = kmeans.cluster_centers_

    # 4) back up
    np.savez(out_path, X=X_red, labels=labels, centers=centers)
    print(f"[OK] Saved: {out_path}  (X:{X_red.shape}, k:{k})")

if __name__ == "__main__":
    main()
