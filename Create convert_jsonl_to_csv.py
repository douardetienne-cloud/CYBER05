import json, csv, sys
from pathlib import Path
IN = Path(sys.argv[1])
OUT = Path(sys.argv[2])
with IN.open('r', encoding='utf-8') as fh, OUT.open('w', newline='', encoding='utf-8') as fo:
    w = csv.writer(fo)
    w.writerow(['id','url','title','excerpt','status','response_time_ms','has_form'])
    for i,line in enumerate(fh):
        try:
            obj = json.loads(line)
        except:
            continue
        w.writerow([
            i,
            obj.get('url',''),
            obj.get('title',''),
            obj.get('excerpt',''),
            obj.get('status',-1),
            obj.get('response_time_ms',0.0),
            int(bool(obj.get('has_form', False)))
        ])
