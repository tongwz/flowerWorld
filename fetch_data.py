#!/usr/bin/env python3
"""拉取持仓股票的财务与行情数据，缓存到 data/ 目录。

数据源: akshare (免费开源 A 股数据库)
产出:
  data/quote_<code>.csv       最新行情
  data/indicator_<code>.csv   按年度财务指标
"""
import json
import time
from pathlib import Path

import akshare as ak
import pandas as pd
import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


def load_holdings() -> list[dict]:
    with open(ROOT / "holdings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["holdings"]


def fetch_quote(code: str) -> pd.DataFrame:
    """单票实时行情(含最新价、PE、PB、总市值)。"""
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == code]
    if row.empty:
        raise ValueError(f"行情中未找到 {code}")
    return row


def fetch_indicator(code: str) -> pd.DataFrame:
    """按年度的财务指标(ROE/增速/毛利率/负债率/股息等)。"""
    return ak.stock_financial_analysis_indicator(symbol=code, start_year="2019")


def main():
    holdings = load_holdings()
    stocks = [h for h in holdings if h["type"] == "stock"]
    print(f"共 {len(stocks)} 只股票待拉取\n")

    # 行情接口一次返回全市场，只调一次
    print("拉取全市场行情 ...")
    spot = ak.stock_zh_a_spot_em()
    spot.to_csv(DATA / "spot_all.csv", index=False)

    for h in stocks:
        code = h["code"]
        name = h["name"]
        try:
            row = spot[spot["代码"] == code]
            row.to_csv(DATA / f"quote_{code}.csv", index=False)

            ind = fetch_indicator(code)
            ind.to_csv(DATA / f"indicator_{code}.csv", index=False)

            price = row.iloc[0]["最新价"]
            print(f"  {name}({code}) 现价 {price}  指标 {len(ind)} 行  OK")
        except Exception as e:  # noqa: BLE001
            print(f"  {name}({code}) 失败: {e}")
        time.sleep(1)  # 温和限频

    print("\n完成，数据在 data/ 目录")


if __name__ == "__main__":
    main()
