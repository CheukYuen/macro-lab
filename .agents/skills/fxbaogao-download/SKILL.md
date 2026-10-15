---
name: fxbaogao-download
description: 在发现报告（fxbaogao.com）按公司检索券商研报，并用已登录的 Playwright 浏览器下载平台分发的原文 PDF，自动校验并写 provenance。用户要求从发现报告查找、下载或核对研报原文时使用；Iwencai 等渠道只给摘录、需要取原文 PDF 时也可用。不用于全网搜索，也不用于批量爬取。
---

## invest-lab 本项目浏览器渠道（覆盖下文旧执行流程）

本项目发现报告检索与下载仅使用 Codex 内部浏览器；不使用 Computer Use、旧 Playwright 脚本或旧 profile，不读取登录态或凭据。页面登录、验证码或权益限制由用户处理，失败保留原回执交 M。

浏览器下载目录为 `/Users/leon/codex-downloads/`。D-抄录按信封授权归档到 invest-sources，手工填写 provenance 七字段：报告页 URL、平台报告 ID、机构、发布日期、下载时间、原文件名、SHA-256；按实际页面／文件记录，未知项保留缺口，不补造。保留原件、语言、平台分发性质及原始出处的既有登记要求。

研报截点按报告内载发布日期；本地副本记录实际来源与取得方式。仅发现晚于截点的更新日期、版号或正文后事件等修订迹象才将研报截点资格记 unproven，其他身份、语言与口径问题分别裁定；不因下载／取得时间晚于截点而默认 unproven。CLI／SDK 断网原命令先请求网络提权，失败保存原回执；环境修复、断网与提权重试不计检索预算。下文旧 Playwright/profile 操作流程保留作历史说明，不用于本项目执行。

# 发现报告研报检索与下载

脚本：`scripts/fxbaogao.ts`（TypeScript，用项目已有的 `@playwright/test`，不新增依赖）。从项目根目录运行：

```bash
npx tsx .agents/skills/fxbaogao-download/scripts/fxbaogao.ts help
```

## Spec

**目的**：为公司估值研究取得券商研报 PDF 原文，用来核对盈利预测、估值方法和目标价。取得的是平台分发件（`source_nature: platform_distributed`），不是券商原始发行文件。

**本轮不做**：不在浏览器外重放或伪造站点接口（下载请求带 `x-bot` 和设备指纹头）；不读取、复制、输出登录 token；不绕过验证码、登录墙或权益限制；不批量爬取全站。

**输入**：
- 检索：公司名 `--keyword`、证券代码 `--code`，以及日期窗口 `--after/--before`（信息截点用 `--before`）。
- 下载：检索产出的清单 JSON（`--list`），或 `--ids` 指定的报告 id；语言 `--lang original|translation|any`，默认 `original`。

**输出**：
- `search`：清单 JSON，含 `candidates`（report_id、标题、机构、发布日期、页数、证券代码、类型、是否券商、命中段落）和 `excluded`（被过滤掉的条目及原因字段）。
- `download`：每份一个目录 `<out-dir>/<report_id>/`，内含原文件名 PDF 和 `provenance.json`；另有一份 `download-run-<时间戳>.json` 运行汇总。

**语言（2026-09-23 起）**：下载菜单结构是在已登录浏览器里实测得到的，样本为 5590064、5651985、5663080。
- 外资报告：顶栏有“中文版报告”按钮；弹窗里有两张可见的 PDF 卡。“PDF 下载”无角标，是**中文译本**；“PDF 下载 英文”带“英文”角标，是**英文原件**。同样有两张 Word 卡。
- 国内报告：没有“中文版报告”按钮；只有一张可见的“PDF 下载”，即原件；另有“Word 下载”。
- 弹窗 DOM 里还有**隐藏**的卡（包括国内报告里不可见的“PDF 下载英文”“PPT 下载”），脚本只认可见卡。
- `--lang original`（默认）：只下载原件，即有英文卡时点英文卡，否则点单张 PDF 卡且要求页面不存在“中文版报告”。找不到原件时记 `status=original_not_available`，继续下一份，**不静默改下译本**。
- 只有 `--lang any` 才允许在没有原件时下载译本。
- `--lang translation`：没有译本时记 `translation_not_available`。
- provenance 新增字段：`language`（original／translation，依据是实际点中的菜单卡）、`menu_option_clicked`、`menu_options`、`has_translation_toggle`、`text_script_check`。`text_script_check` 统计首两页汉字与拉丁字母的比例（汉字 ≥30% 判为中文），与所点卡片的预期语言不一致时标 `needs_review`；文字过少（如扫描件）时不作判断。
- 已存在的 `verified` 记录，只有语言与本次 `--lang` 相符时才跳过。

