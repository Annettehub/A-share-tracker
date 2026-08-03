from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from zoneinfo import ZoneInfo

    _SH = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover
    _SH = None


def now_shanghai() -> datetime:
    return datetime.now(_SH) if _SH else datetime.now()


def today_str() -> str:
    return now_shanghai().strftime("%Y-%m-%d")


PROJECT_DIR = Path(os.environ.get("TRACKER_PROJECT_DIR", Path(__file__).resolve().parent)).resolve()
BUILD_SCRIPT = PROJECT_DIR / "build_single_page_research_site.py"
SYNC_OBSERVATIONS_SCRIPT = PROJECT_DIR / "sync_ai_investing_observations.py"
LOG_FILE = PROJECT_DIR / "行情更新日志.txt"
MARKET_DATA = PROJECT_DIR / "market-data.json"
SKIP_REASON = PROJECT_DIR / "SKIP_REASON.txt"

COMPANIES = [
    {"code": "300602", "market": "SZ", "name": "飞荣达", "start_market_cap_yi": 214.7},
    {"code": "601869", "market": "SH", "name": "长飞光纤", "start_market_cap_yi": 2993.0},
    {"code": "300476", "market": "SZ", "name": "胜宏科技", "start_market_cap_yi": 2373.0},
    {"code": "002384", "market": "SZ", "name": "东山精密", "start_market_cap_yi": 4431.0},
    {"code": "688256", "market": "SH", "name": "寒武纪", "start_market_cap_yi": 7480.0},
    {"code": "002463", "market": "SZ", "name": "沪电股份", "start_market_cap_yi": 2459.0},
    {"code": "300308", "market": "SZ", "name": "中际旭创", "start_market_cap_yi": 10900.0},
    {"code": "603986", "market": "SH", "name": "兆易创新", "start_market_cap_yi": 3250.0},
    {"code": "688372", "market": "SH", "name": "伟测科技", "start_market_cap_yi": 204.0},
    {"code": "688808", "market": "SH", "name": "联讯仪器", "start_market_cap_yi": 1628.7},
    {"code": "000938", "market": "SZ", "name": "紫光股份", "start_market_cap_yi": 1004.7},
    {"code": "300548", "market": "SZ", "name": "长芯博创", "start_market_cap_yi": 490.0},
    {"code": "300408", "market": "SZ", "name": "三环集团", "start_market_cap_yi": 1968.2},
]

TENCENT_PREFIX = {"SZ": "sz", "SH": "sh"}
EASTMONEY_PREFIX = {"SZ": "0.", "SH": "1."}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _ua() -> str:
    return random.choice(USER_AGENTS)


def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    return s


def fetch_tencent_quote(item: dict, s: requests.Session) -> dict:
    symbol = TENCENT_PREFIX[item["market"]] + item["code"]
    response = s.get(
        f"https://qt.gtimg.cn/q={symbol}",
        timeout=15,
        headers={"User-Agent": _ua(), "Referer": "https://gu.qq.com/"},
    )
    response.raise_for_status()
    text = response.content.decode("gbk", errors="ignore")
    payload = text.split('="', 1)[1].rstrip('";')
    fields = payload.split("~")
    price = float(fields[3])
    market_cap_yi = float(fields[45])
    quote_time = datetime.strptime(fields[30], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    return {
        "code": item["code"],
        "name": item["name"],
        "price": price,
        "market_cap_yi": market_cap_yi,
        "quote_time": quote_time,
        "source": "Tencent qt.gtimg.cn",
    }


def fetch_eastmoney_market_cap_yi(item: dict, s: requests.Session) -> float | None:
    secid = EASTMONEY_PREFIX[item["market"]] + item["code"]
    params = {
        "secid": secid,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "invt": "2",
        "fltt": "2",
        "fields": "f43,f57,f86,f116",
    }
    last_error = None
    for attempt in range(3):
        try:
            response = s.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params=params,
                timeout=15,
                headers={"User-Agent": _ua(), "Referer": "https://quote.eastmoney.com/"},
            )
            response.raise_for_status()
            data = response.json().get("data") or {}
            value = data.get("f116")
            if value in (None, "-"):
                return None
            return float(value) / 100000000
        except Exception as error:
            last_error = error
            time.sleep(1 + attempt * 1 + random.random())
    return None


