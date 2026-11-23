# LLM Wiki to Educational Presentation: Agents & Graph Specification

本文件依據 Andrej Karpathy 的 **LLM Wiki（個人/主題外部化結構知識庫）** 概念，規範本專案之 Agent 角色、狀態機（Graph / Loop）、資料流以及品質檢查（Check / Eval Loop）機制。

---

## 1. 專案主題與目標

* **主題**：新手價值投資與三大財務報表解讀基礎（Value Investing & Financial Statements 101）
* **核心目標**：
  1. 以「先討論、後生成、結構化蒸餾」的方式，將 5 篇高品質投資權威文獻轉化為原子化的 LLM Wiki（含交叉索引與概念詞條）。
  2. 設計具備狀態機與自我修正（Self-Correction Check Loop）機制的 Agent Graph。
  3. 以 LLM Wiki 為唯一可信事實來源（Ground Truth），自動產出零基礎也能看懂的互動式教學 HTML 簡報。

---

## 2. Karpathy LLM Wiki 架構原則

Karpathy 提出的 LLM Wiki 核心精神是：**將非結構化原始輸入（Sources）透過 LLM 轉譯成原子化、具交叉連結、易於長期維護的 Markdown 知識圖譜（Wiki Concepts），並以 Master Index 作為導引目錄**。

```
StockWiki/
├── wiki/
│   ├── sources/                # 原始文獻庫（至少 5 篇權威資料）
│   │   ├── S01_value_investing_philosophy.md
│   │   ├── S02_three_financial_statements.md
│   │   ├── S03_key_metrics_and_valuation.md
│   │   ├── S04_economic_moats.md
│   │   └── S05_investor_pitfalls_and_risk.md
│   ├── concepts/               # 原子化概念詞條（蒸餾後知識卡片）
│   │   ├── 安全邊際_Margin_of_Safety.md
│   │   ├── 市場先生_Mr_Market.md
│   │   ├── 三大財務報表鉤稽關係.md
│   │   ├── 本益比與自由現金流.md
│   │   ├── 巴菲特經濟護城河.md
│   │   └── 價值陷阱與防禦策略.md
│   └── INDEX.md                # 知識庫總索引（包含概念關係與目錄樹）
```

---

## 3. Agent 角色定義與職責矩陣

| Agent 角色 | 核心職責 | 輸入 | 輸出 | 關鍵防呆機制 |
| :--- | :--- | :--- | :--- | :--- |
| **WikiIngestionAgent** | 閱讀原始文獻，提煉為原子化概念詞條，建立概念間雙向連結與索引目錄。 | 原始 Markdown 文獻 | `wiki/concepts/*.md`<br>`wiki/INDEX.md` | 禁止捏造概念，必須附帶來源標籤（Source Tag）。 |
| **PedagogyCuratorAgent** | 分析新手認知負擔，從 Wiki 提取核心先備知識，擬定教學大綱。 | `wiki/INDEX.md`<br>Wiki Concepts | 教學大綱結構（教學目標、各章節重點、比喻引導） | 確保大綱由淺入深（Hook $\to$ 核心概念 $\to$ 案例 $\to$ 實戰避坑）。 |
| **SlideGeneratorAgent** | 將大綱與 Wiki 內容轉換為每頁簡報的投影片內容（卡片式資訊）。 | 教學大綱 + Wiki 摘錄 | 投影片草稿（JSON/結構化格式） | 單頁字數嚴格限制，必須包含視覺化結構、關鍵要點與生活化比喻。 |
| **SlideReviewerAgent** | **[核心檢查節點]** 嚴格審查投影片內容，執行事實性、教學性與格式性評估。 | 投影片草稿 + Wiki Ground Truth | 審查評分表（通過 / 退回修正意見） | **嚴格事實核對**：若出現非 Wiki 之公式或概念直接退回重修。 |
| **HtmlPresentationAgent** | 將通過審查之結構化簡報資料，渲染為精美的互動式 HTML 投影片。 | 審查通過的簡報結構 | `index.html`（可點擊瀏覽之簡報） | 單一獨立檔案、CDN 支援、鍵盤快捷鍵操控、全螢幕簡報。 |

---

## 4. Graph / Loop 狀態機架構

### 4.1 流程圖（State Graph）

```mermaid
flowchart TD
    Start([開始 Start]) --> Ingest[1. Ingestion Node: 提煉 Wiki 概念與建立索引]
    Ingest --> Query[2. Query Wiki Node: 根據教學目標檢索相關詞條]
    Query --> Outline[3. Outline Node: 規劃教學架構與認知路徑]
    Outline --> Draft[4. Draft Node: 撰寫投影片內容草稿]
    Draft --> Review{5. Review & Eval Node: 綜合審查}

    Review -- "評分 < 85分 或 存在事實幻覺" --> FixLoop[回饋修正意見 Loop (Shift-Left)]
    FixLoop --> Draft
    
    Review -- "評分 >= 85分 且 全數通過" --> Render[6. Render HTML Node: 產生互動式簡報]
    Render --> Done([完成 Output: index.html])
```

### 4.2 狀態定義（State Machine Schema）

```python
class PresentationState(TypedDict):
    topic: str                        # 主題名稱
    sources: List[str]                # 原始文獻路徑列表
    wiki_index: Dict[str, Any]        # Wiki 概念索引結構
    teaching_outline: Dict[str, Any]  # 教學大綱 (章節、核心觀念、情境範例)
    slide_drafts: List[Dict[str, Any]]# 各頁投影片草稿
    review_feedback: List[str]        # 評審與檢查回饋意見
    review_score: float               # 評審綜合分數 (0-100)
    retry_count: int                  # 重試迴圈計數 (上限 3 次)
    final_html: str                   # 最終產出 HTML 內容
```

---

## 5. 重試與檢查機制（Check / Eval Loop 設計）

### 5.1 三大檢查維度（Evaluation Rubrics）
1. **事實嚴謹度（Factual Grounding & Faithfulness，權重 40%）**：
   - 所有名詞（例如 P/E、ROE、FCF、安全邊際）定義是否嚴格對齊 Wiki 內容？
   - 是否存在未在 Wiki 中提及的捏造公式或自創數據？
2. **新手友善度（Pedagogical Accessibility，權重 35%）**：
   - 是否有生硬術語未解釋？
   - 是否包含「生活化比喻」（例如把「損益表」比喻為個人薪資單、「資產負債表」比喻為個人財產與房貸清單）？
3. **簡報版面節奏（Slide Structure & Cognitive Load，權重 25%）**：
   - 每頁簡報是否聚焦在 1 個核心重點？
   - 投影片內文字是否過多（嚴格避免「把教科書貼在簡報上」）？

### 5.2 檢查前移（Shift-Left Verification）機制
* 在傳統流程中，若等到 HTML 簡報渲染完成才檢查，一旦發現概念錯誤，必須連同前端版面全部推倒重來。
* 本設計將檢查往前移至 **`Draft` 與 `Review` 之間（純結構層面）**：在生成 HTML 標籤前，先針對結構化資料進行 Fact-Check 與大綱連貫性驗證；只有當通過分數門檻（$\ge 85$ 分）時，才進入 HTML 渲染階段，大幅節省 Token 與重修成本。
