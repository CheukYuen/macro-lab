"""宏观框架模拟输出的配套计算（示意数据，非研究结论）。

所有输入都是编造的示意数，只用来展示 DESIGN.md 的计算流程能产出什么。
运行：uv run --no-project --with numpy --with scipy python docs/changes/macro-framework/mock/mock_calc.py
"""

import json

import numpy as np
from scipy.optimize import minimize

# id, 名称, 10 年几何年化 P50（%）, 年化波动（%）, (P10, P90)；人民币计价视角
ASSETS = [
    ("CNY_CASH", "人民币现金", 1.50, 0.3, (0.9, 2.2)),
    ("CGB", "中国国债", 1.75, 2.5, (1.0, 2.6)),
    ("CN_CREDIT", "中国信用债", 2.00, 2.0, (1.1, 2.8)),
    ("CSI300", "沪深300", 5.6, 22.0, (0.5, 10.5)),
    ("CSI1000", "中证1000", 3.7, 28.0, (-2.5, 9.5)),
    ("HSI", "港股（恒生）", 7.1, 23.0, (1.5, 12.0)),
    ("SPX", "标普500（不对冲）", 4.4, 15.0, (-0.5, 9.0)),
    ("DMXUS", "发达市场除美（不对冲）", 6.3, 15.0, (1.5, 10.5)),
    ("UST_H", "美国国债（对冲）", 2.5, 5.0, (1.2, 3.8)),
    ("GOLD", "黄金", 1.8, 15.0, (-4.0, 8.5)),
    ("CMDTY", "大宗商品", 3.5, 17.0, (-2.0, 8.5)),
]
IDS = [a[0] for a in ASSETS]
N = len(ASSETS)
IDX = {k: i for i, k in enumerate(IDS)}

# 长期结构相关矩阵（上三角给定，示意）
PAIRS = {
    ("CNY_CASH", "CGB"): 0.3, ("CNY_CASH", "CN_CREDIT"): 0.3,
    ("CGB", "CN_CREDIT"): 0.7, ("CGB", "CSI300"): -0.2, ("CGB", "CSI1000"): -0.2,
    ("CGB", "HSI"): -0.1, ("CGB", "SPX"): -0.05, ("CGB", "DMXUS"): -0.05,
    ("CGB", "UST_H"): 0.3, ("CGB", "GOLD"): 0.1, ("CGB", "CMDTY"): -0.1,
    ("CN_CREDIT", "CSI300"): -0.1, ("CN_CREDIT", "CSI1000"): -0.1, ("CN_CREDIT", "HSI"): -0.05,
    ("CN_CREDIT", "UST_H"): 0.2, ("CN_CREDIT", "GOLD"): 0.05,
    ("CSI300", "CSI1000"): 0.85, ("CSI300", "HSI"): 0.6, ("CSI300", "SPX"): 0.3,
    ("CSI300", "DMXUS"): 0.35, ("CSI300", "UST_H"): -0.1, ("CSI300", "CMDTY"): 0.25,
    ("CSI1000", "HSI"): 0.45, ("CSI1000", "SPX"): 0.25, ("CSI1000", "DMXUS"): 0.3,
    ("CSI1000", "UST_H"): -0.1, ("CSI1000", "CMDTY"): 0.2,
    ("HSI", "SPX"): 0.55, ("HSI", "DMXUS"): 0.6, ("HSI", "UST_H"): -0.1,
    ("HSI", "GOLD"): 0.05, ("HSI", "CMDTY"): 0.3,
    ("SPX", "DMXUS"): 0.8, ("SPX", "UST_H"): -0.1, ("SPX", "GOLD"): 0.05, ("SPX", "CMDTY"): 0.25,
    ("DMXUS", "UST_H"): -0.1, ("DMXUS", "GOLD"): 0.15, ("DMXUS", "CMDTY"): 0.35,
    ("UST_H", "GOLD"): 0.2, ("UST_H", "CMDTY"): -0.1,
    ("GOLD", "CMDTY"): 0.35,
}
EQUITY = ["CSI300", "CSI1000", "HSI", "SPX", "DMXUS"]
QDII = ["SPX", "DMXUS", "UST_H"]


def corr_matrix(pairs):
    c = np.eye(N)
    for (a, b), v in pairs.items():
        c[IDX[a], IDX[b]] = c[IDX[b], IDX[a]] = v
    assert np.linalg.eigvalsh(c).min() > 0, "相关矩阵非正定"
    return c


