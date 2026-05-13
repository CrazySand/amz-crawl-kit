"""
# 无子选项：https://www.amazon.com/dp/B0BX418N68
# 一个子选项：https://www.amazon.com/dp/B07Z7FSHL8
# 两个子选项：https://www.amazon.com/dp/B0G6CV4D4C

['B0G6CV4D4C', 'B0G6CY2SDQ', 'B0FKMKX4FH', 'B0FKMDTK89', 'B0DNJRTM35', 'B0DNJSGDX2', 'B0FKMF8YD8', 'B0FKMJZG9L',
    'B0DNJSY31C', 'B0DNJTLH9V', 'B0G6CV4D4C', 'B0DNJSY31C', 'B0FXX1H25B', 'B0FXWZ4GC7', 'B0FXWZ2XPQ', 'B0FXX243RL']

{
    "asin": "B0FJ1Y7WKR",
    "url": "https://www.amazon.com/dp/B0FJ1Y7WKR",
    "title": "FADLASH Premade Lash Fans D Curl Premade Fans Eyelash Extensions 16D 0.07 Volume Lash Fans Premade Handmade Premade Lash Extensions Fans (16D-07D, Camellia)",
    "price": "$9.99"
}
"""

import os
import json
from collections import defaultdict
from lxml import etree
from selenium.common.exceptions import TimeoutException
from crazydriver import CrazyDriver, By

driver = CrazyDriver()

# ====================================================
# 工具


def iter_search_asins_by_page(keyword: str):
    """在 Selenium 控制的浏览器中按页抓取亚马逊搜索结果的 ASIN。

    本函数为**生成器**：每执行一次 ``next()``（或 ``for`` 循环前进一步），
    会使用全局 ``driver`` 打开对应页码的搜索 URL，即完成一次**搜索翻页**；
    随后从当前页解析 ``data-asin``，将**本页**得到的 ASIN 列表 ``yield``
    给调用方。

    当某一页无法解析出任何 ASIN 时，生成器结束（不再继续翻页）。

    Args:
        keyword: 搜索关键词，用于构造 ``https://www.amazon.com/s?k=...&page=...``。

    Yields:
        当前页提取到的 ASIN 字符串列表；无 ASIN 时不再产出并结束。
    """
    page = 1
    while True:
        url = f"https://www.amazon.com/s?k={keyword}&page={page}"
        driver.get(url)  # 访问搜索页面
        items = driver.explicit_waits(By.XPATH, "//div[@role='listitem']")
        asins = [item.get_attribute('data-asin')
                 for item in items if item.get_attribute('data-asin')]
        # 若本页解析不到 ASIN，视为已无后续商品页，结束生成器。
        if not asins:
            return
        yield asins
        page += 1


def get_product_sibling_asins(asin: str) -> list[str]:
    """根据商品 ASIN 抓取详情页上「变体/子款式」对应的兄弟 ASIN 列表。

    打开 ``https://www.amazon.com/dp/{asin}``，在页面中的变体选择区域
    （``tp-inline-twister-dim-values-container`` 下的 ``ul/li``）读取每个选项的
    ``data-asin``，视为与当前商品同属一变体维度的子 ASIN（彼此为兄弟关系）。

    不去区分具体维度（颜色、尺码等），统一收集上述 ``li`` 上所有非空的
    ``data-asin``，去重后返回。

    Args:
        asin: 当前亚马逊商品 ASIN，作为详情页路径参数。

    Returns:
        从变体列表中解析出的兄弟 ASIN 字符串列表。
    """
    url = f"https://www.amazon.com/dp/{asin}"
    driver.get(url)
    try:
        items = driver.explicit_waits(
            By.XPATH, "//div[@id='tp-inline-twister-dim-values-container']/ul/li", seconds=10)
    except TimeoutException:
        return []
    asins = [item.get_attribute(
        'data-asin') for item in items if item.get_attribute('data-asin')]
    return list(set(asins))


def get_product_info(asin: str) -> dict:
    """打开商品详情页，用 lxml 从 ``page_source`` 解析标题与主价文案。

    Args:
        asin: 商品 ASIN。

    Returns:
        含 ``asin``、``url``、``title``、``price`` 的字典。显式等待超时仍会解析
        当前 ``page_source``；节点缺失或 ``text`` 为空时对应字段为空字符串 ``""``。
    """
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

