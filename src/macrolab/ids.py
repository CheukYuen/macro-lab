"""指标 ID 表。ID 只从 docs/data-ids/*.csv 读，不在脚本里写死。

    from macrolab import ids
    ids.select("choice-edb", region="CN", dimension="国债")

核对 CSV 与同名 .md 说明里的 ID 一致：uv run python -m macrolab.ids --check
"""
import csv
import re
import sys

from macrolab import DATA_IDS


def load(table: str = "choice-edb") -> list[dict]:
    with (DATA_IDS / f"{table}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def select(table: str = "choice-edb", *, region=None, dimension=None, frequency=None,
           usable_only: bool = True) -> list[str]:
    """按条件取 ID。usable_only 时排除停更（discontinued）与取数无数据（no_data）。"""
    out = []
    for r in load(table):
        if region and r["region"] != region:
            continue
        if dimension and r["dimension"] != dimension:
            continue
        if frequency and r["frequency"] != frequency:
            continue
        if usable_only and r["status"] != "ok":
            continue
        out.append(r["id"])
    return out


def lookup(table: str = "choice-edb") -> dict[str, dict]:
    return {r["id"]: r for r in load(table)}


def check(table: str = "choice-edb") -> list[str]:
    """返回 CSV 与 .md 主表之间不一致的 ID；空列表表示一致。"""
    csv_ids = {r["id"] for r in load(table)}
    md = (DATA_IDS / f"{table}.md").read_text(encoding="utf-8")
    body = md.split("## 查询失败")[0]
    md_ids = set()
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.fullmatch(r"E[A-Z0-9]+", cells[2]):
            md_ids.add(cells[2])
    return sorted((csv_ids - md_ids) | (md_ids - csv_ids))


if __name__ == "__main__":
    if "--check" in sys.argv:
        diff = check()
        print("OK" if not diff else f"MISMATCH {diff}")
        sys.exit(1 if diff else 0)