**校验**（写入 provenance 的 `checks` / `identity`）：
- `%PDF-` 开头、大于 10KB、`pdfinfo` 能读出页数、页数等于列表标注页数。任一失败，`status` 记为 `failed_checks`。
- 前两页文本能找到机构名（外资用别名，如 美银→BofA）和证券代码。未找到时 `needs_review: true`，不阻断下载。

**失败行为**：
- 未登录、PDF 下载选项不出现（页面提示验证、登录、权益、额度等）：整批停下（`stopped`），交给用户处理。
- 单份找不到下载按钮或下载失败：记录 `error`，继续下一份。
- 已经 `verified` 的 id 再次运行时跳过（`skipped_existing`）。
- 进程有看门狗（默认 15 分钟，`--timeout-min` 调整）；退出码非 0 表示有失败或中止。

**验收**

以下为旧仓库 `/Users/leon/Stock/investment-research-agent` 固定提交 `b111a88` 的历史验收记录；本节全部证据路径均指该旧仓库中的路径，未复制到本仓。

2026-09-23 第二轮，语言区分。证据在旧仓库 `b111a88` 下的路径 `workspace/calc-runs/t07-p0/fxbaogao-langtest/` 与 `zhongtian/fxbaogao/5590064/`：
- 5590064（大摩 08-07）`--lang original`：点中“PDF 下载 英文”，8 页，汉字占比 0，`language=original`；两次下载 sha256 一致（81192e94…）。
- 5663080（华泰 09-01）`--lang original`：点中唯一可见的“PDF 下载”，6 页，汉字占比 0.798，`language=original`；与此前下载的 sha256 一致。
- 5663080 `--lang translation`：记 `translation_not_available`，不下载。
- 首轮测试未过滤隐藏卡，把国内原件误标为 translation，已修复；无效产物隔离在 `fxbaogao-langtest-invalid-run1/`。

2026-09-23 第一轮，**当时未区分语言**：脚本点第一张“PDF 下载”卡，外资报告拿到的是中文译本，却标为 verified。例如美银 5651985、大摩 5590064 的首次下载都是译本，已事后补标 `language=translation`。以下结论只证明取到了有效 PDF，不证明是原件。证据在旧仓库 `b111a88` 下的路径 `workspace/calc-runs/t07-p0/iwencai/investigation/fxbaogao-pw-test/`：
- 检索 6 家公司（烽火、永鼎、通鼎、中天、亨通、长飞），能翻页，并按日期自动停止。通鼎在窗口内没有券商公司研究，返回空结果。
- 下载 10 份，全部 `verified`，页数全部与列表一致，身份核对全部命中（美银译本通过别名命中；身份核对只看机构名和代码，**不能区分原件与译本**）。
- 长飞·华泰 5631176 重新下载后，sha256 与此前手动归档件 `materials/local/yofc-ht-2026-08-24` 逐字节一致。
- 不存在的 id 报错后继续；重复运行 10 份全部跳过。

## 流程

