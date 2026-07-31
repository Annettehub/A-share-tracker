from __future__ import annotations

import html
import base64
import json
import re
from datetime import datetime
from pathlib import Path

from build_research_site import IMAGE_SOURCE, OUTPUTS, DEST, SITE_TITLE, cap, prepare, prepare_dashboard_companies

TARGET_HTML = "2026 H2 吴梓豪A股公司追踪 2026.7.html"
MARKET_DATA = DEST / "market-data.json"
WEEKLY_OBSERVATIONS = DEST / "weekly-observations.json"


def trim_repeated_company_heading(companies: list[dict]) -> None:
    for company in companies:
        escaped_name = re.escape(html.escape(company["name"]))
        company["content"] = re.sub(
            rf"<h2>\s*{escaped_name}\s*(.*?)</h2>",
            lambda match: f"<h2>{match.group(1).strip()}</h2>" if match.group(1).strip() else "",
            company["content"],
            count=1,
        )


def pct(value: float) -> str:
    return f"{value:+.1f}%"


def price(value: float | str) -> str:
    return f"{float(value):.1f}"


def pct_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace("+", "").replace(",", "")
    if text in {"", "-", "—"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def annotate_dashboard_ranks(companies: list[dict]) -> None:
    for company in companies:
        company.pop("drawdown_rank", None)
        company.pop("upside_rank", None)

    drawdowns = [(pct_number(company.get("drawdown_from_recent_high")), company) for company in companies]
    drawdowns = [(value, company) for value, company in drawdowns if value is not None and value < 0]
    for rank, (_value, company) in enumerate(sorted(drawdowns, key=lambda item: item[0])[:3], start=1):
        company["drawdown_rank"] = rank

    upsides = [(pct_number(company.get("space")), company) for company in companies]
    upsides = [(value, company) for value, company in upsides if value is not None and value > 0]
    for rank, (_value, company) in enumerate(sorted(upsides, key=lambda item: item[0], reverse=True)[:3], start=1):
        company["upside_rank"] = rank


def ranked_metric(value: object, kind: str, rank: object | None) -> str:
    text = html.escape(str(value))
    if rank in {1, 2, 3}:
        return f'<span class="rank-badge rank-{kind}-{rank}">{text}</span>'
    return text


def quote_day_label(companies: list[dict]) -> str:
    for company in companies:
        quote_time = company.get("quote_time")
        if not quote_time:
            continue
        try:
            dt = datetime.strptime(quote_time[:19], "%Y-%m-%d %H:%M:%S")
            return f"{dt.month:02d}/{dt.day:02d}"
        except ValueError:
            continue
    return "当前"


def load_weekly_observations() -> dict | None:
    if not WEEKLY_OBSERVATIONS.exists():
        return None
    return json.loads(WEEKLY_OBSERVATIONS.read_text(encoding="utf-8"))


def render_observation_items(items: list[dict], fallback_items: list[str]) -> str:
    if not items:
        return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in fallback_items) + "</ul>"
    rendered = []
    for item in items:
        keywords = " / ".join(html.escape(str(keyword)) for keyword in item.get("matched_keywords", [])[:4])
        source_path = html.escape(str(item.get("source_path", "")))
        source_url = html.escape(str(item.get("source_url", "")))
        source_time = html.escape(str(item.get("source_commit_time", ""))[:10])
        rendered.append(
            f"""
            <div class="observation-item">
              <div class="observation-meta">{source_time} · {keywords}</div>
              <strong>{html.escape(str(item.get("title", "来源记录")))}</strong>
              <p>{html.escape(str(item.get("snippet", "")))}</p>
              <a href="{source_url}" target="_blank" rel="noopener">{source_path}</a>
            </div>
            """
        )
    return '<div class="observation-list">' + "\n".join(rendered) + "</div>"


def render_company_observations(data: dict | None, companies: list[dict]) -> str:
    fallback = [
        "公告、业绩预告、机构调研与订单线索",
        "每周市值相对 2026-07-17 起点变化",
        "与原始研究假设不一致的新增信息",
    ]
    if not data:
        return "<ul>" + "".join(f"<li>{item}</li>" for item in fallback) + "</ul>"

    groups = data.get("company_observations", {})
    blocks = []
    for company in companies:
        items = groups.get(company["name"], [])
        if not items:
            continue
        blocks.append(
            f"""
            <div class="company-observation-group">
              <h4>{html.escape(company["name"])}</h4>
              {render_observation_items(items, [])}
            </div>
            """
        )
    if not blocks:
        return "<ul>" + "".join(f"<li>{item}</li>" for item in fallback) + "</ul>"
    return "\n".join(blocks)


