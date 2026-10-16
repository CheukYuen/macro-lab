"""run_manifest.json：每次运行一份，记录数据来源、限制与产出的哈希。

    from macrolab import manifest
    manifest.write(run_dir, experiment="cn/2026-10-macro-report", data_source="choice",
                   status="DONE_WITH_LIMITS", information_cutoff="2026-10-16 A股收盘",
                   outputs=["../../reports/xxx-choice.md"], limits=["..."])

raw/ 下的文件和 outputs 自动补 sha256 与字节数；路径相对 run_dir。
"""
import hashlib
import json
from pathlib import Path

STATUSES = {"DONE", "DONE_WITH_LIMITS", "BLOCKED", "FAILED"}
REQUIRED = ("experiment", "data_source", "status", "information_cutoff")


def _file_entry(run_dir: Path, rel: str) -> dict:
    p = (run_dir / rel).resolve()
    return {"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}


def write(run_dir: Path, *, outputs: list[str] = (), **fields) -> Path:
    run_dir = Path(run_dir)
    missing = [k for k in REQUIRED if k not in fields]
    if missing:
        raise ValueError(f"manifest 缺字段 {missing}")
    if fields["status"] not in STATUSES:
        raise ValueError(f"status 只能是 {sorted(STATUSES)}")
    raw = sorted(str(p.relative_to(run_dir)) for p in (run_dir / "raw").rglob("*") if p.is_file()) \
        if (run_dir / "raw").is_dir() else []
    doc = {"run_id": run_dir.name, **fields,
           "raw": [_file_entry(run_dir, r) for r in raw],
           "outputs": [_file_entry(run_dir, o) for o in outputs]}
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path
