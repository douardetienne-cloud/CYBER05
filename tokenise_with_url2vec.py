tokenize_with_url2vec.py
-------------------------

import argparse
import sys
import csv
import tempfile
import re
import pandas as pd
from pathlib import Path

# ARGUMENTS
parser = argparse.ArgumentParser(description="URL tokenization via url2vec (robust).")
parser.add_argument("input_csv", help="Input CSV with a 'url' column")
parser.add_argument("output_csv", help="Output CSV (id,url,tokens)")
parser.add_argument("--url2vec-path", required=True,
                    help="Path to the url2vec package (e.g., ~/third_party/url2vec or ~/third_party/url2vec/url2vec)")
args = parser.parse_args()

in_csv = Path(args.input_csv)
out_csv = Path(args.output_csv)
u2v_root = Path(args.url2vec_path).expanduser().resolve()

if not in_csv.exists():
    print(f"[ERROR] Input file not found: {in_csv}")
    sys.exit(1)
if not u2v_root.exists():
    print(f"[ERROR] url2vec folder not found: {u2v_root}")
    sys.exit(1)

# IMPORT url2vec
candidates = []
if (u2v_root / "url2vec").is_dir():
    candidates += [u2v_root, u2v_root / "url2vec"]
else:
    candidates += [u2v_root]

for c in candidates:
    sys.path.append(str(c))

# By default, everything is set to None
seq_mod = None
get_sequences = None
tokenize_fn = None

try:
    import url2vec.util.seqmanager as seq_mod  # type: ignore
    # available functions depending on repository version
    get_sequences = getattr(seq_mod, "get_sequences", None)
    # some versions provide tokenize / tokenize_url / tokens_from_url, etc.
    for name in ("tokenize", "tokenize_url", "tokens_from_url"):
        if hasattr(seq_mod, name):
            tokenize_fn = getattr(seq_mod, name)
            break
except Exception as e:
    print("[WARN] Failed to import url2vec.util.seqmanager:", e)
    print("→ A local fallback will be used if necessary.")

# READ CSV
df = pd.read_csv(in_csv)
if 'url' not in df.columns:
    print("[ERROR] Column 'url' is missing from the CSV.")
    sys.exit(1)

urls = df['url'].dropna().astype(str).tolist()
print(f"[INFO] Reading: {len(urls)} URLs from {in_csv}")

# MODE 1: get_sequences(filename)
token_sequences = []

def try_get_sequences_from_file(url_list):
    """Write a temporary file of URLs and call get_sequences(path)"""
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmpf:
        tmp_path = Path(tmpf.name)
        for u in url_list:
            tmpf.write(u.strip() + "\n")
    try:
        print(f"[INFO] Tokenization via get_sequences({tmp_path}) ...")
        seqs = list(get_sequences(str(tmp_path)))  # force full reading
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    return seqs

used_mode = None
if callable(get_sequences):
    try:
        token_sequences = try_get_sequences_from_file(urls)
        if len(token_sequences) == len(urls) and len(token_sequences) > 0:
            used_mode = "get_sequences(file)"
        else:
            print(f"[WARN] get_sequences returned {len(token_sequences)} sequences for {len(urls)} URLs.")
            token_sequences = []
    except Exception as e:
        print("[WARN] get_sequences(file) failed:", e)
        token_sequences = []

# MODE 2: URL-by-URL tokenization
if not token_sequences:
    if callable(tokenize_fn):
        print("[INFO] Switching to URL-by-URL tokenization via url2vec.util.seqmanager …")
        seqs = []
        for u in urls:
            try:
                toks = tokenize_fn(u)  # depending on the repository signature; often returns a list of tokens
                # normalize
                if isinstance(toks, str):
                    toks = toks.split()
                elif toks is None:
                    toks = []
                seqs.append(list(toks))
            except Exception:
                seqs.append([])
        token_sequences = seqs
        used_mode = "url2vec.tokenize_* per-url"

# MODE 3: Local fallback (regex split)
if not token_sequences:
    print("[INFO] Local fallback: regex split on / ? = & - _ . :")
    SPLIT_RE = re.compile(r'[\/\?\=\&\-\_\.\:]+')
    seqs = []
    for u in urls:
        parts = [p for p in SPLIT_RE.split(u) if p]
        seqs.append(parts)
    token_sequences = seqs
    used_mode = "fallback-regex"

assert len(token_sequences) == len(urls), f"Unexpected number of sequences: {len(token_sequences)} != {len(urls)}"

# --------------------- OUTPUT CSV WRITING ---------------------
out_csv.parent.mkdir(parents=True, exist_ok=True)
with out_csv.open("w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["id", "url", "tokens"])
    for i, (u, seq) in enumerate(zip(urls, token_sequences)):
        toks = " ".join(seq) if isinstance(seq, (list, tuple)) else str(seq)
        w.writerow([i, u, toks])

print(f"[OK] Tokenization completed (mode: {used_mode}). Output: {out_csv}")
