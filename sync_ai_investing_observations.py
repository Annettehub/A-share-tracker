from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(os.environ.get("TRACKER_PROJECT_DIR", Path(__file__).resolve().parent)).resolve()
CACHE_DIR = PROJECT_DIR / ".cache" / "ai-investing"
OUTPUT_FILE = PROJECT_DIR / "weekly-observations.json"
REPO_URL = "https://github.com/Annettehub/ai-investing.git"
REPO_WEB = "https://github.com/Annettehub/ai-investing"

COMPANY_KEYWORDS = {
    "飞荣达": ["飞荣达", "300602"],
    "长飞光纤": ["长飞光纤", "YOFC", "601869", "06869"],
    "胜宏科技": ["胜宏科技", "胜宏", "300476"],
    "东山精密": ["东山精密", "东山", "002384", "苏州东山"],
    "寒武纪": ["寒武纪", "688256", "HWJ"],
    "沪电股份": ["沪电股份", "沪电", "002463"],
    "中际旭创": ["中际旭创", "Innolight", "300308"],
    "兆易创新": ["兆易创新", "GigaDevice", "603986"],
    "伟测科技": ["伟测科技", "伟测", "688372"],
    "联讯仪器": ["联讯仪器", "联讯", "688808"],
    "紫光股份": ["紫光股份", "新华三", "H3C", "000938"],
    "长芯博创": ["长芯博创", "300548"],
    "三环集团": ["三环集团", "三环", "MLCC", "300408"],
}

INDUSTRY_KEYWORDS = {
    "AI算力/CAPEX": ["AI CAPEX", "capex", "CAPEX", "算力", "智算", "数据中心", "AI 基础设施", "AI基础设施", "云厂商", "CSP", "NeoCloud"],
    "光模块/CPO": ["光模块", "光互联", "光通信", "800G", "1.6T", "CPO", "硅光", "光引擎", "OIO"],
    "AI PCB": ["AI PCB", "PCB", "HDI", "背板", "Rubin", "Blackwell", "服务器板"],
    "液冷/散热": ["液冷", "散热", "电磁屏蔽", "热管理"],
    "存储/HBM": ["存储", "HBM", "DRAM", "NAND", "DDR5", "SSD", "QLC", "长江存储", "三星", "海力士", "Micron", "美光"],
    "AI芯片/国产替代": ["AI芯片", "AI 芯片", "国产替代", "昇腾", "升腾", "华为", "ASIC", "Chiplet"],
    "半导体测试/仪器": ["测试", "封测", "探针卡", "ATE", "示波器", "误码仪", "测量仪器", "联讯仪器", "伟测科技"],
    "被动元件/MLCC": ["被动元件", "MLCC", "陶瓷件", "陶瓷插芯", "三环集团"],
}

TEXT_SUFFIXES = {".md", ".txt"}
EXCLUDED_PARTS = {".git", "node_modules", ".next", "dist", "build", "99-backup", "site", "value-investing"}
INCLUDED_TOP_LEVEL = {"02-kb", "03-raw", "04-output", "config"}


def run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return result.stdout.strip()


def refresh_repo() -> None:
    CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
    if (CACHE_DIR / ".git").exists():
        try:
            run_git(["fetch", "--depth=1", "origin", "main"], CACHE_DIR)
            run_git(["reset", "--hard", "origin/main"], CACHE_DIR)
        except subprocess.CalledProcessError as error:
            print(f"ai-investing 刷新失败，使用本地缓存：{error.stderr.strip() if error.stderr else error}")
    else:
        run_git(["clone", "--depth=1", REPO_URL, str(CACHE_DIR)])


def current_commit() -> str:
    return run_git(["rev-parse", "HEAD"], CACHE_DIR)


def last_commit_time(relative_path: str) -> str:
    value = run_git(["log", "-1", "--format=%cI", "--", relative_path], CACHE_DIR)
    return value or ""


def relevant_files() -> list[Path]:
    files: list[Path] = []
    for path in CACHE_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(CACHE_DIR)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.parts[0] not in INCLUDED_TOP_LEVEL:
            continue
        if relative.name in {"index.md", "log.md"}:
            continue
        if "模板" in relative.name or "检查清单" in relative.name:
            continue
        if relative.parts[0] == "config" and relative.name != "watchlist.md":
            continue
        files.append(path)
    return files


def title_from_text(text: str, fallback: str) -> str:
    frontmatter_title = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.MULTILINE)
    if frontmatter_title:
        return frontmatter_title.group(1).strip()
    heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if heading:
        return heading.group(1).strip()
    return fallback


