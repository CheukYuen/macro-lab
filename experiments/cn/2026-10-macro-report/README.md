# 2026 年 10 月中国市场与外部宏观环境

- 问题：9 月数据与 10 月上半月市场下，中国宏观与外部环境处在什么位置，对 A 股及风格的含义。
- 工作流 skill：`macro_event_market_impact_skill`。
- 信息截止：2026-10-16 A 股收盘。
- 状态：DONE_WITH_LIMITS。局限见各运行的 `run_manifest.json`。

## 版本

| 版本 | 报告 | 运行 | 数据源 | 说明 |
| --- | --- | --- | --- | --- |
| wind | [docx](reports/2026年10月中国市场与外部宏观环境分析报告-wind.docx) | [runs/20261016-wind](runs/20261016-wind/run_manifest.json) | Wind MCP（请求号记在 manifest） | 先跑；内容在 `report_content.json`，`build_report.py` 生成 docx |
| choice | [md](reports/2026年10月中国市场与外部宏观环境分析报告-choice.md) | [runs/20261016-choice](runs/20261016-choice/run_manifest.json) | Choice EDB/行情 + FRED | Wind 额度不足后改用 Choice；raw 入库 |

两版并存，不互相替代。两版数值有差异时，以各自 manifest 记录的口径为准。

## 迁入记录

2026-10-16 由顶层 `runs/`、`reports/` 迁入，文件名加了数据源后缀。迁入时删除了字体缓存；渲染截图和 PDF 移到 `out/`，不入库，可以重建。
