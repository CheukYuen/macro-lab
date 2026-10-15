# 来源说明：Claude 宏观框架草稿

- 原路径：`/Users/leon/Stock/invest-lab/docs/changes/macro-framework/`。未提交 Git；2026-10-15 迁入后从 invest-lab 删除。
- 作者与时间：Claude Code 会话，2026-10-14 至 15。
- 起因：用户认为 landing-zone 的指标与建模受当时数据源限制，要求在数据源不受限的前提下重新设计。开始前用户回答了四问：两个出口（估值链路、大类资产）共用底层；中美双核加全球因子；长期 CMA 与周期两层；四类数据源全部可用。
- 内容：
  - `DESIGN.md`：设计稿 v0，含指标层、资产层、长期收益假设、风险模型、周期层、两个出口和待定项 D1–D9；
  - `indicators.csv`：指标表 200 项，其中 T1 82 项；
  - `HANDOFF.md`：当时的接续记录；
  - `mock/mock-output.md`：模拟输出，**全部数字为示意数**；
  - `mock/mock_calc.py`：配置示例的计算脚本。
- 性质：草稿，用户未逐项确认 D1–D9。迁入后用户决定中国、美国、全球三条线分开、从头逐步讨论；本草稿只作候选参考，其中"中美双核一次设计"的结构不再作为基线。
- 已知失效：
  - 文中路径（`docs/imports/landing-zone-macro/`、`SPEC.md`、`docs/changes/valuation-conventions/` 等）指 invest-lab；本仓库对应位置是 `../landing-zone-macro/`，其余仍在 invest-lab；
  - `HANDOFF.md` 的"下一步"已被本次迁移取代；
  - 脚本运行命令中的路径需改为本目录路径。