def cov(vols, c):
    v = np.array(vols) / 100
    return np.outer(v, v) * c


GEO = np.array([a[2] for a in ASSETS]) / 100
VOL = np.array([a[3] for a in ASSETS])
CORR = corr_matrix(PAIRS)
SIGMA = cov(VOL, CORR)
ARITH = GEO + np.diag(SIGMA) / 2  # 算术期望 ≈ 几何 + σ²/2

TARGET_VOL = 0.08


def constraints(sigma, target_vol):
    eq = [IDX[k] for k in EQUITY]
    qd = [IDX[k] for k in QDII]
    return [
        {"type": "eq", "fun": lambda w: w.sum() - 1},
        {"type": "ineq", "fun": lambda w: target_vol**2 - w @ sigma @ w},
        {"type": "ineq", "fun": lambda w: 0.60 - w[eq].sum()},
        {"type": "ineq", "fun": lambda w: 0.25 - w[qd].sum()},
    ]


BOUNDS = [(0.02, 1.0) if k == "CNY_CASH" else (0.0, 0.10) if k in ("GOLD", "CMDTY") else (0.0, 1.0) for k in IDS]


def mvo(mu, sigma=SIGMA, bounds=BOUNDS, cons=None):
    cons = cons if cons is not None else constraints(sigma, TARGET_VOL)
    w0 = np.full(len(mu), 1 / len(mu))
    r = minimize(lambda w: -w @ mu, w0, method="SLSQP", bounds=bounds, constraints=cons,
                 options={"maxiter": 500, "ftol": 1e-12})
    assert r.success, r.message
    return np.clip(r.x, 0, None)


def resampled(n=500, seed=7):
    rng = np.random.default_rng(seed)
    p10 = np.array([a[4][0] for a in ASSETS]) / 100
    p90 = np.array([a[4][1] for a in ASSETS]) / 100
    sd = (p90 - p10) / 2.563
    ws = []
    for _ in range(n):
        g = GEO + rng.standard_normal(N) * sd
        ws.append(mvo(g + np.diag(SIGMA) / 2))
    return np.mean(ws, axis=0)


def risk_parity(sigma, ids):
    sub = [IDX[k] for k in ids]
    s = sigma[np.ix_(sub, sub)]
    m = len(sub)

    def obj(w):
        rc = w * (s @ w)
        return ((rc - rc.mean()) ** 2).sum() * 1e6

    r = minimize(obj, np.full(m, 1 / m), method="SLSQP", bounds=[(1e-6, 1)] * m,
                 constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"ftol": 1e-14, "maxiter": 1000})
    w = np.zeros(N)
    w[sub] = r.x
    return w


def stats(w, sigma=SIGMA):
    vol = float(np.sqrt(w @ sigma @ w))
    ar = float(w @ ARITH)
    geo = ar - vol**2 / 2
    cvar = -ar + vol * 2.0627  # 正态 1 年 95% CVaR（损失为正）
    return {"arith": ar, "geo": geo, "vol": vol, "cvar95_1y": cvar}


def stress_sigma(kind):
    c = CORR.copy()
    v = VOL.copy()
    for a in EQUITY:
        v[IDX[a]] *= 1.5
        for b in EQUITY:
            if a != b:
                c[IDX[a], IDX[b]] = 0.85
    if kind == "deflation":  # 增长冲击：股债负相关加深，黄金避险
        s_cn, s_us, gold = -0.4, -0.35, 0.0
    else:  # 通胀冲击（2022 型）：股债同跌
        s_cn, s_us, gold = 0.0, 0.4, 0.1
    for a in EQUITY:
        for b, val in (("CGB", s_cn), ("CN_CREDIT", s_cn / 2), ("UST_H", s_us), ("GOLD", gold)):
            c[IDX[a], IDX[b]] = c[IDX[b], IDX[a]] = val
    ev, evec = np.linalg.eigh(c)
    c = evec @ np.diag(np.clip(ev, 1e-6, None)) @ evec.T
    d = np.sqrt(np.diag(c))
    c = c / np.outer(d, d)
    return cov(v, c)