def fetch_sina_price(item: dict, s: requests.Session) -> float | None:
    prefix = TENCENT_PREFIX[item["market"]]
    symbol = prefix + item["code"]
    try:
        response = s.get(
            f"https://hq.sinajs.cn/list={symbol}",
            timeout=15,
            headers={"User-Agent": _ua(), "Referer": "https://finance.sina.com.cn/"},
        )
        response.raise_for_status()
        response.encoding = "gbk"
        match = re.search(r'"([^"]+)"', response.text)
        if not match:
            return None
        parts = match.group(1).split(",")
        if len(parts) < 4:
            return None
        return float(parts[3])
    except Exception:
        return None


def fetch_tencent_recent_high(item: dict, quote: dict, s: requests.Session) -> dict:
    symbol = TENCENT_PREFIX[item["market"]] + item["code"]
    quote_date = datetime.strptime(quote["quote_time"][:10], "%Y-%m-%d").date()
    start_date = quote_date - timedelta(days=62)
    params = {"param": f"{symbol},day,,,1000,qfq"}
    response = s.get(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params=params,
        timeout=20,
        headers={"User-Agent": _ua(), "Referer": "https://gu.qq.com/"},
    )
    response.raise_for_status()
    data = response.json().get("data", {}).get(symbol, {})
    klines = data.get("qfqday") or data.get("day") or []
    rows = []
    for line in klines:
        if len(line) < 5:
            continue
        trade_date = datetime.strptime(line[0], "%Y-%m-%d").date()
        if start_date <= trade_date <= quote_date:
            rows.append({"date": line[0], "close": float(line[2]), "high": float(line[3])})
    if not rows:
        raise ValueError(f"{item['name']}: 最近 2 个月日线为空")
    high_row = max(rows, key=lambda row: row["high"])
    high_price = float(high_row["high"])
    drawdown = (float(quote["price"]) - high_price) / high_price * 100
    return {
        "recent_high_window_start": start_date.strftime("%Y-%m-%d"),
        "recent_high_window_end": quote_date.strftime("%Y-%m-%d"),
        "recent_high_date": high_row["date"],
        "recent_high_price": round(high_price, 2),
        "drawdown_from_recent_high_pct": round(drawdown, 3),
        "recent_high_source": "Tencent daily kline qfq endpoint",
    }


def retry(fn, attempts: int = 3):
    last_error = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as error:
            last_error = error
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def already_updated_today() -> bool:
    if not MARKET_DATA.exists():
        return False
    try:
        data = json.loads(MARKET_DATA.read_text(encoding="utf-8"))
    except Exception:
        return False
    quotes = data.get("quotes", {})
    if not quotes:
        return False
    dates = [q.get("quote_time", "")[:10] for q in quotes.values() if q.get("quote_time")]
    if not dates:
        return False
    return max(dates) == today_str()


def is_trading_day_today(s: requests.Session) -> bool:
    """用一只股票探测今日是否有 A 股行情；探测失败则不跳过，交由主流程报错。"""
    item = COMPANIES[0]
    try:
        q = fetch_tencent_quote(item, s)
    except Exception:
        return True
    return q["quote_time"][:10] == today_str()


