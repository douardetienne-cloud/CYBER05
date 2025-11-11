Usage :
  python detect_and_merge_git.py \
    --csv pipeline/tmp/data.tokens.csv \
    --npz pipeline/tmp/features.npz \
    --reps outputs/seeds_cluster_reps.json \
    --out outputs/seeds_selected.json \
    --top-anomalies 20 \
    --contamination 0.02
"""

import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

# GitHub code using scikit-learn: IsolationForest
from sklearn.ensemble import IsolationForest

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Tokenised CSV (id,url,(url_tokens|tokens), ...)")
    p.add_argument("--npz", required=True, help="features.npz (X, labels, centers)")
    p.add_argument("--reps", required=True, help="JSON representatives (step F)")
    p.add_argument("--out", required=True, help="Output JSON (final seeds)")
    p.add_argument("--top-anomalies", type=int, default=20, help="Number of anomalies to add")
    p.add_argument("--contamination", type=float, default=0.02, help="Presumed anomaly rate (IsolationForest)")
    return p.parse_args()

def main():
    args = parse_args()
    csv_path = Path(args.csv)
    npz_path = Path(args.npz)
    reps_path = Path(args.reps)
    out_path = Path(args.out)

    # Load data
    df = pd.read_csv(csv_path)
    arr = np.load(npz_path, allow_pickle=True)
    X = arr["X"]            # (n_samples, n_features)
    labels = arr["labels"]  # (n_samples,)
    # centers = arr["centers"]  # not needed here

    # Synchronize if necessary
    if len(df) != len(labels):
        n = min(len(df), len(labels))
        df = df.iloc[:n].reset_index(drop=True)
        X = X[:n]
        labels = labels[:n]

    # Token column (supports 'url_tokens' or 'tokens')
    tok_col = "url_tokens" if "url_tokens" in df.columns else ("tokens" if "tokens" in df.columns else None)
    if tok_col is None:
        raise SystemExit("[ERR] CSV must contain 'url_tokens' or 'tokens'.")

    # 2) IsolationForest
    print(f"[ANOM] IsolationForest (contamination={args.contamination}) …")
    iso = IsolationForest(
        n_estimators=200,
        contamination=args.contamination,
        random_state=42,
        n_jobs=-1
    )
    # decision_function: larger = more "normal", smaller = more "abnormal"
    iso.fit(X)
    scores = iso.decision_function(X)          # array shape (n_samples,)
    pred = iso.predict(X)                      # 1 = normal, -1 = anomaly
    df["_anomaly_pred"] = pred
    df["_anomaly_score"] = -scores             # invert: larger => more anomalous

    # 3) Load representatives and create a set to avoid duplicates
    with reps_path.open("r", encoding="utf-8") as fh:
        reps = json.load(fh)
    selected_urls = set([r.get("url","") for r in reps])

    # 4) Select top anomalies (excluding representatives)
    anomalies = df[df["_anomaly_pred"] == -1].copy()
    # Sort by anomaly score (descending, most anomalous first),
    # and fallback on response_time_ms if available.
    if "response_time_ms" in df.columns:
        anomalies["_rt"] = pd.to_numeric(anomalies["response_time_ms"], errors="coerce").fillna(0.0)
    else:
        anomalies["_rt"] = 0.0

    anomalies = anomalies.sort_values(["_anomaly_score", "_rt"], ascending=[False, False])

    topN = max(0, args["top_anomalies"] if isinstance(args, dict) else args.top_anomalies)
    add_list = []
    for _, row in anomalies.iterrows():
        if len(add_list) >= topN:
            break
        url = row.get("url", "")
        if not url or url in selected_urls:
            continue
        add_list.append({
            "cluster": int(row.name if "cluster" in row else -1),  # cluster not essential here
            "id": int(row.get("id", -1)) if "id" in row else None,
            "url": url,
            "tokens": row.get(tok_col, ""),
            "_anomaly": 1
        })
        selected_urls.add(url)

    print(f"[ANOM] Added {len(add_list)} anomalies to {len(reps)} representatives.")

    # 5) Scoring / prioritization
    # We combine: anomaly, has_form, status>=400, response_time_ms, and a bonus if representative
    # (Columns may be missing: we handle defaults.)
    def to_num(s):
        try:
            return float(s)
        except Exception:
            return 0.0

    def score_entry(e):
        # Find the corresponding row in df to enrich
        row = df[df["url"] == e["url"]].head(1)
        has_form = int(row["has_form"].iloc[0]) if "has_form" in df.columns and not row.empty else 0
        status = int(row["status"].iloc[0]) if "status" in df.columns and not row.empty else -1
        rt = to_num(row["response_time_ms"].iloc[0]) if "response_time_ms" in df.columns and not row.empty else 0.0

        anomaly_bonus = 2.0 if e.get("_anomaly", 0) == 1 else 0.0
        error_bonus = 1.5 if status >= 400 else 0.0
        form_bonus = 1.5 if has_form == 1 else 0.0
        rt_bonus = min(rt / 1000.0, 2.0)  # rough normalization (<= 2)

        base = 1.0  # all seeds start at 1
        return base + anomaly_bonus + error_bonus + form_bonus + rt_bonus

    final = []
    # Mark representatives
    for r in reps:
        r = dict(r)
        r["_anomaly"] = 0
        r["_score"] = score_entry(r)
        final.append(r)
    # Add anomalies
    for a in add_list:
        a = dict(a)
        a["_score"] = score_entry(a)
        final.append(a)

    final_sorted = sorted(final, key=lambda x: x["_score"], reverse=True)

    # Write output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(final_sorted, fh, ensure_ascii=False, indent=2)

    print(f"[OK] {len(final_sorted)} final seeds written → {out_path}")

if __name__ == "__main__":
    main()
