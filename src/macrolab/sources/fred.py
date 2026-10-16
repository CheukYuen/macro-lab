"""FRED 公开序列（无需凭据），例如美债 DGS2 / DGS10、联邦基金 DFF。"""
import urllib.request
from pathlib import Path

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"


def download(series_id: str, start: str, dest_dir: Path) -> Path:
    """把原始 CSV 原样存到 dest_dir/<series_id>.csv，不做清洗。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{series_id}.csv"
    with urllib.request.urlopen(URL.format(sid=series_id, start=start), timeout=30) as r:
        dest.write_bytes(r.read())
    return dest