# ====================================================
# STEP 1: 获取所有搜索结果的 ASIN

# all_asins = []
# for asins in iter_search_asins_by_page("lashes"):
#     all_asins.extend(asins)

# all_asins = list(set(all_asins))

# with open("all_asins.json", "w") as f:
#     json.dump(all_asins, f)

# ====================================================
# STEP 2: 获取所有 ASIN 的兄弟 ASIN

# assert os.path.exists("all_asins.json"), "all_asins.json 不存在"

# try:
#     with open("all_sibling_asins.json", encoding="utf-8") as f:
#         all_sibling_asins = json.load(f)
# except FileNotFoundError:
#     all_sibling_asins = {}


# with open("all_asins.json", "r", encoding="utf-8") as f:
#     all_asins = json.load(f)

# for asin in all_asins:
#     if asin in all_sibling_asins:
#         print(f"exists: {asin} -> {len(all_sibling_asins[asin])}")
#         continue

#     sibling_asins = get_product_sibling_asins(asin)
#     all_sibling_asins[asin] = sibling_asins

#     with open("all_sibling_asins.json", "w", encoding="utf-8") as f:
#         json.dump(all_sibling_asins, f, ensure_ascii=False, indent=4)

#     print(f"new: {asin} -> {len(sibling_asins)}")

# ====================================================
# STEP 3: 获取所有 ASIN 的商品信息

assert os.path.exists("all_sibling_asins.json"), "all_sibling_asins.json 不存在"

ALL_PRODUCT_INFO_PATH = "all_product_info.json"


def _save_all_product_info(data: defaultdict) -> None:
    with open(ALL_PRODUCT_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


with open("all_sibling_asins.json", "r", encoding="utf-8") as f:
    all_sibling_asins = json.load(f)

try:
    with open(ALL_PRODUCT_INFO_PATH, "r", encoding="utf-8") as f:
        all_product_info = defaultdict(list, json.load(f))
except FileNotFoundError:
    all_product_info = defaultdict(list)

for asin, raw_sibling_asins in all_sibling_asins.items():
    # 「目标条数」needed：与内层实际写入条数一致（按唯一 ASIN 计）。
    # - JSON 中兄弟列表为空：只抓父 ASIN 一次，needed=1。
    # - 非空：先去重再计数，避免 needed 含重复而 done 因 have_asins 去重永远对不齐。
    if not raw_sibling_asins:
        needed = 1
        sibling_asins = [asin]
    else:
        # 去重后「先抓谁」不影响数据正确性；用 dict.fromkeys 保留原列表中首次出现
        # 的顺序，便于日志与 ``all_sibling_asins.json`` 对照排查。若不在意顺序可写
        # ``list(set(raw_sibling_asins))``。
        sibling_asins = list(dict.fromkeys(raw_sibling_asins))
        needed = len(sibling_asins)
    # 用 dict.get，不用 all_product_info[asin]：defaultdict 用 [] 下标会无键也插入
    # 空列表，污染内存与后续 json；get 在键不存在时返回 None，不写入新键。
    done_list = all_product_info.get(asin)
    # done：当前已为该父 ASIN 缓存了多少条；从未爬过该键则为 None，条数按 0 计。
    done = len(done_list) if done_list is not None else 0
    # 若已有条数等于目标，说明该父 ASIN 已完整，整段跳过。
    if done_list is not None and done == needed:
        print(f"exists: {asin} -> {done}")
        continue
    have_asins = {
        info["asin"] for info in all_product_info[asin] if info is not None
    }
    for sibling_asin in sibling_asins:
        if sibling_asin in have_asins:
            print(f"exists: {asin} -> {sibling_asin}")
            continue
        product_info = get_product_info(sibling_asin)
        all_product_info[asin].append(product_info)
        have_asins.add(sibling_asin)
        _save_all_product_info(all_product_info)
        print(f"{sibling_asin} -> {product_info}")

    _save_all_product_info(all_product_info)
    print(f"new: {asin} -> {len(all_product_info[asin])}")