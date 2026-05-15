import json
import re
from pathlib import Path
from collections import defaultdict
from lxml import etree
from selenium.common.exceptions import TimeoutException
from crazydriver import CrazyDriver, By

KEYWORD = "lash extension"

SAVE_DIR = Path.cwd() / KEYWORD.replace(" ", "_")
if not SAVE_DIR.exists():
    SAVE_DIR.mkdir(parents=True)

SEARCH_ASINS_PATH = SAVE_DIR / "search_asins.json"
SIBLING_ASINS_PATH = SAVE_DIR / "sibling_asins.json"
PRODUCT_INFO_PATH = SAVE_DIR / "product_info.json"

driver = CrazyDriver()


def get_product_info(asin: str) -> dict:
    """打开商品详情页，用 lxml 从 ``page_source`` 解析标题与主价文案。"""
    global driver
    url = f"https://www.amazon.com/dp/{asin}"
    driver.get(url)
    try:
        driver.explicit_wait(By.XPATH, "//*[@id='productTitle']", seconds=10)
        driver.explicit_wait(
            By.XPATH, "//span[@id='apex-pricetopay-accessibility-label']", seconds=10)
    except TimeoutException:
        # 节点未在时限内出现仍解析已加载 HTML，部分页面仍可抠出标题或价。
        pass
    root = etree.HTML(driver.page_source)
    t = root.xpath("//*[@id='productTitle']")
    p = root.xpath(
        "//*[@id='apex-pricetopay-accessibility-label']")
    title = (t[0].text or "").strip() if t else ""
    price = (p[0].text or "").strip() if p else ""

    best_sellers_rank = ""
    for li in root.xpath("//*[@id='detailBullets_feature_div']/ul/li"):
        if not any(s.strip() == "Best Sellers Rank:" for s in li.xpath(".//text()")):
            continue
        best_sellers_rank = " ".join(
            [i.strip() for i in li.xpath(".//text()")[2:] if i.strip()])
        break
    return {
        "asin": asin,
        "url": url,
        "title": title,
        "price": price,
        "best_sellers_rank": best_sellers_rank,
    }


assert SIBLING_ASINS_PATH.exists(), "sibling_asins.json 不存在"

with open(SIBLING_ASINS_PATH, "r", encoding="utf-8") as f:
    all_sibling_asins = json.load(f)

try:
    with open(PRODUCT_INFO_PATH, "r", encoding="utf-8") as f:
        product_info = defaultdict(list, json.load(f))
except FileNotFoundError:
    product_info = defaultdict(list)

# sibling_asins 包含 original_asin。
original_asin: str
raw_sibling_asins: dict[str, list[str]]
for original_asin, raw_sibling_asins in all_sibling_asins.items():
    sibling_asins = raw_sibling_asins.keys() if raw_sibling_asins else [
        original_asin]

    have_asins = {
        info["asin"] for info in product_info[original_asin] if info is not None
    }
    for asin in sibling_asins:
        if asin in have_asins:
            print(f"exists: {original_asin} -> {asin}")
            continue
        this_product_info = get_product_info(asin)
        this_product_info["tags"] = raw_sibling_asins.get(asin, [])
        product_info[original_asin].append(this_product_info)
        with open(PRODUCT_INFO_PATH, "w", encoding="utf-8") as f:
            json.dump(product_info, f, ensure_ascii=False, indent=4)
        print(f"{asin} -> {this_product_info}")
