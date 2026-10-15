/**
 * 发现报告（fxbaogao.com）研报检索与 PDF 下载。
 *
 * 只驱动真实浏览器页面：检索读取页面自身收到的列表响应，下载通过点击页面按钮并接住 download 事件。
 * 不在浏览器外重放接口，不读取或输出登录 token；登录由用户在 login 子命令打开的窗口里手动完成。
 */
import { chromium, type BrowserContext, type Page } from '@playwright/test';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, statSync, openSync, readSync, closeSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';

const BASE = 'https://www.fxbaogao.com';
const DEFAULT_PROFILE = join(homedir(), '.fxbaogao-profile');
const MIN_BYTES = 10 * 1024;

type Args = Record<string, string | boolean>;

function parseArgs(argv: string[]): { cmd: string; args: Args } {
  const [cmd = 'help', ...rest] = argv;
  const args: Args = {};
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (!a.startsWith('--')) continue;
    const key = a.slice(2);
    const next = rest[i + 1];
    if (next === undefined || next.startsWith('--')) args[key] = true;
    else { args[key] = next; i++; }
  }
  return { cmd, args };
}

const HELP = `Usage: npx tsx .agents/skills/fxbaogao-download/scripts/fxbaogao.ts <command> [options]

Commands:
  login                      Open a headed browser; log in manually, then close the window.
  status                     Report whether the saved profile is logged in (no token is printed).
  search --keyword <kw> --out <list.json>
         [--before YYYY-MM-DD] [--after YYYY-MM-DD] [--code 600498]
         [--types 11|11,12|all] [--broker-only] [--limit N=50] [--max-pages N=10]
                             Search reports (newest first, order=1) and write a candidate list.
                             --types defaults to 11 (company research); see REPORT_TYPES.
  download (--list <list.json> | --ids <id,id>) --out-dir <dir>
         [--lang original|translation|any] [--max N=10] [--delay-ms 5000] [--headless]
                             Download PDFs one by one via the page buttons, verify, write provenance.
                             --lang defaults to original: the card badged 英文 when the report has one,
                             otherwise the single PDF card of a report without a 中文版报告 translation.
                             No original -> status original_not_available (no silent fallback);
                             only --lang any may fall back to the translation.

Common options:
  --profile <dir>            Persistent browser profile (default ~/.fxbaogao-profile, keep outside the repo).
  --headless                 Run without a window (default: headed; the site has bot checks).
`;

async function openContext(args: Args, forceHeaded = false): Promise<BrowserContext> {
  const profile = resolve(String(args.profile ?? DEFAULT_PROFILE));
  mkdirSync(profile, { recursive: true });
  return chromium.launchPersistentContext(profile, {
    headless: forceHeaded ? false : Boolean(args.headless),
    acceptDownloads: true,
    viewport: { width: 1280, height: 900 },
    locale: 'zh-CN',
  });
}

async function isLoggedIn(page: Page): Promise<boolean> {
  // 只判断登录字段是否存在，不输出其值。localStorage.user 登录后含 id 与 token；jwt-token 键只在部分操作后出现，不能作判据。
  return page.evaluate(() => {
    try {
      const u = JSON.parse(localStorage.getItem('user') || 'null');
      return Boolean(u && u.id && (u.token || u.jwtToken));
    } catch { return false; }
  });
}

async function firstPage(ctx: BrowserContext): Promise<Page> {
  const page = ctx.pages()[0] ?? (await ctx.newPage());
  page.setDefaultTimeout(20_000);
  page.setDefaultNavigationTimeout(45_000);
  return page;
}

async function cmdLogin(args: Args) {
  const ctx = await openContext(args, true);
  const page = await firstPage(ctx);
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  console.error('Log in manually in the opened window. Waiting up to 10 minutes...');
  const deadline = Date.now() + 10 * 60_000;
  while (Date.now() < deadline) {
    try {
      if (await isLoggedIn(page)) { console.log(JSON.stringify({ logged_in: true })); break; }
    } catch { /* 页面跳转中 */ }
    await page.waitForTimeout(3000);
  }
  await ctx.close();
}

async function cmdStatus(args: Args) {
  const ctx = await openContext(args);
  const page = await firstPage(ctx);
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  console.log(JSON.stringify({ logged_in: await isLoggedIn(page) }));
  await ctx.close();
}

