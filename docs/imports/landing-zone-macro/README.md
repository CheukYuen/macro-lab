# landing-zone 宏观分析萃取

- 来源仓库：`/Users/leon/Developer/landing-zone`（智能投顾 3.0 数据落库管道），固定提交 `3ff6a87`，萃取日期 2026-10-14。
- 性质：只读参考、候选材料，未经审核。原项目约在 2026-03～04 完成，内容不一定正确、完善；本目录不表示任何研究结论、取数渠道或证据已被接受。
- 与 `docs/imports/` 下其他目录不同：正文（`01`～`07`）是**综合萃取**，不是原样复制；`appendix/` 下文件原样复制，来源见文末。
- 本目录自成一体，不依赖原仓库即可阅读；文中出现的旧文件名只作出处说明。
- 附录中的数值来自原项目 Choice 导出，**无发布日期／版本记录，截点未证实**，不得直接作为 invest-lab 研究证据；采用前按 `SPEC.md` 第 2、4 节重新取数并核验。

## 阅读顺序

| 文件 | 内容 | 用途 |
| --- | --- | --- |
| [01-宏观指标体系.md](01-宏观指标体系.md) | 指标挑选原则、四模块分析框架、指标字典、口径规则、宏观→资产映射 | 人工研究框架；宏观层选指标 |
| [02-大类资产建模.md](02-大类资产建模.md) | 四大类资产腿、方案 A／B、多窗口 σ／Σ／ρ／μ、无风险利率 | 量化输入；折现与风险参数参照 |
| [03-提示词工程.md](03-提示词工程.md) | 逆向工程方法、indicator_id 命名、喂数格式、月报提示词骨架、测评闭环 | LLM Agent 流水线 |
| [04-新闻与事件.md](04-新闻与事件.md) | 硬事件／原子事件规范、单跳机制、标签体系 | 政策与事件输入 |
| [05-数据工程与基准.md](05-数据工程与基准.md) | 三层库表设计、16 子分类基准指数、数据源优先级 | 数据底座设计参照 |
| [06-问题清单.md](06-问题清单.md) | 已发现的错误、口径冲突、方法缺陷及修正建议 | 复用前必读 |
| [07-迁移到估值链路.md](07-迁移到估值链路.md) | 可复用部分、与 invest-lab 宏观六维度对照、中美扩展缺口 | 宏观→行业→公司估值 |

## 一句话结论

可复用的是**方法与结构**：指标挑选五原则、增长／通胀／流动性／需求结构四模块、长表喂数格式、原子事件规范、生成—评测—优化闭环。**数值与参数不可直接用**：预期收益为历史均值、无风险利率取 1Y、部分口径前后矛盾（详见 `06`）。原项目的数据库／ETL 未完成，月报实际由「Python 脚本 → CSV → 提示词」生成。

## appendix 来源文件

| 原路径（landing-zone） | 本目录 |
| --- | --- |
| `提示词模板/data-type.csv` | `appendix/data/data-type.csv`（喂数 schema：板块顺序与指标元数据） |
| `建模数据/建模月频序列.csv` | `appendix/data/建模月频序列.csv`（10 个序列月末值，2002-01～2026-03） |
| `建模数据/plan_a_returns.csv` | `appendix/data/plan_a_returns.csv`（方案 A 四腿月收益） |
| `建模数据/plan_a_windows/*.csv` | `appendix/data/plan_a_windows/`（6 窗口 × corr／cov／sigma／mu） |
| `建模数据/asset_benchmark_profile.csv` | `appendix/data/asset_benchmark_profile.csv`（1Y／3Y／5Y 收益、波动、Sharpe） |
| `建模数据/cgb_summary_metrics.csv` | `appendix/data/cgb_summary_metrics.csv`（季末国债 1Y／10Y 与期限利差） |
| `提示词模板/市场分析-提示词模板.md` | `appendix/prompts/市场分析-提示词模板-v4.md`（完整月报提示词实例，含数据） |
| `逆向工程/skills/reverse_indicator_id/prompt_round1.txt` | `appendix/prompts/reverse-id-round1.txt` |
| `逆向工程/skills/reverse_indicator_id/prompt_round2.txt` | `appendix/prompts/reverse-id-round2.txt` |
| `新闻加工/key_news_5_same_schema_v2_less_subjective.csv` | `appendix/news/key-news-sample.csv`（5 条加工后新闻样本） |
