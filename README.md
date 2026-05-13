# amz-crawl-kit

轻量亚马逊前台数据采集脚本：按关键词翻页收集 ASIN → 为每个 ASIN 收集兄弟变体 ASIN → 批量抓取详情字段并落盘。适合本地断点续跑与 JSON 下游处理。

![](https://img.cdn1.vip/i/6a03cb83f33a8_1778633603.webp)

## 环境要求

- Python 3.10+（推荐；需匹配你本机已安装的版本）
- Google Chrome（或与 `chromedriver` 主版本一致的浏览器）
- 将 **`chromedriver.exe`** 放在项目根目录（与 `main.py` 同级），与 `crazydriver/core.py` 中的默认路径一致
- Python 依赖：仓库根目录已提供 **`requirements.txt`**（当前固定 `selenium`、`lxml` 版本），安装命令：

  ```bash
  pip install -r requirements.txt
  ```

  `crazydriver` 为本仓库内包，无需单独安装。

## 运行方式说明

当前 `main.py` 把三个步骤写在同一文件里：**同一时刻只应启用一个 Step 的可执行代码**，其余步骤保持注释；否则可能因缺少上游 JSON 在 `assert` 处退出，或重复写浏览器会话。

运行示例：

```bash
python main.py
```

---

## Step 1：搜索关键词 → 全量 ASIN 列表

**产出文件：** `all_asins.json`

**作用：** 使用 `iter_search_asins_by_page(keyword)` 按页访问 `https://www.amazon.com/s?k=...&page=...`，从搜索结果列表项读取 `data-asin`，去重后写入 **JSON 数组**。

**在 `main.py` 中：**

1. 取消 **「STEP 1」** 区块（约 132–139 行）的注释。
2. 将 `"lashes"` 改成你的搜索词。
3. **注释掉「STEP 3」整段**（从 `assert os.path.exists("all_sibling_asins.json")` 到文件末尾的循环与保存逻辑），否则尚未生成 `all_sibling_asins.json` 时会断言失败。

**`all_asins.json` 形状示例：**

```json
["B0XXXXXXXX", "B0YYYYYYYY"]
```

---

## Step 2：ASIN 列表 → 每个父 ASIN 的兄弟变体 ASIN

**产出文件：** `all_sibling_asins.json`

**作用：** 读取 `all_asins.json`，对每个 ASIN 打开详情页，在变体区域（`tp-inline-twister-dim-values-container`）收集兄弟 ASIN；结果以 **父 ASIN → 兄弟 ASIN 列表** 写入 JSON（无变体时列表可为空 `[]`）。每处理一个父 ASIN 会覆盖写回文件，便于断点续跑。

**在 `main.py` 中：**

1. 确认根目录已有 **`all_asins.json`**（先完成 Step 1）。
2. 将 **「STEP 1」** 重新注释掉。
3. 取消 **「STEP 2」** 区块（约 144–167 行）的注释。
4. **继续注释「STEP 3」整段**，避免与 Step 2 同时跑。

**`all_sibling_asins.json` 形状示例：**

```json
{
  "B0AAAAAAAA": ["B0AAAAAAAA", "B0BBBBBBBB"],
  "B0CCCCCCCC": []
}
```

---

## Step 3：兄弟映射 → 每个变体的详情快照

**产出文件：** `all_product_info.json`

**作用：** 读取 `all_sibling_asins.json`。对每个父 ASIN：若兄弟列表为空则只抓父 ASIN 一条详情；否则对去重后的每个兄弟 ASIN 打开详情页，用 **lxml** 解析 `page_source` 中的标题、价格、Best Sellers Rank 等，写入以父 ASIN 为键、**详情 dict 列表** 为值的结构；支持断点续跑（已够条数的父 ASIN 会跳过）。

**在 `main.py` 中：**

1. 确认已有 **`all_sibling_asins.json`**（先完成 Step 2）。
2. 将 **「STEP 1」「STEP 2」** 保持为注释。
3. 保持 **「STEP 3」**（约 169 行起）为**未注释**状态（与仓库默认一致）。

**`all_product_info.json` 形状示例：**

```json
{
  "B0AAAAAAAA": [
    {
      "asin": "B0AAAAAAAA",
      "url": "https://www.amazon.com/dp/B0AAAAAAAA",
      "title": "...",
      "price": "...",
      "best_sellers_rank": "..."
    }
  ]
}
```

---

## 三份产出文件一览

| 步骤 | 文件名 | 内容概要 |
|------|--------|----------|
| Step 1 | `all_asins.json` | 关键词搜索下出现的 ASIN 字符串数组（去重） |
| Step 2 | `all_sibling_asins.json` | 父 ASIN → 其详情页上兄弟变体 ASIN 列表 |
| Step 3 | `all_product_info.json` | 父 ASIN → 该父下各变体/自身的详情字段列表 |

## 注意事项

- 亚马逊页面结构、反爬策略会变更，XPath 可能需随页面改版调整。
- 请遵守亚马逊服务条款、robots 及当地法律，仅用于你有权访问的数据与合规场景。
- `crazydriver` 会在本地目录使用独立 Chrome 用户数据（见 `crazydriver/core.py`），首次运行需能正常启动浏览器。
