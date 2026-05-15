# amz-crawl-kit

轻量亚马逊前台数据采集：**按关键词翻页收集 ASIN → 为每个 ASIN 收集兄弟变体映射 → 批量抓取详情并落盘**。适合本地断点续跑与 JSON 下游处理。

![](https://img.cdn1.vip/i/6a03cb83f33a8_1778633603.webp)

## 环境要求

- Python 3.10+（需与本机已安装版本匹配）
- Google Chrome（主版本与 **ChromeDriver** 一致）
- 将 **`chromedriver.exe`** 放在 **`crazydriver/`** 目录下（与 `crazydriver/core.py` 中的 `CHROME_DEFAULT_PATH` 一致）
- 依赖见仓库根目录 **`requirements.txt`**（当前为 `selenium`、`lxml`）：

  ```bash
  pip install -r requirements.txt
  ```

  使用 Notebook 时建议同时安装 Jupyter 内核或直接在 VS Code / Cursor 中打开 `main.ipynb`。

  `crazydriver` 为本仓库内包，无需单独安装。

## 运行方式

**入口文件为根目录下的 `main.ipynb`。** 在 Jupyter 或 IDE 中自上而下执行；每个 **STEP** 依赖上一步生成的 JSON，未满足 `assert` 时不要执行后续步骤。

1. 在靠前单元格中设置 **`KEYWORD`**（搜索词）。数据会写入 **`Path.cwd() / KEYWORD.replace(" ", "_")`**，例如关键词 `lash extension` 对应目录 `lash_extension/`。
2. **STEP 1**：搜索与去重 → `search_asins.json`
3. **STEP 2**：读取 `search_asins.json`，逐 ASIN 打开详情页，从页面源码解析 `dimensionValuesDisplayData` → `sibling_asins.json`（支持断点续跑）
4. **STEP 3**：读取 `sibling_asins.json`，对每个父 ASIN 下各子 ASIN 抓取详情并写入 `product_info.json`（含变体规格 **`tags`**，支持断点续跑）

各 STEP 内会创建 `CrazyDriver()`；若中断后重跑，注意是否需重启内核或复用同一 `driver`（以你本地实际执行为准）。

若仓库中仍保留 `main.py`，仅作旧版参考；**现行采集流程以 `main.ipynb` 为准。**

---

## STEP 1：搜索关键词 → ASIN 列表

**产出：**`<SAVE_DIR>/search_asins.json`

**作用：** 使用 `iter_search_asins_by_page(KEYWORD)` 访问 `https://www.amazon.com/s?k=...&page=...`，从列表项读取 `data-asin`，去重后写入 **JSON 数组**。

**形状示例：**

```json
["B0XXXXXXXX", "B0YYYYYYYY"]
```

---

## STEP 2：搜索结果 ASIN → 兄弟变体映射

**产出：**`<SAVE_DIR>/sibling_asins.json`

**作用：** 对每个搜索得到的 ASIN 打开详情页，用正则从 `page_source` 中提取 `dimensionValuesDisplayData` 并 `json.loads`。结果为 **父 ASIN → 子 ASIN → 变体展示文案列表**；无变体或未匹配到字段时为 `{}`（空对象）。每处理完一个父 ASIN 即写回文件，便于断点续跑。

**形状示例：**

```json
{
  "B0AAAAAAAA": {
    "B0AAAAAAAA": ["320pcs Kit-3040D-D-9-16mm"],
    "B0BBBBBBBB": ["280Pcs-80D-12mm"]
  },
  "B0CCCCCCCC": {}
}
```

---

## STEP 3：兄弟映射 → 各变体详情快照

**产出：**`<SAVE_DIR>/product_info.json`

**作用：** 读取 `sibling_asins.json`。对每个父 ASIN：若兄弟映射为空则只抓父 ASIN 一条详情；否则对每个子 ASIN 打开详情页，用 **lxml** 解析标题、价格、Best Sellers Rank 等；将 **`tags`**（来自 Step 2 中该子 ASIN 对应的列表，无则 `[]`）并入每条记录。已抓过的 `(父 ASIN, 子 ASIN)` 会跳过；每新增一条即保存整个 `product_info`，便于断点续跑。

**形状示例：**

```json
{
  "B0AAAAAAAA": [
    {
      "asin": "B0AAAAAAAA",
      "url": "https://www.amazon.com/dp/B0AAAAAAAA",
      "title": "...",
      "price": "...",
      "best_sellers_rank": "...",
      "tags": ["320pcs Kit-3040D-D-9-16mm"]
    }
  ]
}
```

---

## 产出文件一览

| 步骤 | 相对路径（在 `SAVE_DIR` 下） | 内容概要 |
|------|------------------------------|----------|
| STEP 1 | `search_asins.json` | 关键词搜索下出现的 ASIN 字符串数组（去重） |
| STEP 2 | `sibling_asins.json` | 父 ASIN → 子 ASIN → 变体展示文案列表 |
| STEP 3 | `product_info.json` | 父 ASIN → 该父下各子体/自身的详情字典列表（含 `tags`） |

## 注意事项

- 亚马逊页面结构、反爬策略会变更，XPath 与内嵌 JSON 字段可能需随页面改版调整。
- 请遵守亚马逊服务条款、robots 及当地法律，仅用于你有权访问的数据与合规场景。
- `crazydriver` 会在 `crazydriver/chrome_data` 使用独立 Chrome 用户数据，首次运行需能正常启动浏览器。
