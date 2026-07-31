from __future__ import annotations

import html
import os
import re
import shutil
from pathlib import Path


if os.environ.get("TRACKER_PROJECT_DIR"):
    PROJECT_DIR = Path(os.environ["TRACKER_PROJECT_DIR"]).resolve()
else:
    PROJECT_DIR = Path(__file__).resolve().parent

ROOT = PROJECT_DIR
OUTPUTS = PROJECT_DIR
DEST = PROJECT_DIR
IMAGE_SOURCE = PROJECT_DIR / ".source" / "wuzixiao-2026h2-a-h.png"
if not IMAGE_SOURCE.exists():
    IMAGE_SOURCE = Path(r"C:\Users\ANNETT~1\AppData\Local\Temp\codex-clipboard-641a3170-183c-472d-b4fc-47f27064791a.png")
IMAGE_NAME = "wuzixiao-2026h2-a-h.png"
SITE_TITLE = "2026 H2 吴梓豪A股公司追踪"

COMPANIES = [
    ("frd", "飞荣达", "300602.SZ", "散热 / 液冷 / 电磁屏蔽", "36.61", 214.7, 301.5, "40.4%", "华为手机散热与下半年业绩增长相关。", PROJECT_DIR / "1.飞荣达_驱动因素分析_2026年.md"),
    ("yofc", "长飞光纤", "601869.SH / 06869.HK", "光纤光缆 / 光通信材料", "361", 2993, 4140, "38.3%", "27 年利润超百亿为核心观察点，PE 区间来自原图。", PROJECT_DIR / "2.长飞光纤_驱动因素分析_2026年.md"),
    ("shkj", "胜宏科技", "300476.SZ", "AI PCB", "241.5", 2373, 3096, "30.5%", "计算机板与明年 Rubin Ultra 正交背板为观察重点。", PROJECT_DIR / "3.胜宏科技_驱动因素分析_2026年.md"),
    ("dsjm", "东山精密", "002384.SZ", "PCB / 光模块相关", "241.9", 4431, 5610, "26.6%", "索尔思已占业务大头，估值相对合理为原图表述。", PROJECT_DIR / "4.东山精密_驱动因素分析_2026年.md"),
    ("cambricon", "寒武纪", "688256.SH", "AI 芯片", "1190", 7480, 9605, "28.4%", "维持高增长高 PE 状态，27 年利润规模为观察点。", PROJECT_DIR / "5.寒武纪_驱动因素分析_2026年.md"),
    ("hudian", "沪电股份", "002463.SZ", "AI PCB", "127", 2459, 3125, "27.1%", "27 年增幅会高于 26 年为原图观察要点。", PROJECT_DIR / "6.沪电股份_驱动因素分析_2026年.md"),
    ("innolight", "中际旭创", "300308.SZ", "高速光模块", "979", 10900, 12495, "14.6%", "CPO 渗透率与 26-27 年业绩增长是核心跟踪变量。", PROJECT_DIR / "7.中际旭创_驱动因素分析_2026年.md"),
    ("gigadevice", "兆易创新", "603986.SH", "存储 / MCU", "463", 3250, 3720, "14.5%", "下半年存储可能出现高点，年底 PE 是否调整为观察点。", PROJECT_DIR / "8.兆易创新_驱动因素分析_2026年.md"),
]

