"""Choice 量化 API（EMQuantAPI）取数。

一次登录内完成全部取数：同一账号在别处登录会报 10001009，中途断开要整批重来。

    from macrolab.sources import choice
    with choice.session() as c:
        edb = choice.edb(c, ids, "2024-09-01", "2026-10-16")
        closes = choice.closes(c, ["000300.SH"], "2026-06-01", "2026-10-16")

SDK 由 .agents/skills/choice-quantapi-skill 安装在 ~/.choice/，不在 uv 环境里，这里按路径导入。
"""
import json
import sys
from contextlib import contextmanager
from itertools import groupby
from pathlib import Path

SDK_DIR = Path.home() / ".choice" / "EMQuantAPI_Python" / "python3"


def _import_c():
    try:
        from EmQuantAPI import c
    except ImportError:
        sys.path.append(str(SDK_DIR))
        from EmQuantAPI import c
    return c


@contextmanager
def session():
    c = _import_c()
    login = c.start()
    if login.ErrorCode != 0:
        raise RuntimeError(f"Choice LOGIN_FAILED {login.ErrorCode} {login.ErrorMsg}")
    try:
        yield c
    finally:
        c.stop()


def _prefix(edb_id: str) -> str:
    # c.edb 一次只能放同一前缀（EMM / EMI / EMG / E1 ...），混用报 10003003
    return edb_id[:3] if edb_id.startswith("EM") else edb_id[:2]


def edb(c, ids: list[str], start: str, end: str) -> tuple[dict, dict]:
    """逐个取 EDB 序列。返回 (结果, 错误)：结果按 ID 存 codes/indicators/dates/data。"""
    out, errors = {}, {}
    for _, group in groupby(sorted(ids, key=_prefix), key=_prefix):
        for i in group:
            r = c.edb(i, f"StartDate={start},EndDate={end}")
            if r.ErrorCode != 0:
                errors[i] = f"{r.ErrorCode} {r.ErrorMsg}"
                continue
            out[i] = {"codes": r.Codes, "indicators": r.Indicators, "dates": r.Dates, "data": r.Data}
    return out, errors


def closes(c, codes: list[str], start: str, end: str, field: str = "CLOSE"):
    """行情序列（前复权）。返回 (长表 DataFrame, 错误)。"""
    import pandas as pd

    frames, errors = [], {}
    for code in codes:
        df = c.csd(code, field, start, end, "Period=1,AdjustFlag=1,Order=1,Market=0,Ispandas=1")
        if not isinstance(df, pd.DataFrame):
            errors[code] = f"{df.ErrorCode} {df.ErrorMsg}"
            continue
        frames.append(df.reset_index())
    return (pd.concat(frames) if frames else pd.DataFrame()), errors


def lookup(c, queries: list[tuple[str, str]], limit: int = 5) -> dict:
    """按名称查代码：queries 为 [(关键词, 类型代码)]，类型代码见 skill 的 secucode 文档。"""
    found = {}
    for q, t in queries:
        err, s = c.secucode(q, t, "")
        ents = json.loads(s)["data"]["entityList"] if err == 0 else []
        found[q] = [(e["fullName"], e["secuCode"] + e["marketChar"], e["className"]) for e in ents][:limit]
    return found
