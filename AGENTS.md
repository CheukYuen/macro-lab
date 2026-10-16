# macro-lab

本项目对宏观指标、大类资产与建模做详细讨论和实验。中国、美国、全球三条线分开推进，中国线先行，逐步讨论、逐项确认。

开始工作先读 `HANDOFF.md`。

## 定位

- 独立实验室，与 `/Users/leon/Stock/invest-lab` 分开运行。invest-lab 的宏观层（SPEC 宏观维度、macro 角色、已定估值口径）不受本项目影响；结论成熟后再定交接口径。
- `docs/imports/` 下的材料都是候选参考，未经审核，不代表已采纳。使用前先读 `docs/imports/README.md` 和各目录的来源说明。

## 目录

- `docs/imports/`：迁入的参考材料。
- `docs/data-ids/`：数据源指标 ID 对照。`choice-edb.md` 是给人看的说明，`choice-edb.csv` 给脚本读。取宏观序列前先查这里。
- `.agents/skills/`：数据 skill。2026-10-15 自 invest-lab 复制，此后两边各自维护。
- `src/macrolab/`：公共代码。`sources/` 放各数据源的取数（choice、fred），`ids.py` 读 ID 表，`manifest.py` 写运行记录。
- `experiments/`：全部实验与报告，按区域分为 `cn/`、`us/`、`global/`、`cross/`；`INDEX.md` 是总索引。

## 实验与报告

报告、取数脚本、原始数据都放在所属实验的目录下，不在仓库顶层另建目录。

```
experiments/<区域>/<YYYY-MM[-DD]-slug>/
  README.md                问题、结论、版本对照
  reports/<名称>-<数据源>.<ext>
  runs/<YYYYMMDD>-<数据源>[-序号]/
    run.py 等入口脚本       很薄；取数调用 macrolab，ID 从 docs/data-ids/*.csv 取
    raw/                   原始返回值，原样保存
    out/                   渲染图、中间 PDF、缓存；不入库
    run_manifest.json      用 macrolab.manifest.write 生成
```

- 开始前：先在 `experiments/INDEX.md` 找有没有现成实验。没有就新建目录，并在 INDEX 登记一行。
- 同一问题换数据源再跑：在原实验下新建一个 run，报告用数据源后缀区分。各版本并存，README 的版本表写明差异。
- manifest 必填：experiment、data_source、status（DONE / DONE_WITH_LIMITS / BLOCKED / FAILED）、information_cutoff。另外写明请求记录、局限、失败经过。raw 文件和产出的 sha256 由脚本自动补齐。
- Git：脚本、manifest、`raw/`（JSON/CSV）、最终报告都入库；`out/` 不入库。单个 raw 文件超过约 5 MB 的，先问用户再决定是否入库。
- 运行中发现 ID 的问题（停更、取数无数据、口径不同），同步写回 `docs/data-ids/`。改完跑一次 `uv run python -m macrolab.ids --check`。
- 多次运行里重复出现的逻辑再抽到 `src/macrolab/`，不预先抽象。已有 run 的脚本作为历史记录保留，不回头改写。

## 运行与资料

- Python 3.12，统一使用 `uv run`；文件使用 UTF-8。
- Choice SDK 装在 `~/.choice/`，不在 uv 环境里，由 `macrolab.sources.choice` 按路径导入。一次登录内取完全部数据（10001009 = 账号在别处登录）。
- docx 渲染依赖 Codex documents 运行环境，路径从 `MACROLAB_DOCX_RUNTIME`、`MACROLAB_DOCX_RENDERER` 读取。
- 长输出分段读取，或先保存为文件再分段读。
- shell 为 C locale：sed、tr 按字节处理会损坏中文；替换中文用 Python 或编辑工具。
- 原始资料保存在 `/Users/leon/Stock/invest-sources`，按资料 ID＋定位引用，不在本仓库重复保存原件。写入登记的规则待定，见 `HANDOFF.md`。
- 数据凭据只从环境变量或终端登录取得，不写入仓库。
