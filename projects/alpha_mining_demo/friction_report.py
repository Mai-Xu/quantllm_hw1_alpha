"""
真实摩擦与统计不确定性报告（针对评审「真实摩擦」反馈）。

对 runs/final/factors.json 的留存因子，补齐：
  1. 毛/净收益、换手率、最大回撤、Sharpe
  2. 双边费用 + 印花税（卖出）+ 过户费 + 滑点，三档情景
  3. 可交易性过滤：停牌（volume=0 / high=low）与涨跌停（按板块阈值）在**建仓日**剔除
  4. 统计不确定性：日度 RankIC 的 HAC(Newey–West) t 值 + 平稳区块 bootstrap 置信区间
     （重叠 label 使 IC 序列自相关，普通 t 检验会高估显著性）
  5. 融券约束：A 股个股普遍不可做空 → 多头组合为主，多空仅供参照并明确标注
  6. 容量约束：按多头组合换手占 ADV 比例估算规模上限

口径与局限（如实声明）：
  - label 为 T+1→T+3 收盘到收盘收益（沿用项目既有口径）；执行假设为 T+1 收盘成交
  - 价格已按每股首日 close 归一化，但**日收益率不受影响**（除以常数）
  - 涨跌停用「日收益 ≥ 阈值×0.98」近似（主板 10%、创业/科创 20%）；ST 5% 无法识别
  - 未建模：冲击成本的非线性、融券费用、分红除权、指数成分调整的实际生效日

用法：
    python friction_report.py
输出：
    runs/final/friction_report.md
    runs/final/friction_detail.json
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from eval_factors import load_base_dataset, load_config

from vnpy.alpha.dataset import process_cs_norm, process_drop_na
from functools import partial

BASE_DIR = Path(__file__).resolve().parent
OUT_MD = BASE_DIR / "runs/final/friction_report.md"
OUT_JSON = BASE_DIR / "runs/final/friction_detail.json"

TRADING_DAYS = 244
LABEL_HORIZON = 3      # label 为 T+1→T+3，持有时长 3 个交易日
HAC_LAG = 3            # 重叠 2 日 → 滞后取 3
BOOT_B = 2000          # bootstrap 次数
BLOCK_LEN = 10         # 平稳区块长度（保留重叠自相关）
SEED = 20261009

# 三档成本情景（单边费率）
COST_SCENARIOS = {
    "low":  {"commission": 0.00020, "stamp_sell": 0.0005, "transfer": 0.00001, "slippage": 0.0005},
    "base": {"commission": 0.00025, "stamp_sell": 0.0005, "transfer": 0.00001, "slippage": 0.0010},
    "high": {"commission": 0.00030, "stamp_sell": 0.0005, "transfer": 0.00001, "slippage": 0.0020},
}


# ----------------------------------------------------------------- 工具

def limit_threshold(vt_symbol: str) -> float:
    """按板块返回涨跌停幅度近似值（ST 5% 无法识别，归入 10%）。"""
    code = vt_symbol.split(".")[0]
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    return 0.10


def hac_tstat(x: np.ndarray, lag: int = HAC_LAG) -> tuple[float, float]:
    """Newey–West HAC t 值：均值的稳健显著性（Bartlett 核）。"""
    x = x[np.isfinite(x)]
    n = x.size
    if n < 3:
        return 0.0, 0.0
    mean = x.mean()
    dev = x - mean
    gamma0 = float((dev * dev).mean())
    var = gamma0
    for l in range(1, min(lag, n - 1) + 1):
        w = 1.0 - l / (lag + 1.0)
        cov = float((dev[l:] * dev[:-l]).mean())
        var += 2.0 * w * cov
    if var <= 0:
        return mean, 0.0
    se = np.sqrt(var / n)
    return mean, mean / se if se else 0.0


def stationary_bootstrap(x: np.ndarray, stat, b: int = BOOT_B,
                         block: int = BLOCK_LEN, seed: int = SEED) -> tuple[float, float]:
    """
    平稳区块 bootstrap：以几何分布区块重采样，保留自相关结构。
    返回 (lo, hi) 的 95% 区间（2.5% / 97.5% 分位）。
    """
    x = x[np.isfinite(x)]
    n = x.size
    if n < block * 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    p = 1.0 / block
    stats = np.empty(b)
    for i in range(b):
        idx = np.empty(n, dtype=np.int64)
        pos = 0
        while pos < n:
            start = rng.integers(0, n)
            length = rng.geometric(p)
            end = min(pos + length, n)
            take = end - pos
            idx[pos:end] = (start + np.arange(take)) % n
            pos = end
        stats[i] = stat(x[idx])
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def deoverlap(returns: np.ndarray, k: int = LABEL_HORIZON) -> np.ndarray:
    """
    把重叠的 k 日前瞻收益抽成**非重叠**序列（每 k 个交易日取一个）。

    这是让「年化收益 / 波动 / 回撤」口径成立的前提：
    - 逐日累加：k 日收益重复计入 k 倍，净值会发散到负值（本仓库 2026-09-16 记录过该 artifact）
    - 逐日连乘：同样重复复利
    - 每隔 k 日取一个：每个样本代表一段互不重叠的持有期，可正常累乘/年化
    """
    returns = np.nan_to_num(np.asarray(returns, dtype=float), nan=0.0)
    return returns[::k]


def ann_factor(k: int = LABEL_HORIZON) -> float:
    """非重叠 k 日序列的年化因子。"""
    return TRADING_DAYS / k


def nav_from(returns: np.ndarray) -> np.ndarray:
    """净值曲线（输入应为非重叠序列）。"""
    return np.cumprod(1.0 + np.nan_to_num(returns, nan=0.0))


def max_drawdown(returns: np.ndarray) -> float:
    """最大回撤（基于非重叠序列的连乘净值）。"""
    nav = nav_from(returns)
    if nav.size == 0:
        return 0.0
    peak = np.maximum.accumulate(nav)
    dd = nav / peak - 1.0
    return float(dd.min())


def sharpe_of(returns: np.ndarray, k: int = LABEL_HORIZON) -> float:
    """Sharpe（非重叠 k 日序列，按 244/k 期年化）。"""
    returns = returns[np.isfinite(returns)]
    if returns.size < 2 or returns.std(ddof=1) == 0:
        return 0.0
    return float(returns.mean() / returns.std(ddof=1) * np.sqrt(ann_factor(k)))


# ----------------------------------------------------------------- 主流程

def build_panel(factor_map: dict[str, str], config: dict) -> pd.DataFrame:
    """算因子 + label + 执行所需的价量列，返回长表。"""
    ds = copy.deepcopy(load_base_dataset(config))
    for name, expr in factor_map.items():
        ds.add_feature(name=name, expression=expr)
    ds.set_label(config["label"])
    ds.add_processor("learn", partial(process_drop_na, names=["label"]))
    ds.add_processor("learn", partial(process_cs_norm, names=["label"], method="zscore"))
    ds.prepare_data(None, max_workers=config["workers"])

    cols = ["datetime", "vt_symbol"] + list(factor_map) + \
           ["label", "open", "high", "low", "close", "volume", "turnover"]
    pdf = ds.result_df.select([c for c in cols if c in ds.result_df.columns]).to_pandas()
    pdf["datetime"] = pd.to_datetime(pdf["datetime"])
    pdf = pdf.sort_values(["vt_symbol", "datetime"])

    # 日收益（与归一化无关）与执行日可交易性标记
    g = pdf.groupby("vt_symbol", sort=False)
    pdf["ret"] = g["close"].pct_change()
    pdf["susp"] = (pdf["volume"].fillna(0) <= 0) | (pdf["high"] == pdf["low"])
    thr = pdf["vt_symbol"].map(limit_threshold)
    pdf["limit_up"] = pdf["ret"] >= thr * 0.98
    pdf["limit_dn"] = pdf["ret"] <= -thr * 0.98
    pdf["amount"] = pdf["turnover"]          # 成交额（原始量纲，用作 ADV 代理）
    return pdf


def analyse_factor(pdf: pd.DataFrame, name: str, cfg: dict) -> dict:
    """单因子：分段 RankIC（HAC）+ 十分组毛/净收益 + 摩擦与容量。"""
    d = pdf[["datetime", "vt_symbol", name, "label", "ret", "susp",
             "limit_up", "limit_dn", "amount"]].dropna(subset=[name, "label"]).copy()

    def ic_series(frame: pd.DataFrame) -> np.ndarray:
        return frame.groupby("datetime").apply(
            lambda g: g[name].corr(g["label"], method="spearman"),
            include_groups=False
        ).dropna().to_numpy()

    # ---- 全样本与分段 RankIC（分段：train 样本内 / valid 选择段 / test 样本外）
    ic_all = ic_series(d)
    ic_mean, ic_t = hac_tstat(ic_all)
    ic_lo, ic_hi = stationary_bootstrap(ic_all, np.mean)

    seg_stats: dict[str, dict] = {}
    seg_spec = {
        "train": tuple(cfg["train_period"]),
        "valid": tuple(cfg["valid_period"]),
        "test": tuple(cfg["test_period"]),
    }
    for seg, (s, e) in seg_spec.items():
        sub = d[(d["datetime"] >= pd.Timestamp(s)) & (d["datetime"] <= pd.Timestamp(e))]
        arr = ic_series(sub)
        m, t = hac_tstat(arr)
        lo, hi = stationary_bootstrap(arr, np.mean)
        seg_stats[seg] = {
            "days": int(arr.size),
            "rank_ic_mean": float(m),
            "hac_t": float(t),
            "boot_ci95": [float(lo), float(hi)],
        }

    # ---- 十分组（建仓日剔除停牌与涨停：涨停买入不可成交）
    d["eligible"] = (~d["susp"]) & (~d["limit_up"])
    per_day = d.groupby("datetime")
    daily_rows = []
    for dt, g in per_day:
        good = g[g["eligible"]]
        if good.shape[0] < 20:
            continue
        try:
            g2 = good.copy()
            g2["q"] = pd.qcut(g2[name], 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        by_q = g2.groupby("q")["label"].mean()
        row = {"datetime": dt, "n": good.shape[0]}
        for q in range(10):
            row[f"q{q}"] = float(by_q.get(q, np.nan))
        row["limitup_ratio"] = float(g["limit_up"].mean())
        row["susp_ratio"] = float(g["susp"].mean())
        daily_rows.append(row)

    dd = pd.DataFrame(daily_rows).set_index("datetime").sort_index()
    if dd.empty:
        return {"name": name, "error": "无可分组交易日"}

    # 多头组（Q10）：A 股个股不可做空 → 以多头为主口径
    long_ret_all = dd["q9"].fillna(0.0).to_numpy()
    ls_ret_all = (dd["q9"] - dd["q0"]).fillna(0.0).to_numpy()
    # 非重叠化：每 LABEL_HORIZON 个交易日取一段，使年化/回撤/Sharpe 口径成立
    long_ret = deoverlap(long_ret_all)
    ls_ret = deoverlap(ls_ret_all)

    # ---- 换手：Q10 名单日际变动比例
    d["q"] = np.nan
    for dt, g in d.groupby("datetime"):
        good = g[g["eligible"]]
        if good.shape[0] < 20:
            continue
        try:
            d.loc[good.index, "q"] = pd.qcut(good[name], 10, labels=False, duplicates="drop")
        except ValueError:
            pass
    top = d[d["q"] == 9]
    prev: set = set()
    turnovers = []
    for dt, g in top.groupby("datetime"):
        cur = set(g["vt_symbol"])
        if prev:
            turnovers.append(1.0 - len(cur & prev) / max(len(cur), 1))
        prev = cur
    avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0

    # ---- 成本（按换手率 × 单边费率之和）
    cost = {}
    base_net = None
    for scen, r in COST_SCENARIOS.items():
        buy = r["commission"] + r["transfer"] + r["slippage"]
        sell = r["commission"] + r["transfer"] + r["slippage"] + r["stamp_sell"]
        per_turn = buy + sell
        # 非重叠序列表：每段持有 3 日，段内每日调仓 → 一段的成本 ≈ 3 × 日均换手 × 单次往返费率
        net = long_ret - LABEL_HORIZON * avg_turnover * per_turn
        if scen == "base":
            base_net = net
        cost[scen] = {
            "per_side_round_trip": per_turn,
            "annual_drag": avg_turnover * per_turn * TRADING_DAYS,
            "long_annual_gross": float(np.mean(long_ret) * ann_factor()),
            "long_annual_net": float(np.mean(net) * ann_factor()),
            "long_sharpe_net": sharpe_of(net),
            "long_maxdd_net": max_drawdown(net),
        }

    # ---- bootstrap CI：多头毛/净年化、多空 Sharpe（回撤在重采样下无意义，不做）
    lo_ann, hi_ann = stationary_bootstrap(long_ret, lambda z: np.mean(z) * ann_factor())
    lo_nann, hi_nann = stationary_bootstrap(base_net, lambda z: np.mean(z) * ann_factor())
    lo_sh, hi_sh = stationary_bootstrap(ls_ret, sharpe_of)

    # ---- 容量：多头持仓市值 / ADV，参与率 ≤10%
    adv = float(top["amount"].median()) if not top.empty else float("nan")
    cap = 0.10 * adv * max(len(top) / max(dd.shape[0], 1), 1) if np.isfinite(adv) else float("nan")

    base = COST_SCENARIOS["base"]
    return {
        "name": name,
        "days": int(dd.shape[0]),
        "ic": {
            "rank_ic_mean": float(ic_mean),
            "hac_t": float(ic_t),
            "boot_ci95": [float(ic_lo), float(ic_hi)],
            "hac_lag": HAC_LAG,
        },
        "segments": seg_stats,
        "gross": {
            "long_annual": float(np.mean(long_ret) * ann_factor()),
            "long_sharpe": sharpe_of(long_ret),
            "long_maxdd": max_drawdown(long_ret),
            "ls_annual": float(np.mean(ls_ret) * ann_factor()),
            "ls_sharpe": sharpe_of(ls_ret),
            "ls_maxdd": max_drawdown(ls_ret),
            "nav_convention": f"非重叠 {LABEL_HORIZON} 日块（每 {LABEL_HORIZON} 个交易日取一），"
                              f"年化因子 {TRADING_DAYS}/{LABEL_HORIZON}",
            "blocks": int(long_ret.size),
        },
        "cost": cost,
        "bootstrap_ci": {
            "long_annual_ci95": [float(lo_ann), float(hi_ann)],
            "long_annual_net_base_ci95": [float(lo_nann), float(hi_nann)],
            "ls_sharpe_ci95": [float(lo_sh), float(hi_sh)],
            "B": BOOT_B, "block_len": BLOCK_LEN,
        },
        "turnover": {
            "avg_daily_top_decile": avg_turnover,
            "annual_round_trips": avg_turnover * TRADING_DAYS,
        },
        "tradability": {
            "limitup_ratio_avg": float(dd["limitup_ratio"].mean()),
            "susp_ratio_avg": float(dd["susp_ratio"].mean()),
            "note": "建仓日剔除停牌与涨停（涨停无法买入）；跌停无法卖出未额外剔除",
        },
        "capacity": {
            "adv_proxy_median_amount": adv,
            "size_limit_at_10pct_participation": cap,
            "note": "以多头组成交额中位数作 ADV 代理，参与率 10% 时的规模上限（粗略）",
        },
        "base_cost_used": base,
    }


def render_md(results: list[dict], cfg: dict) -> str:
    L: list[str] = []
    L.append("# 真实摩擦与统计不确定性报告")
    L.append("")
    L.append("对留存因子补齐毛/净收益、换手、回撤、置信区间，并加入费用、印花税、滑点、"
             "涨跌停/停牌与容量约束。统计显著性使用 HAC(Newey–West) 与平稳区块 bootstrap。")
    L.append("")
    L.append("## 口径声明")
    L.append("")
    L.append(f"- 股票池：沪深300 成分（{cfg['index']}），共 819 只标的")
    L.append("- label：`ts_delay(close,-3)/ts_delay(close,-1)-1`（T+1→T+3 收盘到收盘）")
    L.append("- 执行假设：T+1 收盘成交；建仓日剔除停牌与**涨停**（涨停不可买入）")
    L.append("- 分位：每日截面十分位；多头组 = Q10（等权）")
    L.append("- **融券约束**：A 股个股普遍不可做空 → **多头为准**；多空组合仅作对照，不视为可实施")
    L.append(f"- 重叠收益处理：HAC 滞后 {HAC_LAG} 期；bootstrap 平稳区块 B={BOOT_B}、块长 {BLOCK_LEN}")
    L.append(f"- **年化/回撤口径**：收益序列按非重叠 {LABEL_HORIZON} 日块抽取（每 {LABEL_HORIZON} "
             f"个交易日取一），年化因子 {TRADING_DAYS}/{LABEL_HORIZON}；"
             f"避免重叠收益累加/连乘造成的重复计入")
    L.append("- IC 统计量仍用全部交易日（IC 是相关系数序列，不受重叠收益口径影响）")
    L.append("")
    L.append("## 成本情景（单边费率）")
    L.append("")
    L.append("| 情景 | 佣金 | 印花税(卖出) | 过户费 | 滑点 | 单次买卖合计 |")
    L.append("|---|---|---|---|---|---|")
    for k, r in COST_SCENARIOS.items():
        rt = (r["commission"] + r["transfer"] + r["slippage"]) * 2 + r["stamp_sell"]
        L.append(f"| {k} | {r['commission']*100:.3f}% | {r['stamp_sell']*100:.3f}% | "
                 f"{r['transfer']*100:.4f}% | {r['slippage']*100:.3f}% | {rt*100:.4f}% |")
    L.append("")

    for r in results:
        if "error" in r:
            L.append(f"## {r['name']}\n\n计算失败：{r['error']}\n")
            continue
        L.append(f"## {r['name']}")
        L.append("")
        L.append("### RankIC 与统计不确定性")
        L.append("")
        L.append("| 指标 | 数值 |")
        L.append("|---|---|")
        L.append(f"| RankIC 均值 | {r['ic']['rank_ic_mean']:+.4f} |")
        L.append(f"| HAC t 值（lag={r['ic']['hac_lag']}） | {r['ic']['hac_t']:+.2f} |")
        L.append(f"| RankIC 95% bootstrap CI | "
                 f"[{r['ic']['boot_ci95'][0]:+.4f}, {r['ic']['boot_ci95'][1]:+.4f}] |")
        L.append(f"| 有效交易日 | {r['days']} |")
        L.append("")
        L.append("#### 分段 RankIC（区分样本内/外）")
        L.append("")
        L.append("| 段 | 交易日 | RankIC 均值 | HAC t | 95% bootstrap CI |")
        L.append("|---|---|---|---|---|")
        for seg in ("train", "valid", "test"):
            s = r.get("segments", {}).get(seg)
            if not s:
                continue
            L.append(f"| {seg} | {s['days']} | {s['rank_ic_mean']:+.4f} | "
                     f"{s['hac_t']:+.2f} | [{s['boot_ci95'][0]:+.4f}, {s['boot_ci95'][1]:+.4f}] |")
        L.append("")
        L.append("### 毛收益 / 净收益 / 回撤")
        L.append("")
        L.append("| 口径 | 年化 | Sharpe | 最大回撤 |")
        L.append("|---|---|---|---|")
        g = r["gross"]
        L.append(f"| 多头 Q10（毛） | {g['long_annual']:+.2%} | {g['long_sharpe']:.2f} | {g['long_maxdd']:.2%} |")
        for scen in ("low", "base", "high"):
            c = r["cost"][scen]
            L.append(f"| 多头 Q10（净·{scen}） | {c['long_annual_net']:+.2%} | "
                     f"{c['long_sharpe_net']:.2f} | {c['long_maxdd_net']:.2%} |")
        L.append(f"| 多空 Q10−Q1（毛，仅参照） | {g['ls_annual']:+.2%} | {g['ls_sharpe']:.2f} | {g['ls_maxdd']:.2%} |")
        L.append("")
        L.append("### 置信区间（平稳区块 bootstrap）")
        L.append("")
        L.append("| 统计量 | 95% CI |")
        L.append("|---|---|")
        b = r["bootstrap_ci"]
        L.append(f"| 多头毛年化收益 | [{b['long_annual_ci95'][0]:+.2%}, {b['long_annual_ci95'][1]:+.2%}] |")
        L.append(f"| 多头净年化收益（base） | "
                 f"[{b['long_annual_net_base_ci95'][0]:+.2%}, {b['long_annual_net_base_ci95'][1]:+.2%}] |")
        L.append(f"| 多空 Sharpe | [{b['ls_sharpe_ci95'][0]:.2f}, {b['ls_sharpe_ci95'][1]:.2f}] |")
        L.append("")
        L.append(f"> 最大回撤为确定性统计量（基于非重叠块连乘净值），不做重采样区间："
                 f"多头毛 {r['gross']['long_maxdd']:.2%}、多头净(base) "
                 f"{r['cost']['base']['long_maxdd_net']:.2%}、多空毛 {r['gross']['ls_maxdd']:.2%}。")
        L.append("")
        L.append("### 换手、可交易性与容量")
        L.append("")
        t, tr, cap = r["turnover"], r["tradability"], r["capacity"]
        cap_all = cap["size_limit_at_10pct_participation"]
        adv_med = cap["adv_proxy_median_amount"]
        L.append(f"- 多头日均换手：**{t['avg_daily_top_decile']:.1%}**（年化往返 ≈ {t['annual_round_trips']:.0f} 次）")
        L.append(f"- 年化成本拖累（base）：{r['cost']['base']['annual_drag']:.2%}")
        L.append(f"- 建仓日被剔除的涨停占比：{tr['limitup_ratio_avg']:.2%}；停牌占比：{tr['susp_ratio_avg']:.2%}")
        L.append(f"- 多头组 ADV 代理（成交额中位数）：≈ {adv_med:,.0f} 元")
        L.append(f"- 容量（参与率 10%）：≈ {cap_all:,.0f} 元（**粗略**，见局限）")
        L.append("")
    L.append("## 局限（如实声明）")
    L.append("")
    L.append("- 涨跌停以「日收益 ≥ 阈值×0.98」近似；**ST 股 5% 限制无法识别**，会被误判为可交易")
    L.append("- 跌停时无法卖出未额外剔除（持有至 T+3 的假设偏乐观）")
    L.append("- 未建模冲击成本的非线性、融券费用、分红除权、指数成分调整生效日")
    L.append("- 容量估算仅用 ADV 代理与 10% 参与率，未考虑多因子叠加与交易拥挤")
    L.append("- 多空组合在 A 股个股层面不可实施，仅作信号强度参照")
    L.append("")
    return "\n".join(L)


def main() -> None:
    cfg = load_config()
    factors = json.loads((BASE_DIR / "runs/final/factors.json").read_text(encoding="utf-8"))
    factor_map = {k: v["expression"] for k, v in factors.items()}

    print(f"计算 {len(factor_map)} 个因子（含价量列）...")
    pdf = build_panel(factor_map, cfg)
    print(f"面板 {pdf.shape[0]:,} 行")

    results = []
    for name in factor_map:
        print(f"分析 {name} ...")
        results.append(analyse_factor(pdf, name, cfg))

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_md(results, cfg)
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"写入 {OUT_MD}")
    print(f"写入 {OUT_JSON}")


if __name__ == "__main__":
    main()
