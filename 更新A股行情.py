from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


LOCAL_PROJECT_DIR = Path(r"D:\WorkBuddy\Claw\2026-07-16-08-52-07")
if os.environ.get("TRACKER_PROJECT_DIR"):
    PROJECT_DIR = Path(os.environ["TRACKER_PROJECT_DIR"]).resolve()
elif LOCAL_PROJECT_DIR.exists():
    PROJECT_DIR = LOCAL_PROJECT_DIR.resolve()
else:
    PROJECT_DIR = Path(__file__).resolve().parent

BUILD_SCRIPT = PROJECT_DIR / "build_single_page_research_site.py"
if not BUILD_SCRIPT.exists():
    BUILD_SCRIPT = Path(r"C:\Users\Annette Zhang\Documents\Codex\2026-07-18\referenced-chatgpt-conversation-this-is-untrusted\work\build_single_page_research_site.py")
LOG_FILE = PROJECT_DIR / "行情更新日志.txt"

COMPANIES = [
    {"code": "300602", "market": "SZ", "name": "飞荣达", "start_market_cap_yi": 214.7},
    {"code": "601869", "market": "SH", "name": "长飞光纤", "start_market_cap_yi": 2993.0},
    {"code": "300476", "market": "SZ", "name": "胜宏科技", "start_market_cap_yi": 2373.0},
    {"code": "002384", "market": "SZ", "name": "东山精密", "start_market_cap_yi": 4431.0},
    {"code": "688256", "market": "SH", "name": "寒武纪", "start_market_cap_yi": 7480.0},
    {"code": "002463", "market": "SZ", "name": "沪电股份", "start_market_cap_yi": 2459.0},
    {"code": "300308", "market": "SZ", "name": "中际旭创", "start_market_cap_yi": 10900.0},
    {"code": "603986", "market": "SH", "name": "兆易创新", "start_market_cap_yi": 3250.0},
]

TENCENT_PREFIX = {"SZ": "sz", "SH": "sh"}
EASTMONEY_PREFIX = {"SZ": "0.", "SH": "1."}


def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
        }
    )
    return s


def fetch_tencent_quote(item: dict, s: requests.Session) -> dict:
    symbol = TENCENT_PREFIX[item["market"]] + item["code"]
    url = f"https://qt.gtimg.cn/q={symbol}"
    response = s.get(url, timeout=15)
    response.raise_for_status()
    text = response.content.decode("gbk", errors="ignore")
    payload = text.split('="', 1)[1].rstrip('";')
    fields = payload.split("~")
    price = float(fields[3])
    market_cap_yi = float(fields[45])
    quote_time_raw = fields[30]
    quote_time = datetime.strptime(quote_time_raw, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
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
    try:
        response = s.get("https://push2.eastmoney.com/api/qt/stock/get", params=params, timeout=15)
        response.raise_for_status()
        data = response.json().get("data") or {}
        value = data.get("f116")
        if value in (None, "-"):
            return None
        return float(value) / 100000000
    except Exception:
        return None


def retry(fn, attempts: int = 3):
    last_error = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as error:
            last_error = error
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def main() -> None:
    quotes = {}
    checks = []
    s = session()

    for item in COMPANIES:
        quote = retry(lambda item=item: fetch_tencent_quote(item, s))
        em_cap = fetch_eastmoney_market_cap_yi(item, s)
        if em_cap is None:
            quote["eastmoney_check"] = "not_available"
            checks.append(f"{item['name']}: 东方财富校验未返回")
        else:
            diff_pct = abs(quote["market_cap_yi"] - em_cap) / quote["market_cap_yi"] * 100
            quote["eastmoney_market_cap_yi"] = round(em_cap, 2)
            quote["eastmoney_diff_pct"] = round(diff_pct, 3)
            quote["eastmoney_check"] = "pass" if diff_pct <= 0.2 else "review"
            if diff_pct > 0.2:
                checks.append(f"{item['name']}: 双源总市值差异 {diff_pct:.2f}%")
        quotes[item["code"]] = quote

    validation = "双源可用时要求总市值差异不超过 0.2%；校验源不可用时保留主源并提示。"
    if checks:
        validation += " " + "；".join(checks)

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "primary_source": "Tencent qt.gtimg.cn",
        "secondary_source": "Eastmoney push2.eastmoney.com",
        "validation": validation,
        "quotes": quotes,
    }
    (PROJECT_DIR / "market-data.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True)
    lines = [
        f"更新时间：{output['updated_at']}",
        f"主源：{output['primary_source']}",
        f"校验源：{output['secondary_source']}",
        f"网页：{PROJECT_DIR / '2026 H2 吴梓豪A股公司追踪 2026.7.html'}",
        "",
        "本次行情：",
    ]
    for quote in quotes.values():
        lines.append(f"- {quote['name']} {quote['code']}：价格 {quote['price']}，总市值 {quote['market_cap_yi']:.2f} 亿，行情时间 {quote['quote_time']}")
    lines.extend(["", "校验说明：", output["validation"]])
    LOG_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