DASHBOARD_ONLY_COMPANIES = [
    {
        "id": "willsemi-test",
        "name": "伟测科技",
        "code": "688372.SH",
        "track": "封装测试",
        "start_date": "2026-07-25",
        "start_price": "118.9",
        "start_market_cap": 201,
        "year_end_market_cap": 216,
        "space": "7%",
        "source_note": "对标台湾京元电，看好国内AI芯片测试，100以下找低位接。",
    },
    {
        "id": "lianxun-instrument",
        "name": "联讯仪器",
        "code": "688808.SH",
        "track": "封测设备",
        "start_date": "2026-07-25",
        "start_price": "1955",
        "start_market_cap": 2007,
        "year_end_market_cap": 1650,
        "space": "-18%",
        "source_note": "示波器与高速误码分析仪在1.6T光通讯有不错竞争力，未来持续高增长，1600以下可建仓。",
    },
    {
        "id": "unisplendour",
        "name": "紫光股份",
        "code": "000938.SZ",
        "track": "芯片设计 / 服务器 / 交换机",
        "start_date": "2026-07-25",
        "start_price": "41.5",
        "start_market_cap": 1185,
        "year_end_market_cap": 1118,
        "space": "-6%",
        "source_note": "新华三在服务器跟交换机发挥作用，尤其是高速数据中心交换机。",
    },
    {
        "id": "eoptolink",
        "name": "长芯博创",
        "code": "300548.SZ",
        "track": "光器件",
        "start_date": "2026-07-25",
        "start_price": "147.7",
        "start_market_cap": 435,
        "year_end_market_cap": 390,
        "space": "-10%",
        "source_note": "高密度MPO避开太辰光与仕佳，AOC有源光缆谷歌三供，这两年靠这两块支撑增长，6.4T以后MCF-FAU有新增量，走小而精技术路线。",
    },
    {
        "id": "sanhuan",
        "name": "三环集团",
        "code": "300408.SZ",
        "track": "被动元件 / MLCC / 陶瓷件",
        "start_date": "2026-07-25",
        "start_price": "105",
        "start_market_cap": 2093,
        "year_end_market_cap": 2090,
        "space": "0%",
        "source_note": "细分领域突出。第一业务为MLCC(37%)，专攻高压高容大尺寸，受惠AI服务器，高端MLCC由日韩台掌控，三环主攻国内AI服务器。通信器件陶瓷插芯全球第一梯队，真正拳头产品，营收占比29%，受惠AI光通信。半导体陶瓷件占22%也不错。未来稳步高增长，明确度高。100以下找低点建仓。",
    },
]


def as_dict(row: tuple) -> dict:
    keys = ["id", "name", "code", "track", "start_price", "start_market_cap", "year_end_market_cap", "space", "source_note", "file"]
    data = dict(zip(keys, row))
    data["file"] = Path(data["file"])
    data["start_date"] = "2026-07-17"
    data["current_market_cap"] = data["start_market_cap"]
    data["change_from_start"] = "0.0%"
    return data


def dashboard_only_as_dict(data: dict) -> dict:
    item = dict(data)
    item["current_market_cap"] = item["start_market_cap"]
    item["change_from_start"] = "0.0%"
    return item


def inline_markdown(text: str) -> str:
    placeholders: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\u0000{len(placeholders) - 1}\u0000"

    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    for idx, value in enumerate(placeholders):
        escaped = escaped.replace(f"\u0000{idx}\u0000", value)
    return escaped


def display_width(text: str) -> int:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    width = 0
    for char in text:
        width += 2 if ord(char) > 127 else 1
    return width


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def column_bounds(header: str, index: int, col_count: int, headers: list[str]) -> tuple[int, int]:
    if header in {"序号", "#"}:
        return 52, 64
    if header in {"确定性", "状态", "判定", "归属", "归属判定", "类别", "类型", "频率"}:
        return 92, 150
    if "时间" in header or "日期" in header:
        return 130, 210
    if "来源" in header or "数据源" in header:
        return 150, 260
    if header in {"维度", "指标", "项目", "环节", "板块", "客户"}:
        return 140, 240
    if "事项" in header or "场景" in header or "对象" in header:
        return 220, 380
    if any(keyword in header for keyword in ["依据", "证据", "说明", "风险", "不确定", "关联", "关系", "判断", "结论", "备注", "定义", "表现"]):
        return 300, 560
    if col_count >= 5 and index > 0 and headers[0] in {"维度", "类别", "项目"}:
        return 220, 420
    return 170, 340


def column_widths(header: list[str], body: list[list[str]]) -> list[int]:
    widths: list[int] = []
    for index, name in enumerate(header):
        cells = [name] + [row[index] for row in body if index < len(row)]
        min_width, max_width = column_bounds(name, index, len(header), header)
        content_width = max(display_width(cell) for cell in cells) * 7 + 34
        widths.append(clamp(content_width, min_width, max_width))
    return widths