def dashboard_company_cell(company: dict) -> str:
    name = html.escape(str(company["name"]))
    code = html.escape(str(company["code"]))
    if company.get("content"):
        return f'<a href="#{company["id"]}" data-target="{company["id"]}">{name}</a><span>{code}</span>'
    return f'<strong class="plain-company">{name}</strong><span>{code}</span>'


def apply_market_data(companies: list[dict]) -> dict | None:
    if not MARKET_DATA.exists():
        return None
    data = json.loads(MARKET_DATA.read_text(encoding="utf-8"))
    quotes = data.get("quotes", {})
    for company in companies:
        code = str(company["code"]).split(".")[0].strip()
        quote = quotes.get(code)
        if not quote:
            continue
        current_cap = float(quote["market_cap_yi"])
        company["current_market_cap"] = current_cap
        company["current_price"] = float(quote["price"])
        company["change_from_start"] = pct((current_cap - float(company["start_market_cap"])) / float(company["start_market_cap"]) * 100)
        company["space"] = pct((float(company["year_end_market_cap"]) - current_cap) / current_cap * 100)
        if quote.get("drawdown_from_recent_high_pct") is not None:
            company["drawdown_from_recent_high"] = pct(float(quote["drawdown_from_recent_high_pct"]))
            company["recent_high_price"] = float(quote.get("recent_high_price", 0))
            company["recent_high_date"] = quote.get("recent_high_date", "")
        company["quote_time"] = quote.get("quote_time", "")
    return data


