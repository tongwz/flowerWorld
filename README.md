# flowerWorld

A股持仓基本面分析工具（价值投资视角）。

## 功能

- 从 akshare 拉取持仓股票的财务指标（ROE、营收/利润增速、PE/PB、股息率、资产负债率、毛利率）
- 对每只股票做 估值 / 质量 / 成长 三维打分，并给出综合评级
- 生成 `report.md` 报告，含持仓集中度与行业分布统计

## 使用

```bash
pip3 install akshare pandas pyyaml
python3 fetch_data.py    # 拉取并缓存财务数据（data/ 目录）
python3 analyze.py       # 生成报告 report.md
```

持仓变动时手动编辑 `holdings.yaml`。

## 持仓清单

见 `holdings.yaml`：中国平安、海康威视、迈瑞医疗、分众传媒、福耀玻璃、招商银行、赛轮轮胎、隆基绿能、阳光电源、白酒基金LOF。