# 情景：5 年年化收益（%，人民币计价，示意）
SCENARIOS = {
    "base 基准": GEO * 100,
    "capex_up AI加速、美国通胀黏性": [1.8, 1.2, 1.8, 7.5, 6.5, 9.0, 6.5, 6.0, 1.0, 4.0, 6.0],
    "capex_down AI退潮、美国衰退": [1.3, 3.0, 2.2, 1.5, 0.0, 3.0, -3.0, 0.5, 5.0, 6.0, -2.0],
    "中国通缩延续": [1.0, 3.5, 3.0, -1.0, -3.0, 1.0, 4.4, 6.0, 2.8, 4.0, 0.0],
}

# 战术偏离（来自周期层观点，示意）：百分点
TILTS = {"CSI300": 3, "CGB": -2, "CN_CREDIT": -1, "SPX": -2, "UST_H": 2}


def original_method():
    """原版做法：历史均值当预期收益，同一目标波动下的最优权重随窗口跳动。"""
    names = ["现金", "债券", "股票", "另类(70金+30商品)"]
    c = np.array([[1, .68, -.07, -.14], [.68, 1, -.19, -.11], [-.07, -.19, 1, .21], [-.14, -.11, .21, 1]])
    windows = {  # 02 §4.1、§4.4 的原版输出（未核验）
        "12M": ([1.7, 1.8, 22.0, 38.5], [0.1, 1.6, 12.3, 16.8]),
        "60M": ([2.3, 4.1, 2.5, 20.6], [0.25, 1.6, 17.8, 11.3]),
        "120M": ([2.8, 3.8, 7.5, 15.0], [0.39, 1.8, 17.1, 10.9]),
        "240M": ([3.1, 3.9, 13.1, 9.7], [0.49, 2.0, 27.5, 13.3]),
    }
    out = {}
    for k, (mu, vol) in windows.items():
        s = cov(vol, c)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1},
                {"type": "ineq", "fun": lambda w, s=s: TARGET_VOL**2 - w @ s @ w}]
        w = mvo(np.array(mu) / 100, sigma=s, bounds=[(0, 1)] * 4, cons=cons)
        out[k] = dict(zip(names, np.round(w * 100, 1).tolist()))
    return out


def diversification_return(w):
    """每年再平衡的分散化收益：(Σ w_i σ_i² − w'Σw) / 2（Booth–Fama）。"""
    return float((w @ np.diag(SIGMA) - w @ SIGMA @ w) / 2)


def scenario_returns(w):
    bonus = diversification_return(w)
    return {k: round((float(w @ (np.array(v) / 100)) + bonus) * 100, 2) for k, v in SCENARIOS.items()}


def pct(w):
    return {ASSETS[i][1]: round(float(w[i]) * 100, 1) for i in range(N)}


def main():
    plain = mvo(ARITH)
    saa = resampled()
    rp = risk_parity(SIGMA, [k for k in IDS if k != "CNY_CASH"])
    taa = saa.copy()
    for k, v in TILTS.items():
        taa[IDX[k]] += v / 100
    te = float(np.sqrt((taa - saa) @ SIGMA @ (taa - saa)))
    res = {
        "arith_mu": {ASSETS[i][1]: round(float(ARITH[i]) * 100, 2) for i in range(N)},
        "plain_mvo": {"w": pct(plain), **{k: round(v * 100, 2) for k, v in stats(plain).items()}},
        "resampled_saa": {"w": pct(saa), **{k: round(v * 100, 2) for k, v in stats(saa).items()}},
        "risk_parity_ex_cash": {"w": pct(rp), **{k: round(v * 100, 2) for k, v in stats(rp).items()}},
        "taa": {"w": pct(taa), "tracking_error": round(te * 100, 2),
                "equity": round(float(taa[[IDX[k] for k in EQUITY]].sum()) * 100, 1),
                "qdii": round(float(taa[[IDX[k] for k in QDII]].sum()) * 100, 1),
                **{k: round(v * 100, 2) for k, v in stats(taa).items()}},
        "stress_vol": {kind: round(float(np.sqrt(saa @ stress_sigma(kind) @ saa)) * 100, 2)
                       for kind in ("deflation", "inflation")},
        "stress_cvar95_1y": {kind: round(float(-(saa @ ARITH) + np.sqrt(saa @ stress_sigma(kind) @ saa) * 2.0627) * 100, 2)
                             for kind in ("deflation", "inflation")},
        "diversification_return_saa": round(diversification_return(saa) * 100, 2),
        "scenarios_saa": scenario_returns(saa),
        "scenarios_taa": scenario_returns(taa),
        "original_method": original_method(),
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