def base_css() -> str:
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
html, body { min-height: 100%; }
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
.view { display: none; }
.view.active { display: block; }
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
section, .research-article { padding: 24px 26px; }
.section-head, .article-head { display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 16px; }
.source-image { display: grid; gap: 12px; }
.source-image img { width: 100%; height: auto; border: 1px solid var(--line-strong); border-radius: 6px; background: #fff; }
.company-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
.company-card { min-height: 128px; display: grid; align-content: start; gap: 8px; padding: 14px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfb; }
.company-card:hover { border-color: var(--teal); box-shadow: 0 8px 20px rgba(16,36,38,.08); }
.company-card strong { font-size: 18px; color: var(--teal-dark); }
.company-card span, .company-card em { color: var(--muted); font-style: normal; font-size: 13px; line-height: 1.5; }
.card-kicker { color: var(--blue) !important; font-weight: 700; }
.table-wrap { width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; }
table { width: 100%; min-width: 1600px; border-collapse: collapse; background: #fff; table-layout: fixed; }
.markdown-body .table-wrap { width: fit-content; max-width: 100%; overflow-x: auto; }
.markdown-body table { width: auto; min-width: 0; max-width: none; table-layout: fixed; }
.markdown-body th, .markdown-body td { box-sizing: border-box; white-space: normal; overflow-wrap: break-word; word-break: normal; }
th, td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; line-height: 1.55; }
th { color: #173237; background: #e7efed; font-weight: 800; white-space: normal; }
th.baseline, td.baseline { background: var(--baseline); }
th.metric-cell, td.metric-cell { width: 112px; text-align: center; vertical-align: middle; }
th.metric-cell { line-height: 1.25; word-break: keep-all; }
 .rank-badge { display: inline-block; min-width: 68px; padding: 4px 8px; border-radius: 5px; font-weight: 800; text-align: center; line-height: 1.25; }
.rank-down-1 { background: #ffd7d2; color: #7c1f17; box-shadow: inset 0 0 0 1px #e79a92; }
.rank-down-2 { background: #ffe4c2; color: #734000; box-shadow: inset 0 0 0 1px #e7b46f; }
.rank-down-3 { background: #fff0b8; color: #604a00; box-shadow: inset 0 0 0 1px #d9bf4c; }
.rank-up-1 { background: #cfeeda; color: #07522a; box-shadow: inset 0 0 0 1px #88c99b; }
.rank-up-2 { background: #dff4df; color: #174f20; box-shadow: inset 0 0 0 1px #9bd29b; }
.rank-up-3 { background: #edf7d2; color: #405400; box-shadow: inset 0 0 0 1px #c5d77a; }
td a, .plain-company { display: block; color: var(--teal-dark); font-weight: 800; margin-bottom: 3px; }
td span { color: var(--muted); font-size: 12px; }
.weekly { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.monitor-box { padding: 16px; border: 1px solid var(--line); border-radius: 6px; background: #fbfcfb; }
.monitor-box h3 { margin: 0 0 10px; font-size: 16px; }
.monitor-box ul { margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.75; }
.observation-list { display: grid; gap: 12px; }
.observation-item { padding: 12px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
.observation-item strong { display: block; color: var(--teal-dark); line-height: 1.45; margin-bottom: 6px; }
.observation-item p { margin: 0 0 8px; color: #26383c; line-height: 1.65; }
.observation-item a { color: var(--blue); font-size: 12px; overflow-wrap: anywhere; }
.observation-meta { color: var(--muted); font-size: 12px; line-height: 1.45; margin-bottom: 5px; }
.company-observation-group { display: grid; gap: 8px; margin-top: 14px; }
.company-observation-group:first-child { margin-top: 0; }
.company-observation-group h4 { margin: 0; color: #14282c; font-size: 15px; }
.article-head { align-items: start; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
.article-summary { margin: 16px 0; padding: 14px; border-left: 4px solid var(--gold); background: #fff8ee; color: #4c3b25; line-height: 1.75; }
.markdown-body { color: #1b2629; line-height: 1.82; font-size: 15px; }
.markdown-body h2, .markdown-body h3, .markdown-body h4 { margin: 28px 0 12px; color: #14282c; line-height: 1.35; }
.markdown-body h2 { font-size: 22px; } .markdown-body h3 { font-size: 18px; } .markdown-body h4 { font-size: 16px; }
.markdown-body p { margin: 12px 0; }
.markdown-body blockquote { margin: 14px 0; padding: 12px 14px; border-left: 4px solid var(--teal); background: var(--shade); color: #2f4247; }
.markdown-body pre { overflow-x: auto; padding: 14px; border-radius: 6px; background: #102426; color: #e9f4f1; line-height: 1.65; font-size: 15px; }
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
  table { min-width: 1400px; }
  .markdown-body table { min-width: 680px; }
}
"""


def render(companies: list[dict], dashboard_companies: list[dict]) -> str:
    market_data = apply_market_data(dashboard_companies)
    annotate_dashboard_ranks(dashboard_companies)
    weekly_data = load_weekly_observations()
    quote_day = quote_day_label(dashboard_companies)
    market_note = "当前市值暂等于起点市值。接入行情快照后，这里会显示抓取时间、来源与校验结果。"
    if market_data:
        validation_text = str(market_data.get("validation", ""))
        if "校验未返回" in validation_text or "校验源不可用" in validation_text:
            compact_validation = "东方财富暂未返回，已保留主源数据"
        elif "差异" in validation_text:
            compact_validation = "双源差异需复核"
        else:
            compact_validation = "双源校验通过"
        market_note = (
            f"行情快照：{html.escape(market_data.get('updated_at', ''))}｜"
            f"主源：腾讯行情｜"
            f"校验：{compact_validation}"
        )
    weekly_note = "尚未同步 ai-investing 仓库；这里先保留观察项占位。"
    if weekly_data:
        weekly_note = (
            f"已同步 {html.escape(str(weekly_data.get('source_repo', 'Annettehub/ai-investing')))}；"
            f"快照时间：{html.escape(str(weekly_data.get('updated_at', '')))}；"
            f"来源提交：{html.escape(str(weekly_data.get('source_commit', ''))[:7])}。"
        )
    market_observation_html = render_observation_items(
        (weekly_data or {}).get("market_observations", []),
        [
            "AI CAPEX 与国内算力建设变化",
            "800G / 1.6T / CPO 产业链订单与产能变化",
            "AI PCB、液冷散热、存储周期的周度新闻",
        ],
    )
    company_observation_html = render_company_observations(weekly_data, companies)
    image_data = base64.b64encode(IMAGE_SOURCE.read_bytes()).decode("ascii")
    image_src = f"data:image/png;base64,{image_data}"
    nav_main = "\n".join(
        [
            '<a class="nav-main" href="#home" data-target="home">README 首页</a>',
            '<a class="nav-main" href="#dashboard" data-target="dashboard">公司池仪表盘</a>',
            '<a class="nav-main" href="#weekly" data-target="weekly">周度观察</a>',
        ]
    )
    nav_companies = "\n".join(
        f'<a href="#{c["id"]}" class="nav-company" data-target="{c["id"]}"><span>{c["name"]}</span><small>{c["track"]}</small></a>'
        for c in companies
    )
    mobile_options = "".join(f'<option value="{c["id"]}">{c["name"]}</option>' for c in companies)
    cards = "\n".join(
        f"""
        <a class="company-card" href="#{c['id']}" data-target="{c['id']}">
          <span class="card-kicker">{c['code']}</span>
          <strong>{c['name']}</strong>
          <span>{c['track']}</span>
          <em>起点市值 {cap(c['start_market_cap'])}</em>
        </a>
        """
        for c in companies
    )
    rows = "\n".join(
        f"""
        <tr>
          <td>{dashboard_company_cell(c)}</td>
          <td>{c['track']}</td>
          <td class="baseline metric-cell">{c.get('start_date', '2026-07-17')}</td>
          <td class="baseline metric-cell">{price(c['start_price'])}</td>
          <td class="baseline metric-cell">{cap(c['start_market_cap'])}</td>
          <td class="metric-cell">{price(c.get('current_price', c['start_price']))}</td>
          <td class="metric-cell">{cap(c['current_market_cap'])}</td>
          <td class="metric-cell">{c['change_from_start']}</td>
          <td class="metric-cell">{ranked_metric(c.get('drawdown_from_recent_high', '-'), 'down', c.get('drawdown_rank'))}</td>
          <td class="metric-cell">{cap(c['year_end_market_cap'])}</td>
          <td class="metric-cell">{ranked_metric(c['space'], 'up', c.get('upside_rank'))}</td>
          <td>{c['source_note']}</td>
        </tr>
        """
        for c in dashboard_companies
    )
    company_views = "\n".join(
        f"""
        <article class="view research-article" id="{c['id']}">
          <div class="article-head">
            <div>
              <p class="eyebrow">{c['code']} · {c['track']}</p>
              <h1>{c['name']}</h1>
            </div>
          </div>
          <div class="markdown-body">{c['content']}</div>
        </article>
        """
        for c in companies
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{SITE_TITLE}</title>
  <style>{base_css()}</style>
</head>
<body>
  <div class="mobile-bar">
    <strong>{SITE_TITLE}</strong>
    <select aria-label="快速跳转" id="mobileNav">
      <option value="home">README 首页</option>
      <option value="dashboard">公司池仪表盘</option>
      <option value="weekly">周度观察</option>
      {mobile_options}
    </select>
  </div>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <strong>{SITE_TITLE}</strong>
        <span>单文件内容切换版 · 本地静态原型</span>
      </div>
      {nav_main}
      <div class="nav-section-title">公司资料</div>
      {nav_companies}
    </aside>
    <main class="content">
      <div class="view" id="home">
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
            <div class="metric"><span>页面结构</span><strong>单文件切换</strong></div>
          </div>
        </header>
        <section>
          <div class="section-head">
            <div>
              <p class="eyebrow">Market Structure</p>
              <h2>AI 市场中的的资金机制观察</h2>
              <p>当前 AI 驱动的牛市并非纯粹由基本面支撑，而是由动量交易（Momentum Trading）自我强化机制推动。当市场上涨过度集中于少数龙头（如美股“七姐妹”、韩国三星/海力士）时，一旦基本面出现裂缝，动量反转将触发<strong>连锁式去杠杆</strong>，导致踩踏式下跌。韩国市场因结构更脆弱，风险高于美国。</p>
              <p>每一轮大行情都需要一个真实的基本面方向。没有 AI 产业趋势，就不会有最早的一批买家；没有利润和资本开支的兑现，趋势也不可能维持这么久。牛市里，基本面负责点火，资金结构决定火势。消息制造第一批买家，业绩排名、基准压力和产品规则制造后面的买家。下跌时也是一样：消息制造第一批卖家，趋势、波动率、融资和赎回制造后面的卖家。所以动量把牛市推高后，也必然会把下跌变成踩踏，这是机制决定的。</p>
              <p>虽然吴梓豪大佬的逻辑扎实，AI 依然是未来，但股市里的 AI，需要一百分的谨慎。</p>
            </div>
          </div>
        </section>
        <section>
          <div class="section-head">
            <div>
              <p class="eyebrow">Source Image</p>
              <h2>吴梓豪 2026H2 投资建议图片</h2>
              <p>原图作为首页研究来源展示区保留，表格中的「目前市值」「年底市值」「目前至年底空间」用于第一版仪表盘的起点数据。</p>
            </div>
          </div>
          <div class="source-image">
            <img src="{image_src}" alt="吴梓豪2026H2 A+H股投资建议原图">
            <p class="note">来源标注：吴梓豪「半导体大佬的会议室」2026H2 A+H 股投资建议。页面仅作个人研究归档与跟踪。</p>
          </div>
        </section>
        <section>
          <div class="section-head">
            <div>
              <p class="eyebrow">Company Pool</p>
              <h2>8 家公司资料入口</h2>
              <p>点击公司卡片会在当前 HTML 中切换到对应公司资料，不跳到新网页，也不会滚动到长页面下方。</p>
            </div>
          </div>
          <div class="company-grid">{cards}</div>
        </section>
      </div>

      <section class="view" id="dashboard">
        <div class="section-head">
          <div>
            <p class="eyebrow">Dashboard</p>
            <h1>公司池市值跟踪仪表盘</h1>
            <p>原 8 家公司以 2026-07-17 为起点；后续从新图新增的公司以 2026-07-25 为起点。灰色列为起点数据；行情日收盘价和市值来自本地行情快照，后续每周更新后记录「距起点变化」「距最高点下跌幅度」和「距 2026 年底目标市值空间」。</p>
            <p>{market_note}</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th style="width:140px;">公司</th>
                <th style="width:150px;">强相关方向</th>
                <th class="baseline metric-cell">起点<br>日期</th>
                <th class="baseline metric-cell">起点<br>股价</th>
                <th class="baseline metric-cell">起点<br>市值</th>
                <th class="metric-cell">{quote_day}<br>收盘价</th>
                <th class="metric-cell">{quote_day}<br>市值</th>
                <th class="metric-cell">距起点<br>变化</th>
                <th class="metric-cell">距最高点<br>下跌幅度</th>
                <th class="metric-cell">2026 年底<br>目标市值</th>
                <th class="metric-cell">目前至<br>年底空间</th>
                <th style="width:300px;">原图说明摘录</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <p class="note">「距最高点下跌幅度」按最近 2 个月日线最高股价直接计算；「目标市值」仅用于记录原图中的年底目标市值，不代表投资建议；页面不展示基本面评级、估值高低判断或价格走势图。</p>
      </section>

      <section class="view" id="weekly">
        <div class="section-head">
          <div>
            <p class="eyebrow">Weekly Monitor</p>
            <h1>周度市场观察记录</h1>
            <p>自动扫描 Annettehub/ai-investing 中与 8 家公司或强相关产业链有关的记录，推入市场观察和公司观察。这里只记录事实与来源，不写买卖判断。</p>
            <p>{weekly_note}</p>
          </div>
        </div>
        <div class="weekly">
          <div class="monitor-box">
            <h3>市场观察</h3>
            {market_observation_html}
          </div>
          <div class="monitor-box">
            <h3>公司观察</h3>
            {company_observation_html}
          </div>
        </div>
      </section>

      {company_views}
    </main>
  </div>
  <script>
    const views = Array.from(document.querySelectorAll(".view"));
    const navLinks = Array.from(document.querySelectorAll("[data-target]"));
    const mobileNav = document.getElementById("mobileNav");
    const validIds = new Set(views.map((view) => view.id));

    function activate(id) {{
      const target = validIds.has(id) ? id : "home";
      views.forEach((view) => view.classList.toggle("active", view.id === target));
      navLinks.forEach((link) => link.classList.toggle("active", link.dataset.target === target));
      if (mobileNav) mobileNav.value = target;
      document.querySelector(".content").scrollTop = 0;
      window.scrollTo(0, 0);
    }}

    window.addEventListener("hashchange", () => activate(location.hash.slice(1)));
    if (mobileNav) {{
      mobileNav.addEventListener("change", () => {{
        location.hash = mobileNav.value;
      }});
    }}
    activate(location.hash.slice(1));
  </script>
</body>
</html>
"""


def write_single_page(base: Path, companies: list[dict], dashboard_companies: list[dict]) -> None:
    html_text = render(companies, dashboard_companies)
    (base / TARGET_HTML).write_text(html_text, encoding="utf-8", newline="\n")
    (base / "index.html").write_text(html_text, encoding="utf-8", newline="\n")


def main() -> None:
    companies = prepare()
    trim_repeated_company_heading(companies)
    dashboard_companies = prepare_dashboard_companies(companies)
    write_single_page(OUTPUTS, companies, dashboard_companies)
    write_single_page(DEST, companies, dashboard_companies)


if __name__ == "__main__":
    main()