// 页面标签 class reportType-<code> 与文字的对应（2026-09-23 实测）。
const REPORT_TYPES: Record<number, string> = {
  11: '公司研究', 12: '行业研究', 13: '宏观策略', 14: '会议纪要', 16: '财报',
  17: '招股书', 18: '金工量化', 20: '期货研究', 99: '其他',
};

type Candidate = {
  report_id: string;
  title: string;
  org: string | null;
  publish_date: string | null;
  pages: number | null;
  stock_codes: string[];
  stock_names: string[];
  report_type: number | null;
  report_type_name: string | null;
  is_broker: boolean | null;
  is_deep: boolean | null;
  view_url: string;
  hit_snippets: string[];
};

const stripTags = (s: unknown) => String(s ?? '').replace(/<[^>]+>/g, '');

function toDate(v: unknown): string | null {
  if (typeof v !== 'number') return null;
  // pubTime 为秒级时间戳，按北京时间取日期。
  return new Date(v * 1000 + 8 * 3600_000).toISOString().slice(0, 10);
}

function normalize(item: Record<string, unknown>): Candidate | null {
  if (item.docId === undefined || item.docId === null) return null;
  const stocks = Array.isArray(item.stocks) ? (item.stocks as { key?: string; value?: string }[]) : [];
  const type = typeof item.reportType === 'number' ? item.reportType : null;
  const paras = Array.isArray(item.paragraphObjs) ? (item.paragraphObjs as { content?: string }[]) : [];
  return {
    report_id: String(item.docId),
    title: stripTags(item.title),
    org: (item.orgName as string) ?? null,
    publish_date: toDate(item.pubTime),
    pages: typeof item.pageNum === 'number' ? item.pageNum : null,
    stock_codes: stocks.map((s) => String(s.key ?? '')).filter(Boolean),
    stock_names: stocks.map((s) => stripTags(s.value)).filter(Boolean),
    report_type: type,
    report_type_name: type === null ? null : REPORT_TYPES[type] ?? String(type),
    is_broker: typeof item.isNotBroker === 'boolean' ? !item.isNotBroker : null,
    is_deep: typeof item.isDeep === 'boolean' ? item.isDeep : null,
    view_url: `${BASE}/view?id=${item.docId}`,
    hit_snippets: paras.slice(0, 3).map((p) => stripTags(p.content).slice(0, 200)),
  };
}

function dataList(body: unknown): Record<string, unknown>[] {
  const d = (body as { data?: { dataList?: unknown } })?.data?.dataList;
  return Array.isArray(d) ? (d as Record<string, unknown>[]) : [];
}