def clean_snippet(text: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_>#|\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:220] + ("..." if len(text) > 220 else "")


def text_blocks(text: str) -> list[str]:
    blocks = []
    for raw in re.split(r"\n\s*\n", text):
        block = raw.strip()
        if not block or block.startswith("---"):
            continue
        blocks.append(block)
    return blocks


def matched_keywords(text: str, groups: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    lowered = text.lower()
    for label, words in groups.items():
        if any(word.lower() in lowered for word in words):
            matches.append(label)
    return matches


def source_url(commit: str, relative_path: str) -> str:
    return f"{REPO_WEB}/blob/{commit}/{quote(relative_path.replace(os.sep, '/'), safe='/')}"


def build_item(path: Path, block: str, commit: str, keyword_labels: list[str], company: str | None = None) -> dict:
    relative = path.relative_to(CACHE_DIR).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "company": company,
        "title": title_from_text(text, path.stem),
        "source_path": relative,
        "source_url": source_url(commit, relative),
        "source_commit_time": last_commit_time(relative),
        "matched_keywords": keyword_labels[:5],
        "snippet": clean_snippet(block),
    }


def candidate_blocks(path: Path, text: str) -> list[str]:
    return text_blocks(text)


def fallback_block(text: str) -> str:
    for block in text_blocks(text):
        if block.startswith("#") or block.startswith("title:"):
            continue
        return block
    return text[:500]


def best_matching_block(text: str, groups: dict[str, list[str]]) -> str:
    for block in text_blocks(text):
        if block.startswith("#") or block.startswith("title:"):
            continue
        if len(clean_snippet(block)) < 30:
            continue
        if matched_keywords(block, groups):
            return block
    return fallback_block(text)


def is_false_company_match(company: str, block: str) -> bool:
    if company == "寒武纪" and "寒武纪时期" in block:
        context_words = ["688256", "AI芯片", "AI 芯片", "国产", "昇腾", "升腾", "海光", "字节"]
        return not any(word in block for word in context_words)
    return False


def scan() -> dict:
    refresh_repo()
    commit = current_commit()
    market_items: list[dict] = []
    company_items: dict[str, list[dict]] = {company: [] for company in COMPANY_KEYWORDS}
    seen = set()

    for path in relevant_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        file_text = f"{path.relative_to(CACHE_DIR).as_posix()}\n{text}"
        market_labels = matched_keywords(file_text, INDUSTRY_KEYWORDS)

        for company, keywords in COMPANY_KEYWORDS.items():
            company_groups = {company: keywords}
            if not matched_keywords(file_text, company_groups):
                continue
            best_block = best_matching_block(text, company_groups)
            industry_labels = matched_keywords(best_block, INDUSTRY_KEYWORDS)
            if is_false_company_match(company, best_block):
                continue
            labels = [company, *industry_labels]
            key = ("company", company, path.relative_to(CACHE_DIR).as_posix(), clean_snippet(best_block)[:80])
            if key not in seen and len(company_items[company]) < 3:
                seen.add(key)
                company_items[company].append(build_item(path, best_block, commit, labels, company))

        if market_labels and path.relative_to(CACHE_DIR).parts[0] != "config":
            best_block = best_matching_block(text, INDUSTRY_KEYWORDS)
            key = ("market", path.relative_to(CACHE_DIR).as_posix(), clean_snippet(best_block)[:80])
            if key not in seen:
                seen.add(key)
                market_items.append(build_item(path, best_block, commit, market_labels))

    def sort_key(item: dict) -> tuple[str, str]:
        return (item.get("source_commit_time") or "", item.get("source_path") or "")

    market_items = sorted(market_items, key=sort_key, reverse=True)[:10]
    for company, items in company_items.items():
        company_items[company] = sorted(items, key=sort_key, reverse=True)[:3]

    return {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_repo": "Annettehub/ai-investing",
        "source_repo_url": REPO_WEB,
        "source_commit": commit,
        "market_observations": market_items,
        "company_observations": company_items,
    }


def main() -> None:
    data = scan()
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    market_count = len(data["market_observations"])
    company_count = sum(len(items) for items in data["company_observations"].values())
    print(f"已同步 ai-investing 观察：市场 {market_count} 条，公司 {company_count} 条。")
    print(f"来源提交：{data['source_commit']}")


if __name__ == "__main__":
    main()
