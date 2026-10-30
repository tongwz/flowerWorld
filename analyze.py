#!/usr/bin/env python3
"""读取 data/ 缓存，对每只持仓做 估值/质量/成长 打分，生成 report.md。

打分规则（0~10 分，纯规则，非投资建议）:
  质量: ROE 均值、毛利率、资产负债率
  成长: 营收增速、净利润增速(近3年均值)
  估值: PE 与 PB 相对自身历史分位由数据近似，此处用绝对水位粗判
"""
from pathlib import Path
from typing import List, Optional

import pandas as pd
import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def load_holdings() -> List[dict]:
    with open(ROOT / "holdings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["holdings"]


def load_quote(code: str) -> Optional[dict]:
    p = DATA / f"quote_{code}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if df.empty:
        return None
    r = df.iloc[0]
    return {
        "price": float(r["最新价"]),
        "pe": pd.to_numeric(r.get("市盈率-动态"), errors="coerce"),
        "pb": pd.to_numeric(r.get("市净率"), errors="coerce"),
        "mktcap": pd.to_numeric(r.get("总市值"), errors="coerce"),
    }


def load_indicator(code: str) -> Optional[pd.DataFrame]:
    p = DATA / f"indicator_{code}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


def num(df: pd.DataFrame, col: str) -> pd.Series:
    """取数值列，脏数据转 NaN。"""
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def score_stock(h: dict) -> Optional[dict]:
    code, name = h["code"], h["name"]
    quote = load_quote(code)
    ind = load_indicator(code)
    if quote is None or ind is None:
        return None

    ind = ind.sort_index(ascending=False).head(5)  # 最近5年

    roe = num(ind, "净资产收益率(%)")
    rev_g = num(ind, "主营业务收入增长率(%)")
    profit_g = num(ind, "净利润增长率(%)")
    gross = num(ind, "销售毛利率(%)")
    debt = num(ind, "资产负债率(%)")

    roe_mean = roe.mean()
    rev_g_mean = rev_g.tail(3).mean()
    profit_g_mean = profit_g.tail(3).mean()
    gross_mean = gross.mean()
    debt_last = debt.iloc[0] if not debt.empty else float("nan")

    # ---- 打分 ----
    quality = 5.0
    if roe_mean >= 20: quality += 3
    elif roe_mean >= 15: quality += 2
    elif roe_mean >= 10: quality += 1
    elif roe_mean < 5: quality -= 2
    if gross_mean >= 40: quality += 1.5
    elif gross_mean >= 25: quality += 0.5
    if pd.notna(debt_last) and debt_last > 75: quality -= 1

    growth = 5.0
    if rev_g_mean >= 20: growth += 2.5
    elif rev_g_mean >= 10: growth += 1.5
    elif rev_g_mean < 0: growth -= 2
    if profit_g_mean >= 20: growth += 2.5
    elif profit_g_mean >= 10: growth += 1.5
    elif profit_g_mean < 0: growth -= 2

    valuation = 5.0
    pe, pb = quote["pe"], quote["pb"]
    if pd.notna(pe):
        if pe < 10: valuation += 2.5
        elif pe < 15: valuation += 1.5
        elif pe > 40: valuation -= 2
    if pd.notna(pb):
        if pb < 1: valuation += 1.5
        elif pb > 8: valuation -= 1.5

    return {
        "name": name, "code": code, "industry": h.get("industry", ""),
        "price": quote["price"], "pe": pe, "pb": pb,
        "roe": roe_mean, "rev_g": rev_g_mean, "profit_g": profit_g_mean,
        "gross": gross_mean, "debt": debt_last,
        "quality": round(max(0, min(10, quality)), 1),
        "growth": round(max(0, min(10, growth)), 1),
        "valuation": round(max(0, min(10, valuation)), 1),
        "total": round(max(0, min(10, (quality + growth + valuation) / 3)), 1),
    }


def fmt(v, pct=False, nd=1):
    if pd.isna(v):
        return "—"
    return f"{v:.{nd}f}%" if pct else f"{v:.{nd}f}"


def main():
    holdings = load_holdings()
    scores = []
    for h in holdings:
        if h["type"] == "stock":
            s = score_stock(h)
            if s:
                scores.append(s)

    # 市值/占比(含 LOF 按成本近似)
    total_mv = 0.0
    mv = {}
    for h in holdings:
        if h["type"] == "stock":
            q = load_quote(h["code"])
            m = q["price"] * h["shares"] if q else h["cost"] * h["shares"]
        else:
            m = h["cost"] * h["shares"]
        mv[h["name"]] = m
        total_mv += m

    lines = ["# 持仓基本面报告\n"]
    lines.append("> 规则打分仅供参考，不构成投资建议\n")
    lines.append(f"## 组合概览\n")
    lines.append(f"总市值（不含现金）: {total_mv:,.0f} 元\n")
    lines.append("| 股票 | 市值 | 占比 |")
    lines.append("|---|---:|---:|")
    for name, m in sorted(mv.items(), key=lambda x: -x[1]):
        lines.append(f"| {name} | {m:,.0f} | {m/total_mv*100:.1f}% |")

    lines.append("\n## 个股打分\n")
    lines.append("| 股票 | 现价 | PE | PB | ROE5y | 营收3y增速 | 净利3y增速 | 毛利率 | 资产负债率 | 质量 | 成长 | 估值 | 综合 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in sorted(scores, key=lambda x: -x["total"]):
        lines.append(
            f"| {s['name']} | {fmt(s['price'], nd=2)} | {fmt(s['pe'])} | {fmt(s['pb'])} "
            f"| {fmt(s['roe'], pct=True)} | {fmt(s['rev_g'], pct=True)} | {fmt(s['profit_g'], pct=True)} "
            f"| {fmt(s['gross'], pct=True)} | {fmt(s['debt'], pct=True)} "
            f"| {s['quality']} | {s['growth']} | {s['valuation']} | **{s['total']}** |"
        )

    lines.append("\n## 打分含义\n")
    lines.append("- **质量**: ROE/毛利率/负债率 —— 生意好不好")
    lines.append("- **成长**: 近3年营收与净利增速 —— 生意在不在变好")
    lines.append("- **估值**: PE/PB 绝对水位 —— 现在贵不贵")
    lines.append("- 7分以上=好、5~7=中性、5以下=需要警惕或查看原始财报\n")

    out = ROOT / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {out}")


if __name__ == "__main__":
    main()