async function cmdSearch(args: Args) {
  const keyword = args.keyword;
  const out = args.out;
  if (typeof keyword !== 'string' || typeof out !== 'string') throw new Error('search requires --keyword and --out');
  const limit = Number(args.limit ?? 50);
  const maxPages = Number(args['max-pages'] ?? 10);
  const before = typeof args.before === 'string' ? args.before : null;
  const after = typeof args.after === 'string' ? args.after : null;
  const types = args.types === 'all' ? null
    : String(args.types ?? '11').split(',').map(Number).filter((n) => !Number.isNaN(n));
  const code = typeof args.code === 'string' ? args.code : null;
  const brokerOnly = Boolean(args['broker-only']);

  const ctx = await openContext(args);
  const page = await firstPage(ctx);
  const pages: unknown[] = [];
  let totalCount: number | null = null;
  page.on('response', async (resp) => {
    // 研报列表来自 searchReport/search（未登录为 searchNoAuth）；searchReportData/searchList 是“发现数据”图表栏，不是研报。
    if (!/\/mofoun\/report\/searchReport\/search(NoAuth)?(\?|$)/.test(resp.url())) return;
    try {
      const body = await resp.json();
      if ((body as { code?: number }).code !== 0) { console.error(`search response code ${(body as { code?: number }).code}: ${(body as { msg?: string }).msg}`); return; }
      totalCount = (body as { data?: { count?: number } }).data?.count ?? totalCount;
      pages.push(body);
    } catch { /* 非 JSON */ }
  });
  // order=1 为“时间由近到远”（order=2 是综合排序）；rt=<类型> 与页面“报告类型”勾选一致，多类型时不加 rt、改为本地过滤。
  const rt = types && types.length === 1 ? `rt=${types[0]}&` : '';
  const url = `${BASE}/rp?${rt}keywords=${encodeURIComponent(keyword)}&order=1&nop=-1`;
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  const waitNew = async (n: number) => {
    for (let t = 0; t < 40 && pages.length <= n; t++) await page.waitForTimeout(500);
    return pages.length > n;
  };
  await waitNew(0);
  const loggedIn = await isLoggedIn(page).catch(() => false);

  const seen = new Set<string>();
  const all: Candidate[] = [];
  const keep = (c: Candidate) =>
    (!before || (c.publish_date !== null && c.publish_date <= before)) &&
    (!after || (c.publish_date !== null && c.publish_date >= after)) &&
    (!types || (c.report_type !== null && types.includes(c.report_type))) &&
    (!code || c.stock_codes.includes(code)) &&
    (!brokerOnly || c.is_broker === true);
  let consumed = 0;
  let pagesRead = 0;
  let stopNote: string | null = null;
  while (true) {
    for (const body of pages.slice(consumed)) {
      pagesRead++;
      for (const item of dataList(body)) {
        const n = normalize(item);
        if (n && !seen.has(n.report_id)) { seen.add(n.report_id); all.push(n); }
      }
    }
    consumed = pages.length;
    const lastPageDates = dataList(pages.at(-1)).map((i) => toDate(i.pubTime)).filter((d): d is string => d !== null);
    const newestOnLastPage = lastPageDates.sort().at(-1) ?? null;
    if (all.filter(keep).length >= limit || pagesRead >= maxPages) break;
    if (after && newestOnLastPage && newestOnLastPage < after) break; // 按时间倒序，整页已早于下限
    const next = page.locator('li.ant-pagination-next');
    if ((await next.count()) === 0 || (await next.getAttribute('aria-disabled')) === 'true') break;
    await page.waitForTimeout(1500);
    await page.keyboard.press('Escape'); // 关闭可能遮挡分页的登录弹窗
    try { await next.click({ timeout: 10_000 }); } catch (e) {
      stopNote = `pagination click failed: ${(e as Error).message.split('\n')[0]}`;
      await page.screenshot({ path: resolve(out, '..', `search-debug-${Date.now()}.png`) }).catch(() => {});
      break;
    }
    if (!(await waitNew(consumed))) { stopNote = 'no new page response after clicking next'; break; }
    console.error(`page ${pagesRead + 1} loaded (${all.length} seen so far)`);
  }
  await ctx.close();

  const kept = all.filter(keep).slice(0, limit);
  const result = {
    keyword, searched_at: new Date().toISOString(), logged_in: loggedIn, source_url: url,
    filters: { before, after, types, code, broker_only: brokerOnly, limit, max_pages: maxPages },
    site_total_count: totalCount, pages_read: pagesRead, stop_note: stopNote, total_seen: all.length, kept: kept.length,
    candidates: kept,
    excluded: all.filter((c) => !keep(c)).map((c) => ({
      report_id: c.report_id, publish_date: c.publish_date, org: c.org, report_type_name: c.report_type_name,
      stock_codes: c.stock_codes, title: c.title,
    })),
  };
  mkdirSync(resolve(out, '..'), { recursive: true });
  writeFileSync(out, JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ keyword, pages_read: pagesRead, total_seen: all.length, kept: kept.length, out }));
  if (pages.length === 0) {
    console.error('No search list response captured; the page structure may have changed.');
    process.exitCode = 1;
  }
}

