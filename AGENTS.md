# macro-lab

本项目对宏观指标、大类资产与建模做详细讨论和实验。中国、美国、全球三条线分开推进，中国线先行，逐步讨论、逐项确认。

开始工作先读 `HANDOFF.md`。

## 定位

- 独立实验室，与 `/Users/leon/Stock/invest-lab` 分开运行。invest-lab 的宏观层（SPEC 宏观维度、macro 角色、已定估值口径）不受本项目影响；结论成熟后再定交接口径。
- `docs/imports/` 下的材料都是候选参考，未经审核，不代表已采纳。使用前先读 `docs/imports/README.md` 和各目录的来源说明。

## 目录

- `docs/imports/`：迁入的参考材料。
- `.agents/skills/`：数据 skill。2026-10-15 自 invest-lab 复制，此后两边各自维护。
- `runs/`：运行、状态与错误记录。
- 讨论与实验产物的目录，随中国线的讨论确定。

## 运行与资料

- Python 3.12，统一使用 `uv run`；文件使用 UTF-8。
- 长输出分段读取，或先保存为文件再分段读。
- shell 为 C locale：sed、tr 按字节处理会损坏中文；替换中文用 Python 或编辑工具。
- 原始资料保存在 `/Users/leon/Stock/invest-sources`，按资料 ID＋定位引用，不在本仓库重复保存原件。写入登记的规则待定，见 `HANDOFF.md`。
- 数据凭据只从环境变量或终端登录取得，不写入仓库。