def table_to_html(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in raw.strip().strip("|").split("|")] for raw in lines]
    if not rows:
        return ""
    header = rows[0]
    body = rows[2:] if len(rows) > 1 and re.match(r"^[\s|:\-]+$", lines[1]) else rows[1:]
    col_count = len(header)
    classes = [f"cols-{col_count}"]
    if header and header[0] in {"序号", "#"}:
        classes.append("index-table")
    out = [f"<div class=\"table-wrap\"><table class=\"{' '.join(classes)}\">"]
    widths = column_widths(header, body)
    out.append("<colgroup>" + "".join(f"<col style=\"width:{width}px\">" for width in widths) + "</colgroup>")
    out.append("<thead><tr>" + "".join(f"<th>{inline_markdown(cell)}</th>" for cell in header) + "</tr></thead>")
    out.append("<tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline_markdown(cell)}</td>" for cell in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    table_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    in_ul = False
    in_ol = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append("<p>" + inline_markdown(" ".join(line.strip() for line in paragraph)) + "</p>")
            paragraph = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(table_to_html(table_lines))
            table_lines = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_table()
            close_lists()
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_paragraph()
            close_lists()
            table_lines.append(stripped)
            continue
        flush_table()

        if not stripped:
            flush_paragraph()
            close_lists()
            continue

        if re.fullmatch(r"-{3,}", stripped):
            flush_paragraph()
            close_lists()
            out.append("<hr>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_lists()
            level = min(len(heading.group(1)) + 1, 6)
            out.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_lists()
            out.append(f"<blockquote>{inline_markdown(stripped.lstrip('>').strip())}</blockquote>")
            continue

        unordered = re.match(r"^[-*]\s+(.+)$", stripped)
        if unordered:
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_markdown(unordered.group(1))}</li>")
            continue

        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_markdown(ordered.group(1))}</li>")
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_table()
    close_lists()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(out)