function sha256(path: string) {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function pdfInfo(path: string): Record<string, string> {
  try {
    const out = execFileSync('pdfinfo', [path], { encoding: 'utf8' });
    const info: Record<string, string> = {};
    for (const line of out.split('\n')) {
      const m = line.match(/^([^:]+):\s*(.*)$/);
      if (m) info[m[1].trim()] = m[2].trim();
    }
    return info;
  } catch (e) {
    return { error: String((e as Error).message).split('\n')[0] };
  }
}

function magic(path: string) {
  const fd = openSync(path, 'r');
  const buf = Buffer.alloc(5);
  readSync(fd, buf, 0, 5, 0);
  closeSync(fd);
  return buf.toString('latin1');
}

// 外资与部分机构在 PDF 首页用英文或简称，身份核对时按别名查找。
const ORG_ALIASES: Record<string, string[]> = {
  美银证券: ['BofA', 'Merrill', 'Bank of America'],
  摩根士丹利: ['Morgan Stanley', '摩根士丹利'],
  高盛: ['Goldman'],
  摩根大通: ['J.P. Morgan', 'JPMorgan'],
  花旗: ['Citi'],
  瑞银: ['UBS'],
  野村: ['Nomura'],
  中金公司: ['中金', 'CICC'],
  华泰证券: ['华泰'],
};

function identityCheck(path: string, org: string | null | undefined, codes: string[] | undefined) {
  let text = '';
  try { text = execFileSync('pdftotext', ['-l', '2', path, '-'], { encoding: 'utf8' }); } catch { return { checked: false, org_found: null, code_found: null }; }
  const names = org ? [org, org.replace(/(证券|研究所|股份有限公司)$/, ''), ...(ORG_ALIASES[org] ?? [])].filter((n) => n.length >= 2) : [];
  const lower = text.toLowerCase();
  return {
    checked: true,
    pages: [1, 2],
    org_found: names.length ? names.some((n) => lower.includes(n.toLowerCase())) : null,
    code_found: codes && codes.length ? codes.some((c) => text.includes(c)) : null,
  };
}

class StopError extends Error {}

type Lang = 'original' | 'translation' | 'any';

// 下载菜单实测（2026-09-23，5590064／5651985／5663080）：
// 外资报告顶栏有“中文版报告”按钮，菜单里有两张 PDF 卡：“PDF 下载”（无角标，中文译本）与“PDF 下载 英文”（角标“英文”，英文原件）；
// 国内报告顶栏无“中文版报告”，菜单只有一张“PDF 下载”（原件）及“Word 下载”。
async function pdfCards(page: Page) {
  // 弹窗 DOM 里还有隐藏的卡（如国内报告也有不可见的“PDF 下载英文”“PPT 下载”），只认可见的卡。
  const all = page.locator('.ant-modal-body button');
  const n = await all.count();
  const visible: number[] = [];
  const texts: string[] = [];
  for (let i = 0; i < n; i++) {
    if (await all.nth(i).isVisible()) { visible.push(i); texts.push((await all.nth(i).innerText()).replace(/\s+/g, ' ').trim()); }
  }
  const buttons = { nth: (k: number) => all.nth(visible[k]) };
  const hasTranslationToggle = (await page.getByRole('button', { name: '中文版报告' }).count()) > 0;
  const english = texts.findIndex((t) => /^PDF 下载 ?英文$/.test(t));
  const plain = texts.findIndex((t) => t === 'PDF 下载');
  const options: { language: 'original' | 'translation'; index: number; label: string }[] = [];
  if (english >= 0) options.push({ language: 'original', index: english, label: texts[english] });
  if (plain >= 0) options.push({ language: english >= 0 || hasTranslationToggle ? 'translation' : 'original', index: plain, label: texts[plain] });
  return { buttons, texts, hasTranslationToggle, options };
}

function pickCard(options: { language: 'original' | 'translation'; index: number; label: string }[], lang: Lang) {
  const original = options.find((o) => o.language === 'original');
  const translation = options.find((o) => o.language === 'translation');
  if (lang === 'original') return original ?? null;
  if (lang === 'translation') return translation ?? null;
  return original ?? translation ?? null;
}

// 首两页文本的文字构成：汉字占比高判为中文，否则英文。只作交叉检查，不作语言判定依据。
function textScript(path: string) {
  let text = '';
  try { text = execFileSync('pdftotext', ['-l', '2', path, '-'], { encoding: 'utf8' }); } catch { return { checked: false, cjk_ratio: null, script: null }; }
  const cjk = (text.match(/[\u4e00-\u9fff]/g) ?? []).length;
  const latin = (text.match(/[A-Za-z]/g) ?? []).length;
  const total = cjk + latin;
  if (total < 200) return { checked: false, cjk_ratio: null, script: null, reason: 'too little text (scanned?)' };
  const ratio = cjk / total;
  return { checked: true, cjk_ratio: Number(ratio.toFixed(3)), script: ratio >= 0.3 ? 'chinese' : 'english' };
}

async function downloadOne(page: Page, c: Pick<Candidate, 'report_id'> & Partial<Candidate>, outDir: string, lang: Lang = 'original') {
  const view = `${BASE}/view?id=${c.report_id}`;
  await page.goto(view, { waitUntil: 'domcontentloaded' });
  if (!(await isLoggedIn(page))) throw new StopError('not logged in (run the login command)');
  const title = (await page.title()).replace(/\s*-\s*发现报告\s*$/, '');

  const openBtn = page.getByRole('button', { name: '下载' }).first();
  try {
    await openBtn.waitFor({ state: 'visible', timeout: 20_000 });
  } catch {
    throw new Error('download button not found (report may not exist or the page layout changed)');
  }
  await openBtn.click();
  try {
    await page.locator('.ant-modal-body button', { hasText: 'PDF 下载' }).first().waitFor({ state: 'visible', timeout: 15_000 });
  } catch {
    const body = await page.locator('body').innerText();
    const hint = (body.match(/.{0,20}(验证|滑块|登录|权益|次数|额度|开通|VIP).{0,20}/) ?? [''])[0];
    throw new StopError(`PDF download option not shown; page says: ${hint.replace(/\s+/g, ' ')}`);
  }
  const menu = await pdfCards(page);
  const card = pickCard(menu.options, lang);
  const dir = join(outDir, c.report_id);
  if (!card) {
    const status = lang === 'translation' ? 'translation_not_available' : 'original_not_available';
    const record = { report_id: c.report_id, url: view, requested_lang: lang, menu_options: menu.texts, has_translation_toggle: menu.hasTranslationToggle, status, checked_at: new Date().toISOString() };
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'provenance.json'), JSON.stringify(record, null, 2));
    return { ...record, needs_review: false, page_count: null, bytes: null, original_filename: null };
  }
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 90_000 }), menu.buttons.nth(card.index).click()]);
  const failure = await dl.failure();
  if (failure) throw new Error(`download failed: ${failure}`);
  mkdirSync(dir, { recursive: true });
  const filename = dl.suggestedFilename();
  const path = join(dir, filename);
  await dl.saveAs(path);

  const bytes = statSync(path).size;
  const info = pdfInfo(path);
  const pageCount = info.Pages ? Number(info.Pages) : null;
  const checks = {
    pdf_magic: magic(path) === '%PDF-',
    size_over_10kb: bytes > MIN_BYTES,
    pdfinfo_pages: pageCount !== null && pageCount > 0,
    pages_match_listing: c.pages ? pageCount === c.pages : null,
  };
  const ok = checks.pdf_magic && checks.size_over_10kb && checks.pdfinfo_pages && checks.pages_match_listing !== false;
  // 身份核对只看前两页文本，不阻断下载；未命中时标记人工复核。
  const identity = ok ? identityCheck(path, c.org, c.stock_codes) : null;
  // 语言以实际点中的菜单卡为准；再用首两页中英文字符比例交叉检查，不一致时要求人工复核。
  const script = ok ? textScript(path) : null;
  const expectedScript = card.label.includes('英文') ? 'english' : 'chinese';
  const languageMismatch = Boolean(script && script.checked && script.script !== expectedScript);
  const provenance = {
    report_id: c.report_id,
    channel: '发现报告',
    url: view,
    page_title: title,
    title: c.title ?? null,
    org: c.org ?? null,
    publish_date: c.publish_date ?? null,
    listing_pages: c.pages ?? null,
    stock_codes: c.stock_codes ?? [],
    original_filename: filename,
    path,
    bytes,
    sha256: sha256(path),
    page_count: pageCount,
    pdf_creator: info.Creator ?? null,
    pdf_producer: info.Producer ?? null,
    pdfinfo_error: info.error ?? null,
    source_nature: 'platform_distributed',
    acquired_at: new Date().toISOString(),
    language: card.language,
    requested_lang: lang,
    menu_option_clicked: card.label,
    menu_options: menu.texts,
    has_translation_toggle: menu.hasTranslationToggle,
    text_script_check: script ? { ...script, expected: expectedScript, mismatch: languageMismatch } : null,
    checks,
    identity,
    needs_review: Boolean(identity && (identity.org_found === false || identity.code_found === false)) || languageMismatch,
    status: ok ? 'verified' : 'failed_checks',
  };
  writeFileSync(join(dir, 'provenance.json'), JSON.stringify(provenance, null, 2));
  return provenance;
}

