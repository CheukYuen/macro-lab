# 宏观与大类资产设计状态

- 用户授权：详细设计 B；不取数、不编程、不回测。
- 状态：详细设计已交付，文档复核问题已修订；待用户审阅。未实施、未作实证验证。
- 原有工作区改动：`docs/changes/valuation-conventions/HANDOFF.md` 修改；`docs/prompts/yofc-method-trial-3.md` 与三个 data-transcribe staging 路径未跟踪。保持不动。
- 输出性质：proposed 设计，不改变 SPEC 或正式研究基线。
- 分工：三个临时作者分别唯一写 01、02、03；主会话写设计总览、数据与验证契约、研究接口和运行记录。
- 参考方法网页可读；金融接口/数据下载/编程/回测不在授权内。
- 已核对三个子会话 turn_context：model 均为 `gpt-6.1-sol`，`effort` 与 `collaboration_mode.settings.reasoning_effort` 均为 `high`；顶层 `reasoning_effort` 缺失，不能只读该字段判配置失败。
- 子会话：macro_design `01a13adf-ed94-71e3-9f0c-478fd6c67cb2`；asset_design `01a13ae0-07ba-7811-892d-c6d35209adf8`；model_design `01a13ae0-22f8-75b0-84c3-de4c2c0682b6`。
- SOURCES 初始 git status 为空；本轮不写资料仓。
- 主会话已写总览、04 数据口径与验证设计、05 研究接口与实施顺序；等待 01/02/03 后做跨文档一致性检查。

## 最终接收

- 接收六份设计稿：`docs/designs/global-macro-allocation/{README.md,01-宏观指标体系.md,02-资产分类与基准.md,03-模型与组合方案.md,04-数据口径与验证设计.md,05-研究接口与实施顺序.md}`。
- 01：85 个主条目/有限指标组，含定义、频率、用途、候选原始机构和限制；仅研究池设计，非已验证序列清单。
- 02：经济暴露/工具/策略三层、基准候选、全球区域互斥、双币种与资金账、卫星/私募边界。
- 03：三时钟、收益积木、期限匹配、风险/优化方法、四类约束模板及验证与失败降级。
- 04/05：数据时点与特征契约、未来验证、行业公司采用接口、迁移和实施顺序。
- 复核作者 `design_review` 会话 `01a13aec-140d-7441-8eb0-6eb66b4e00ab`，turn_context 实测 `gpt-6.1-sol / high`。复核发现 2 项：资产约束缺穿透计入/高风险信用边界；真实系统入站时间约束过晚。03 原作者和04原作者分别修订；复核作者已确认两项在设计层闭合，见 `design-review.md`。
- 主会话检查：本地跨章/规格/导入链接目标存在；指标主条目计数 85；新六文件逐一 `git diff --no-index --check /dev/null <file>` 无格式错误；数学块定界已修正。仅文档改动，未运行投资模型或测试套件。
- 范围：旧导入与 SPEC 未改；没有金融接口调用、数据下载入库、模型代码或回测，没有 Git 提交。SOURCES 最终 git status 为空。
- LAB 原有变更保留。最终状态另出现范围外未跟踪 `docs/changes/macro-framework/`，归属未判定；本轮未读取或修改，不计入本轮交付。
- 保留限制：候选数据/基准资格、历史版本、税费/套保、模型参数、收益预测和性能尚未验证；部分方法原件可读性限制在正文与 errors.md 记录。这不影响方法设计交付，不授予正式配置或研究接受身份。