1. **登录（用户手动，一次）**：`... fxbaogao.ts login` 打开 Chromium 窗口，由用户本人登录（微信扫码等），检测到登录后窗口自动关闭。登录态保存在仓库外的 `~/.fxbaogao-profile`（`--profile` 可改）。Claude 不代为输入账号或密码。之后用 `status` 确认。
2. **检索**：
   ```bash
   npx tsx .agents/skills/fxbaogao-download/scripts/fxbaogao.ts search \
     --keyword 中天科技 --code 600522 --broker-only \
     --after 2026-06-01 --before 2026-09-22 --headless \
     --out <dir>/search-中天科技.json
   ```
   - 页面地址为 `rp?rt=<类型>&keywords=<kw>&order=1`：`order=1` 表示时间倒序，`rt` 是报告类型，默认 11=公司研究，`--types all` 表示不限。
   - 数据来自页面自己收到的列表响应。按日期窗口翻页，某一整页都早于 `--after` 时停止，最多翻 `--max-pages`（默认 10）页。
   - `publish_date` 取平台的 `pubTime`，可能比报告封面日期晚一天，例如国联民生·亨通封面 09-20，平台记为 09-21。按截点筛选时要留意，最终以 PDF 封面为准。
3. **选篇与派单**：研究作者发现已有报告或提出关注问题，新增下载需求写 requests.json；M 合并篇目与同一缺口预算后派 D-抄录执行。篇目涉及账号权益的确认遵循用户已授权范围；未获授权时由 M 请求用户确认。D-抄录将获授权 id 写成只含 `candidates` 的 JSON，或用 `--ids`，研究作者不自行下载或正式入库。
4. **下载**：
   ```bash
   npx tsx .agents/skills/fxbaogao-download/scripts/fxbaogao.ts download \
     --list <dir>/download-list.json --out-dir /Users/leon/Stock/invest-sources/reports/fxbaogao/ \
     --lang original --max 10 --delay-ms 5000 --headless
   ```
   脚本逐份打开 `/view?id=<id>`，点“下载”，按 `--lang` 从可见卡里选“PDF 下载 英文”或“PDF 下载”，接住浏览器下载事件后保存。文件名来自网站“下载设置”，脚本不依赖文件名，身份信息以 provenance 为准。
5. **汇报**：逐份列出 status、language、needs_review、页数；有 `needs_review` 的打开前两页人工确认。外资报告只有译本时，关键数字须对照原件核验：大摩 5590064 的译本曾把 69mn 误译为 690 万、把 Han's Laser 误译为韩华。

## 边界与注意

- **限速**：串行下载，默认每份间隔 5 秒、单次最多 10 份。批量更大时先征得用户同意。
- **验证码**：遇到验证码或风控提示立即停止，报告给用户，不尝试绕过。
- **存放位置与入库**：下载件保存在 `/Users/leon/Stock/invest-sources/reports/fxbaogao/`，每份使用 `<report_id>/` 子目录并保留 provenance。下载成功不等于正式入库或截点通过；D-抄录按资料仓 AGENTS.md 在同一资料清单登记稳定 source_id、机构、日期、PDF 页序、原件路径与 SHA-256，保留平台分发性质、语言和原始出处。已登记原件不覆写，旧记录兼容；不强制全文逐页文字，有文字绑定 PDF 与页序，无文字记限制。
- **共享提取与交接**：D-抄录依据 M 合并的关注问题首次统一盘点相关章节、图表和估值页，按用途提取，暂缓项保留定位与原因；后续仅按明确缺口定点补料。共享盘点及提取由资料仓管理、D-抄录单一写入，绑定原件及自身确切版本，已引用证据不覆写；具体字段和路径以 T03 契约及任务信封授权为准。未提取不当未披露，共同出处不算独立证据。D-判断独立裁定截点/版本/定义及转引关系，D-抄录据裁定追加修订；宏观/行业/F 判断及 V 机构采用意见留各自研究包。研究引用证据 ID＋版本回溯 source_id＋页码，不在研究仓复制原件或另维护原值副本。
- **反自动化**：`--headless` 实测可用。若站点开始拦截无头模式，去掉 `--headless` 改用有界面运行，不要伪装浏览器指纹。
- **维护**：页面结构变化时，检索会报 `No search list response captured`，下载会报找不到按钮。先在浏览器里人工查看再修改脚本，不要猜接口。