def main() -> None:
    if os.environ.get("FORCE_UPDATE") != "1" and already_updated_today():
        SKIP_REASON.write_text(f"今日已更新（{today_str()}），跳过。", encoding="utf-8")
        print("今日已更新，跳过。")
        return

    s = session()
    if not is_trading_day_today(s):
        SKIP_REASON.write_text(f"非交易日（{today_str()} 无 A 股行情），跳过。", encoding="utf-8")
        print("非交易日，跳过。")
        return

    if SKIP_REASON.exists():
        SKIP_REASON.unlink()

    quotes = {}
    checks = []

    for item in COMPANIES:
        quote = retry(lambda item=item: fetch_tencent_quote(item, s))
        try:
            quote.update(retry(lambda item=item, quote=quote: fetch_tencent_recent_high(item, quote, s)))
        except Exception as error:
            quote["recent_high_error"] = str(error)
            checks.append(f"{item['name']}: 最近 2 个月最高价未返回")

        em_cap = fetch_eastmoney_market_cap_yi(item, s)
        if em_cap is None:
            quote["eastmoney_check"] = "not_available"
            checks.append(f"{item['name']}: 东方财富市值校验未返回")
        else:
            diff_pct = abs(quote["market_cap_yi"] - em_cap) / quote["market_cap_yi"] * 100
            quote["eastmoney_market_cap_yi"] = round(em_cap, 2)
            quote["eastmoney_diff_pct"] = round(diff_pct, 3)
            quote["eastmoney_check"] = "pass" if diff_pct <= 0.2 else "review"
            if diff_pct > 0.2:
                checks.append(f"{item['name']}: 双源总市值差异 {diff_pct:.2f}%")

        sina_price = fetch_sina_price(item, s)
        if sina_price is not None:
            pdiff = abs(quote["price"] - sina_price) / quote["price"] * 100
            quote["sina_price"] = round(sina_price, 2)
            quote["sina_diff_pct"] = round(pdiff, 3)
            quote["sina_check"] = "pass" if pdiff <= 0.5 else "review"
            if pdiff > 0.5:
                checks.append(f"{item['name']}: 腾讯/新浪现价差异 {pdiff:.2f}%")

        quotes[item["code"]] = quote

    # 关键校验：缺数据直接失败，让 GitHub 发送失败邮件（用户无需手动检查）
    if len(quotes) != len(COMPANIES):
        raise SystemExit(f"公司数量异常：获取到 {len(quotes)} 家，期望 {len(COMPANIES)} 家")
    for code, q in quotes.items():
        if q.get("price") is None or q.get("market_cap_yi") is None:
            raise SystemExit(f"{q.get('name')}：价格或市值缺失，终止更新")

    validation = "双源可用时要求总市值差异不超过 0.2%；校验源不可用时保留主源并提示。"
    if checks:
        validation += " " + "；".join(checks)

    output = {
        "updated_at": now_shanghai().strftime("%Y-%m-%d %H:%M:%S"),
        "primary_source": "Tencent qt.gtimg.cn",
        "secondary_source": "Eastmoney push2.eastmoney.com / Sina hq.sinajs.cn",
        "validation": validation,
        "quotes": quotes,
    }
    MARKET_DATA.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    observations_status = "未找到 ai-investing 观察同步脚本。"
    if SYNC_OBSERVATIONS_SCRIPT.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(SYNC_OBSERVATIONS_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            observations_status = result.stdout.strip() or "ai-investing 观察已同步。"
        except Exception as error:
            observations_status = f"ai-investing 观察同步失败，已继续更新行情：{error}"

    subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True)

    lines = [
        f"更新时间：{output['updated_at']}",
        f"主源：{output['primary_source']}",
        f"校验源：{output['secondary_source']}",
        f"网页：{PROJECT_DIR / '2026 H2 吴梓豪A股公司追踪 2026.7.html'}",
        f"ai-investing观察：{observations_status}",
        "",
        "本次行情：",
    ]
    for quote in quotes.values():
        high_text = "最高价未返回"
        if quote.get("recent_high_price") is not None:
            high_text = (
                f"近 2 个月最高价 {quote['recent_high_price']}（{quote.get('recent_high_date', '')}），"
                f"距高点 {quote.get('drawdown_from_recent_high_pct', 0):+.1f}%"
            )
        lines.append(
            f"- {quote['name']} {quote['code']}：价格 {quote['price']}，"
            f"总市值 {quote['market_cap_yi']:.2f} 亿，行情时间 {quote['quote_time']}，{high_text}"
        )
    lines.extend(["", "校验说明：", output["validation"]])
    LOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