def first_summary(markdown: str) -> str:
    for block in re.split(r"\n\s*\n", markdown):
        cleaned = block.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("|") or cleaned.startswith("---"):
            continue
        cleaned = re.sub(r"[*_`>#]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:130] + ("..." if len(cleaned) > 130 else "")
    return "已接入本地研读资料。"


def cap(value: float) -> str:
    return f"{float(value):,.0f} 亿"


def css() -> str:
    return """
:root {
  --bg: #f6f7f4;
  --paper: #ffffff;
  --ink: #172124;
  --muted: #58666b;
  --line: #d7dedb;
  --line-strong: #aab7b5;
  --teal: #0d6f68;
  --teal-dark: #084d49;
  --gold: #b2762b;
  --blue: #2d5f94;
  --baseline: #ecefed;
  --shade: #eef2f0;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Inter", "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  background: var(--bg);
  color: var(--ink);
  letter-spacing: 0;
}
a { color: inherit; text-decoration: none; }
.app { min-height: 100vh; display: grid; grid-template-columns: 286px minmax(0, 1fr); }
.sidebar {
  position: sticky; top: 0; height: 100vh; padding: 22px 18px; overflow: auto;
  background: #102426; color: #f4faf8; border-right: 1px solid #0b1b1d;
}
.brand { display: grid; gap: 8px; padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,.16); margin-bottom: 18px; }
.brand strong { font-size: 18px; line-height: 1.35; }
.brand span { color: #b7cbc7; font-size: 12px; line-height: 1.5; }
.nav-section-title { margin: 18px 0 8px; font-size: 12px; color: #9fbbb6; text-transform: uppercase; }
.nav-main, .nav-company { display: grid; gap: 3px; padding: 10px 11px; border-radius: 6px; color: #edf7f4; }
.nav-main:hover, .nav-company:hover, .active { background: rgba(255,255,255,.09); }
.nav-company small { color: #a8c0bb; font-size: 11px; line-height: 1.35; }
.content { min-width: 0; padding: 28px 34px 56px; }
.hero, section, .research-article { background: var(--paper); border: 1px solid var(--line); border-radius: 8px; }
.hero { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(280px, .8fr); gap: 24px; align-items: end; padding: 26px; }
.eyebrow { margin: 0 0 8px; color: var(--teal-dark); font-size: 13px; font-weight: 700; }
h1 { margin: 0; font-size: 34px; line-height: 1.18; letter-spacing: 0; }
h2 { margin: 0; font-size: 24px; line-height: 1.3; }
.hero p, .section-head p, .note { color: var(--muted); line-height: 1.75; margin: 8px 0 0; }
.hero-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.metric { padding: 13px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfb; }
.metric span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
.metric strong { font-size: 18px; color: var(--ink); }
section, .research-article { margin-top: 24px; padding: 24px 26px; }
.section-head, .article-head { display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 16px; }
.source-image { display: grid; gap: 12px; }
.source-image img { width: 100%; height: auto; border: 1px solid var(--line-strong); border-radius: 6px; background: #fff; }
.company-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.company-card { min-height: 128px; display: grid; align-content: start; gap: 8px; padding: 14px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfb; }
.company-card:hover { border-color: var(--teal); box-shadow: 0 8px 20px rgba(16,36,38,.08); }
.company-card strong { font-size: 18px; color: var(--teal-dark); }
.company-card span, .company-card em { color: var(--muted); font-style: normal; font-size: 13px; line-height: 1.5; }
.card-kicker { color: var(--blue) !important; font-weight: 700; }
.table-wrap { width: fit-content; max-width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; }
table { width: auto; min-width: 0; max-width: none; border-collapse: collapse; background: #fff; table-layout: fixed; }
th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; line-height: 1.55; }
th { color: #173237; background: #e7efed; font-weight: 800; white-space: normal; }
th, td { box-sizing: border-box; overflow-wrap: break-word; word-break: normal; }
th.baseline, td.baseline { background: var(--baseline); }
td a { display: block; color: var(--teal-dark); font-weight: 800; margin-bottom: 3px; }
td span { color: var(--muted); font-size: 12px; }
.weekly { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.monitor-box { padding: 16px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfb; }
.monitor-box h3 { margin: 0 0 10px; font-size: 16px; }
.monitor-box ul { margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.75; }
.article-head { align-items: start; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
.article-summary { margin: 16px 0; padding: 14px; border-left: 4px solid var(--gold); background: #fff8ee; color: #4c3b25; line-height: 1.75; }
.markdown-body { color: #1b2629; line-height: 1.82; font-size: 15px; }
.markdown-body h2, .markdown-body h3, .markdown-body h4 { margin: 28px 0 12px; color: #14282c; line-height: 1.35; }
.markdown-body h2 { font-size: 22px; } .markdown-body h3 { font-size: 18px; } .markdown-body h4 { font-size: 16px; }
.markdown-body p { margin: 12px 0; }
.markdown-body blockquote { margin: 14px 0; padding: 12px 14px; border-left: 4px solid var(--teal); background: var(--shade); color: #2f4247; }
.markdown-body pre { overflow-x: auto; padding: 14px; border-radius: 6px; background: #102426; color: #e9f4f1; line-height: 1.65; font-size: 13px; }
.markdown-body code { font-family: "Consolas", "SFMono-Regular", monospace; font-size: .92em; }
.markdown-body :not(pre) > code { padding: 2px 5px; border-radius: 4px; background: #edf1ef; color: #284144; }
.markdown-body ul, .markdown-body ol { padding-left: 22px; }
.mobile-bar { display: none; position: sticky; top: 0; z-index: 5; padding: 10px 14px; background: #102426; color: #fff; border-bottom: 1px solid #0b1b1d; }
.mobile-bar select { width: 100%; margin-top: 8px; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,.24); background: #173438; color: #fff; font-size: 14px; }
@media (max-width: 1080px) {
  .app { grid-template-columns: 240px minmax(0, 1fr); }
  .content { padding: 22px; }
  .hero { grid-template-columns: 1fr; }
  .company-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .app { display: block; }
  .sidebar { display: none; }
  .mobile-bar { display: block; }
  .content { padding: 16px 12px 40px; }
  section, .research-article, .hero { padding: 18px 14px; border-radius: 6px; }
  h1 { font-size: 26px; }
  h2 { font-size: 21px; }
  .hero-metrics, .weekly, .company-grid { grid-template-columns: 1fr; }
  .section-head, .article-head { display: grid; }
  table { min-width: 680px; }
}
"""


def prepare() -> list[dict]:
    companies = [as_dict(row) for row in COMPANIES]
    for company in companies:
        markdown = company["file"].read_text(encoding="utf-8")
        company["summary"] = first_summary(markdown)
        company["content"] = markdown_to_html(markdown)
    return companies


def prepare_dashboard_companies(research_companies: list[dict] | None = None) -> list[dict]:
    companies = [dict(company) for company in (research_companies or [as_dict(row) for row in COMPANIES])]
    companies.extend(dashboard_only_as_dict(row) for row in DASHBOARD_ONLY_COMPANIES)
    return companies


def nav(companies: list[dict], active: str, prefix: str = "") -> str:
    main = [
        ("index", "README 首页", f"{prefix}index.html"),
        ("dashboard", "公司池仪表盘", f"{prefix}dashboard.html"),
        ("weekly", "周度观察", f"{prefix}weekly.html"),
    ]
    main_links = "\n".join(f'<a class="nav-main {"active" if key == active else ""}" href="{url}">{label}</a>' for key, label, url in main)
    company_links = "\n".join(
        f'<a href="{prefix}companies/{c["id"]}.html" class="nav-company {"active" if c["id"] == active else ""}"><span>{c["name"]}</span><small>{c["track"]}</small></a>'
        for c in companies
    )
    return f"""
    <aside class="sidebar">
      <div class="brand">
        <strong>{SITE_TITLE}</strong>
        <span>Bloomberg Dashboard + Notion Markdown 架构 · 本地静态原型</span>
      </div>
      {main_links}
      <div class="nav-section-title">公司资料</div>
      {company_links}
    </aside>
    """


def mobile(companies: list[dict], prefix: str = "") -> str:
    options = "".join(f'<option value="{prefix}companies/{c["id"]}.html">{c["name"]}</option>' for c in companies)
    return f"""
    <div class="mobile-bar">
      <strong>{SITE_TITLE}</strong>
      <select aria-label="快速跳转" onchange="if(this.value) location.href=this.value">
        <option value="{prefix}index.html">README 首页</option>
        <option value="{prefix}dashboard.html">公司池仪表盘</option>
        <option value="{prefix}weekly.html">周度观察</option>
        {options}
      </select>
    </div>
    """


def shell_page(title: str, body: str, companies: list[dict], active: str, prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · {SITE_TITLE}</title>
  <link rel="stylesheet" href="{prefix}assets/site.css">
</head>
<body>
  {mobile(companies, prefix)}
  <div class="app">
    {nav(companies, active, prefix)}
    <main class="content">{body}</main>
  </div>
</body>
</html>
"""


def index_page(companies: list[dict]) -> str:
    cards = "\n".join(
        f"""
        <a class="company-card" href="companies/{c['id']}.html">
          <span class="card-kicker">{c['code']}</span>
          <strong>{c['name']}</strong>
          <span>{c['track']}</span>
          <em>起点市值 {cap(c['start_market_cap'])}</em>
        </a>
        """
        for c in companies
    )
    body = f"""
      <header class="hero">
        <div>
          <p class="eyebrow">README · 研究说明</p>
          <h1>{SITE_TITLE}</h1>
          <p>本页面以吴梓豪「半导体大佬的会议室」2026H2 A+H 股投资建议图片为原始观察池，并接入 8 篇已经完成的个人研读资料。页面用途是长期理解公司、跟踪产业变化与记录市值相对起点的变化，不构成买卖建议。</p>
        </div>
        <div class="hero-metrics">
          <div class="metric"><span>起点日期</span><strong>2026-07-17</strong></div>
          <div class="metric"><span>已接入资料</span><strong>8 家公司</strong></div>
          <div class="metric"><span>更新节奏</span><strong>周度观察</strong></div>
          <div class="metric"><span>价格呈现</span><strong>市值表格</strong></div>
        </div>
      </header>
      <section>
        <div class="section-head">
          <div>
            <p class="eyebrow">Source Image</p>
            <h2>吴梓豪 2026H2 投资建议图片</h2>
            <p>原图作为首页研究来源展示区保留，表格中的「目前市值」「年底市值」「目前至年底空间」用于第一版仪表盘的起点数据。</p>
          </div>
        </div>
        <div class="source-image">
          <img src="assets/{IMAGE_NAME}" alt="吴梓豪2026H2 A+H股投资建议原图">
          <p class="note">来源标注：吴梓豪「半导体大佬的会议室」2026H2 A+H 股投资建议。页面仅作个人研究归档与跟踪。</p>
        </div>
      </section>
      <section>
        <div class="section-head">
          <div>
            <p class="eyebrow">Company Pool</p>
            <h2>8 家公司资料入口</h2>
            <p>点击公司卡片会打开独立公司页面。当前版本保留资料原结构，暂不改写公司页内容。</p>
          </div>
        </div>
        <div class="company-grid">{cards}</div>
      </section>
    """
    return shell_page("README 首页", body, companies, "index")


def dashboard_page(companies: list[dict]) -> str:
    rows = "\n".join(
        f"""
        <tr>
          <td><a href="companies/{c['id']}.html">{c['name']}</a><span>{c['code']}</span></td>
          <td>{c['track']}</td>
          <td class="baseline">{c['start_price']}</td>
          <td class="baseline">{cap(c['start_market_cap'])}</td>
          <td>{cap(c['current_market_cap'])}</td>
          <td>{c['change_from_start']}</td>
          <td>{cap(c['year_end_market_cap'])}</td>
          <td>{c['space']}</td>
          <td>{c['source_note']}</td>
        </tr>
        """
        for c in companies
    )
    body = f"""
      <section>
        <div class="section-head">
          <div>
            <p class="eyebrow">Dashboard</p>
            <h1>公司池市值跟踪仪表盘</h1>
            <p>第一版以 2026-07-17 为起点。灰色列为起点数据；当前市值暂等于起点市值，后续每周更新后记录「距起点变化」和「距 2026 年底观察市值空间」。</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>公司</th>
                <th>强相关方向</th>
                <th class="baseline">07/17 股价</th>
                <th class="baseline">07/17 市值</th>
                <th>当前市值</th>
                <th>距起点变化</th>
                <th>2026 年底观察市值</th>
                <th>目前至年底空间</th>
                <th>原图说明摘录</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <p class="note">命名采用「观察市值」而不是投资目标；页面不展示基本面评级、估值高低判断或价格走势图。</p>
      </section>
    """
    return shell_page("公司池仪表盘", body, companies, "dashboard")


def weekly_page(companies: list[dict]) -> str:
    body = """
      <section>
        <div class="section-head">
          <div>
            <p class="eyebrow">Weekly Monitor</p>
            <h1>周度市场观察记录</h1>
            <p>这里预留给后续每周更新。记录事实与来源，不写买卖判断。</p>
          </div>
        </div>
        <div class="weekly">
          <div class="monitor-box">
            <h3>市场观察</h3>
            <ul>
              <li>AI CAPEX 与国内算力建设变化</li>
              <li>800G / 1.6T / CPO 产业链订单与产能变化</li>
              <li>AI PCB、液冷散热、存储周期的周度新闻</li>
            </ul>
          </div>
          <div class="monitor-box">
            <h3>公司观察</h3>
            <ul>
              <li>公告、业绩预告、机构调研与订单线索</li>
              <li>每周市值相对 2026-07-17 起点变化</li>
              <li>与原始研究假设不一致的新增信息</li>
            </ul>
          </div>
        </div>
      </section>
    """
    return shell_page("周度观察", body, companies, "weekly")


def company_page(company: dict, companies: list[dict]) -> str:
    body = f"""
      <article class="research-article">
        <div class="article-head">
          <div>
            <p class="eyebrow">{company['code']} · {company['track']}</p>
            <h1>{company['name']}研读资料</h1>
          </div>
        </div>
        <p class="article-summary">{html.escape(company['summary'])}</p>
        <div class="markdown-body">{company['content']}</div>
      </article>
    """
    return shell_page(f"{company['name']}研读资料", body, companies, company["id"], "../")


def write_site(base: Path, companies: list[dict]) -> None:
    (base / "assets").mkdir(parents=True, exist_ok=True)
    (base / "companies").mkdir(parents=True, exist_ok=True)
    (base / "assets" / "site.css").write_text(css(), encoding="utf-8", newline="\n")
    shutil.copy2(IMAGE_SOURCE, base / "assets" / IMAGE_NAME)
    (base / "index.html").write_text(index_page(companies), encoding="utf-8", newline="\n")
    (base / "dashboard.html").write_text(dashboard_page(companies), encoding="utf-8", newline="\n")
    (base / "weekly.html").write_text(weekly_page(companies), encoding="utf-8", newline="\n")
    for company in companies:
        (base / "companies" / f"{company['id']}.html").write_text(company_page(company, companies), encoding="utf-8", newline="\n")
    shutil.copy2(base / "index.html", base / "ai-industry-research-prototype.html")


def main() -> None:
    companies = prepare()
    write_site(OUTPUTS, companies)
    write_site(DEST, companies)


if __name__ == "__main__":
    main()
