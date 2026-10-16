"""一次登录内完成 Choice 取数：实体查找、EDB 宏观序列、行情序列。原始结果写入 raw/。"""
import json
import sys
from pathlib import Path

import pandas as pd
from EmQuantAPI import c

sys.stdout.reconfigure(encoding="utf-8")
RAW = Path(__file__).parent / "raw"
RAW.mkdir(exist_ok=True)

EDB_MONTHLY = [
    "EMM00000012", "EMM00008445", "EMI00135328", "EMM00121996", "EMM00121999",
    "EMM00122009", "EMM00877640", "EMM00183406", "EMM00183407", "EMM00087086",
    "EMM00087084", "EMM00634721", "EMM02326278", "EMM00631597", "EMM00058496",
    "EMM00072301", "EMM00073348",
]
EDB_DAILY = [
    "EMM00058124", "E1300004", "E1000174", "EMM01588169", "EMG00002651",
    "EMI01778678", "EMM00588704", "EMM00166466",
]
MARKET = {
    "000300.SH": "沪深300", "000001.SH": "上证指数", "399006.SZ": "创业板指",
    "000688.SH": "科创50", "000922.SH": "中证红利", "HSI.HI": "恒生指数",
    "SPX.GI": "标普500", "USDCNH.FX": "美元兑离岸人民币", "USDX.FX": "美元指数",
}
LOOKUPS = [
    ("美国国债10年", "017"), ("美国国债收益率", "017,010"), ("联邦基金利率", "017"),
    ("中证1000", "006"), ("恒生科技", "006"), ("布伦特原油", "018,021"),
]

login = c.start()
if login.ErrorCode != 0:
    print("LOGIN_FAILED", login.ErrorCode, login.ErrorMsg)
    sys.exit(1)
try:
    found = {}
    for q, t in LOOKUPS:
        err, s = c.secucode(q, t, "")
        ents = json.loads(s)["data"]["entityList"] if err == 0 else []
        found[q] = [(e["fullName"], e["secuCode"] + e["marketChar"], e["className"]) for e in ents][:5]
        print("LOOKUP", q, found[q] if err == 0 else (err, s[:120]))
    (RAW / "lookups.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")

    edb_out = {}
    for ids, start in [(EDB_MONTHLY, "2024-09-01"), (EDB_DAILY, "2026-06-01")]:
        for i in ids:
            r = c.edb(i, f"StartDate={start},EndDate=2026-10-16")
            if r.ErrorCode != 0:
                print("EDB_ERR", i, r.ErrorCode, r.ErrorMsg)
                continue
            edb_out[i] = {"codes": r.Codes, "indicators": r.Indicators, "dates": r.Dates, "data": r.Data}
            print("EDB", i, r.Codes[:3], r.Indicators, len(r.Dates), r.Dates[-2:], str(r.Data)[:160])
    (RAW / "edb.json").write_text(json.dumps(edb_out, ensure_ascii=False, indent=1), encoding="utf-8")

    frames = []
    for code in MARKET:
        df = c.csd(code, "CLOSE", "2026-06-01", "2026-10-16",
                   "Period=1,AdjustFlag=1,Order=1,Market=0,Ispandas=1")
        if not isinstance(df, pd.DataFrame):
            print("CSD_ERR", code, df.ErrorCode, df.ErrorMsg)
            continue
        frames.append(df.reset_index())
        print("CSD", code, len(df))
    pd.concat(frames).to_csv(RAW / "market_close.csv", index=False)
finally:
    c.stop()