async function cmdDownload(args: Args) {
  const outDir = args['out-dir'];
  if (typeof outDir !== 'string') throw new Error('download requires --out-dir');
  let items: (Pick<Candidate, 'report_id'> & Partial<Candidate>)[] = [];
  if (typeof args.list === 'string') items = JSON.parse(readFileSync(args.list, 'utf8')).candidates;
  else if (typeof args.ids === 'string') items = args.ids.split(',').map((s) => ({ report_id: s.trim() })).filter((x) => x.report_id);
  else throw new Error('download requires --list or --ids');
  const max = Number(args.max ?? 10);
  const delay = Number(args['delay-ms'] ?? 5000);
  const lang = String(args.lang ?? 'original') as Lang;
  if (!['original', 'translation', 'any'].includes(lang)) throw new Error('--lang must be original, translation or any');
  items = items.slice(0, max);
  mkdirSync(outDir, { recursive: true });

  const ctx = await openContext(args);
  const page = await firstPage(ctx);
  const results: unknown[] = [];
  let stopped: string | null = null;
  for (const [i, c] of items.entries()) {
    const existing = join(outDir, c.report_id, 'provenance.json');
    if (existsSync(existing)) {
      const p = JSON.parse(readFileSync(existing, 'utf8'));
      if (p.status === 'verified' && (p.language === lang || (lang === 'any' && p.language))) {
        results.push({ report_id: c.report_id, status: 'skipped_existing' });
        console.error(`[${i + 1}/${items.length}] ${c.report_id} skipped (already verified)`);
        continue;
      }
    }
    try {
      const p = await downloadOne(page, c, outDir, lang);
      results.push({ report_id: c.report_id, status: p.status, needs_review: p.needs_review, pages: p.page_count, bytes: p.bytes, file: p.original_filename });
      console.error(`[${i + 1}/${items.length}] ${c.report_id} ${p.status}${p.needs_review ? ' (needs review)' : ''} ${p.page_count}p ${p.bytes}B`);
    } catch (e) {
      const msg = (e as Error).message;
      results.push({ report_id: c.report_id, status: e instanceof StopError ? 'stopped' : 'error', error: msg });
      console.error(`[${i + 1}/${items.length}] ${c.report_id} ${e instanceof StopError ? 'STOP' : 'ERROR'}: ${msg}`);
      if (e instanceof StopError) { stopped = msg; break; }
    }
    if (i < items.length - 1) await page.waitForTimeout(delay);
  }
  await ctx.close();
  const summary = { run_at: new Date().toISOString(), out_dir: outDir, requested: items.length, stopped, results };
  writeFileSync(join(outDir, `download-run-${Date.now()}.json`), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
  if (stopped || results.some((r) => !['verified', 'skipped_existing', 'original_not_available', 'translation_not_available'].includes((r as { status: string }).status))) process.exitCode = 1;
}

async function main() {
  const { cmd, args } = parseArgs(process.argv.slice(2));
  // 整体看门狗：login 最长 11 分钟，其余 15 分钟；到时强制退出，避免挂起。
  const watchdogMs = cmd === 'login' ? 11 * 60_000 : Number(args['timeout-min'] ?? 15) * 60_000;
  setTimeout(() => { console.error(`Timed out after ${watchdogMs / 60_000} min`); process.exit(124); }, watchdogMs).unref();
  if (cmd === 'login') return cmdLogin(args);
  if (cmd === 'status') return cmdStatus(args);
  if (cmd === 'search') return cmdSearch(args);
  if (cmd === 'download') return cmdDownload(args);
  process.stdout.write(HELP);
  if (cmd !== 'help' && cmd !== '--help') process.exitCode = 2;
}

main().catch((e) => { console.error(String(e?.message ?? e)); process.exitCode = 1; });
