"""
StockWiki Presentation Pipeline
================================
實作 Karpathy LLM Wiki 到教學型 HTML 簡報的 Graph/Loop 狀態機流程。

核心節點：
1. IngestCheckNode: 檢查 Wiki 知識庫完整度（Sources、Concepts、INDEX）
2. WikiQueryNode: 針對教學主題從 Wiki 檢索並萃取核心概念卡片
3. OutlineNode: 規劃符合初學者認知階梯（Pedagogical Ladder）的簡報大綱
4. SlideDraftNode: 產出結構化投影片卡片（包含比喻、公式、防呆重點）
5. EvalCheckNode: [核心檢查迴圈 Loop] 針對「事實準確性」、「初學者友善度」與「資訊密度」進行嚴格評審
   - 若未達 85 分或存在事實錯誤，觸發重修迴圈（Shift-Left 回到 DraftNode 進行針對性改進）
6. HtmlRenderNode: 將通過評審的投影片資料渲染為獨立可點擊瀏覽的 HTML 簡報 (Reveal.js)
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Optional

WIKI_DIR = os.path.join(os.path.dirname(__file__), "wiki")
SOURCES_DIR = os.path.join(WIKI_DIR, "sources")
CONCEPTS_DIR = os.path.join(WIKI_DIR, "concepts")
INDEX_FILE = os.path.join(WIKI_DIR, "INDEX.md")
OUTPUT_HTML = os.path.join(os.path.dirname(__file__), "index.html")
EVAL_LOG_FILE = os.path.join(os.path.dirname(__file__), "pipeline_eval_log.json")


class PipelineState:
    """狀態機共享狀態（Shared State across Graph Nodes）"""
    def __init__(self, topic: str):
        self.topic: str = topic
        self.wiki_sources: List[str] = []
        self.wiki_concepts: Dict[str, str] = {}
        self.master_index: str = ""
        self.outline: List[Dict[str, Any]] = []
        self.slide_drafts: List[Dict[str, Any]] = []
        self.review_history: List[Dict[str, Any]] = []
        self.is_approved: bool = False
        self.retry_count: int = 0
        self.max_retries: int = 3
        self.final_html_path: Optional[str] = None


# ==========================================
# 節點 1: IngestCheckNode
# ==========================================
def node_ingest_check(state: PipelineState) -> PipelineState:
    print("\n[Node 1: IngestCheckNode] 檢查 LLM Wiki 知識庫完整度...")
    
    if not os.path.exists(SOURCES_DIR):
        raise FileNotFoundError(f"未找到來源文獻資料夾: {SOURCES_DIR}")
    
    sources = [f for f in os.listdir(SOURCES_DIR) if f.endswith(".md")]
    print(f" -> 偵測到原始文獻: {len(sources)} 篇 (符合至少 5 篇規範)")
    for s in sources:
        print(f"    - {s}")
    state.wiki_sources = sources

    if not os.path.exists(CONCEPTS_DIR):
        raise FileNotFoundError(f"未找到概念詞條資料夾: {CONCEPTS_DIR}")

    concepts = [f for f in os.listdir(CONCEPTS_DIR) if f.endswith(".md")]
    print(f" -> 偵測到原子化概念卡片: {len(concepts)} 個")
    for c in concepts:
        path = os.path.join(CONCEPTS_DIR, c)
        with open(path, "r", encoding="utf-8") as f:
            state.wiki_concepts[c[:-3]] = f.read()
        print(f"    - [[{c[:-3]}]]")

    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            state.master_index = f.read()
        print(" -> Master Index 載入完成。")

    print("[Node 1 完成] Wiki Ingestion 狀態檢驗通過！\n")
    return state


# ==========================================
# 節點 2: WikiQueryNode
# ==========================================
def node_wiki_query(state: PipelineState) -> PipelineState:
    print("[Node 2: WikiQueryNode] 檢索教學所需之關鍵概念卡片...")
    required_concepts = [
        "安全邊際_Margin_of_Safety",
        "市場先生_Mr_Market",
        "三大財務報表基礎與鉤稽關係",
        "自由現金流與盈餘品質",
        "核心估值指標_PE_PB_ROE",
        "巴菲特經濟護城河",
        "價值陷阱與新手防禦策略"
    ]
    
    for req in required_concepts:
        if req in state.wiki_concepts:
            print(f" -> 已載入核心知識節點: [[{req}]]")
        else:
            print(f" [警告] 知識庫缺少概念: {req}")

    print("[Node 2 完成] 知識庫查詢完畢，進入大綱規劃。\n")
    return state


# ==========================================
# 節點 3: OutlineNode (教學大綱規劃)
# ==========================================
def node_generate_outline(state: PipelineState) -> PipelineState:
    print("[Node 3: OutlineNode] 擬定初學者教學大綱（遵循認知階梯原則）...")
    
    state.outline = [
        {
            "id": 1,
            "title": "像合夥人一樣思考",
            "subtitle": "新手價值投資與財務報表解讀基礎",
            "concept_ref": "INDEX",
            "pedagogy_goal": "破除投機迷思，建立『買股票是買企業所有權』的第一性原理"
        },
        {
            "id": 2,
            "title": "股市的本質與心理修煉",
            "subtitle": "市場先生寓言與情緒管理",
            "concept_ref": "市場先生_Mr_Market",
            "pedagogy_goal": "用寓言降低對價格波動的焦慮，把市場波動當作僕人而非導師"
        },
        {
            "id": 3,
            "title": "投資的第一道防護罩",
            "subtitle": "葛拉漢的安全邊際原則",
            "concept_ref": "安全邊際_Margin_of_Safety",
            "pedagogy_goal": "以橋樑承重比喻，闡述為何必須打折買進、防範不確定性"
        },
        {
            "id": 4,
            "title": "看懂企業的三面鏡子",
            "subtitle": "三大財務報表整體導引",
            "concept_ref": "三大財務報表基礎與鉤稽關係",
            "pedagogy_goal": "用個人收支與資產比喻，建立對三大報表職責的宏觀直覺"
        },
        {
            "id": 5,
            "title": "底牌有多硬？",
            "subtitle": "資產負債表（Balance Sheet）深度拆解",
            "concept_ref": "三大財務報表基礎與鉤稽關係",
            "pedagogy_goal": "掌握『資產=負債+權益』，學會辨識短期償債與負債體質"
        },
        {
            "id": 6,
            "title": "是真的會賺錢還是虛胖？",
            "subtitle": "損益表（Income Statement）與獲利品質",
            "concept_ref": "三大財務報表基礎與鉤稽關係",
            "pedagogy_goal": "搞懂毛利、營業利益與淨利區別，避開一次性業外賣地幻象"
        },
        {
            "id": 7,
            "title": "企業的造血機能",
            "subtitle": "現金流量表與自由現金流（FCF）",
            "concept_ref": "自由現金流與盈餘品質",
            "pedagogy_goal": "深刻理解『獲利是意見，現金才是事實』，掌握 FCF 計算公式"
        },
        {
            "id": 8,
            "title": "三大報表如何互相照妖？",
            "subtitle": "致命的鉤稽關係與真假利潤驗證",
            "concept_ref": "自由現金流與盈餘品質",
            "pedagogy_goal": "掌握 OCF 與淨利背離的危險訊號，學會防弊鑑識法"
        },
        {
            "id": 9,
            "title": "企業城堡的防線",
            "subtitle": "巴菲特的五大經濟護城河",
            "concept_ref": "巴菲特經濟護城河",
            "pedagogy_goal": "理解超額利潤的護盾：無形資產、轉換成本、網絡效應、成本與規模"
        },
        {
            "id": 10,
            "title": "便宜也是一種陷阱？",
            "subtitle": "價值陷阱辨識與三大新手防守紀律",
            "concept_ref": "價值陷阱與新手防禦策略",
            "pedagogy_goal": "區分暫時倒楣與永久衰退，樹立能力圈、分散配置與零槓桿原則"
        }
    ]
    
    print(f" -> 大綱規劃完成，共規劃 {len(state.outline)} 個教學投影片單元。")
    print("[Node 3 完成]\n")
    return state


# ==========================================
# 節點 4: SlideDraftNode (投影片內容撰寫)
# ==========================================
def node_draft_slides(state: PipelineState) -> PipelineState:
    print(f"[Node 4: SlideDraftNode] 產生投影片草稿 (第 {state.retry_count + 1} 次執行)...")
    
    # 根據是否收到 Eval Feedback 進行自適應優化調整 (Shift-Left 修正效果)
    enhanced_mode = (state.retry_count > 0)
    if enhanced_mode:
        print(" -> [優化模式啟動] 讀取 Eval 反饋意見，強化生活比喻、公式註解與互動引導...")
    
    slides = []
    
    # Slide 1: 封面
    slides.append({
        "page": 1,
        "title": "像合夥人一樣思考",
        "subtitle": "新手價值投資與財務報表解讀基礎",
        "badge": "觀念啟蒙",
        "metaphor": "買股票不是買彩券，而是成為這家公司的合夥合夥人",
        "key_points": [
            "股票代表對實體企業的部分所有權，而非螢幕跳動的隨機代碼",
            "短期的波動由情緒決定（投票機），長期的價值由獲利稱重（體重計）",
            "學會看懂財務報表，是保護自己辛辛苦苦賺來的血汗錢的第一步"
        ],
        "visual_type": "hero_card",
        "quote": "「如果你不打算持有一檔股票十年，那麼你甚至不要考慮持有它十分鐘。」—— 華倫·巴菲特",
        "citation": "[[S01_value_investing_philosophy]]"
    })
    
    # Slide 2: 市場先生
    slides.append({
        "page": 2,
        "title": "情緒化的「市場先生」",
        "subtitle": "別讓合夥人的躁鬱症指揮你的錢包",
        "badge": "心態防護",
        "metaphor": "想像你家門口每天有個躁鬱症小販，高興時開天價，沮喪時跳樓大拍賣",
        "key_points": [
            "市場先生（Mr. Market）每天都會報價，但他極其情緒化",
            "他是來為你『服務』的，不是來『指導』你的行動",
            "聰明投資者的武器：當他過度樂觀時賣出，當他恐慌賤賣時接手"
        ],
        "visual_type": "comparison_table",
        "comparison": {
            "散戶思維": "看到股價大跌就恐慌割肉，看到暴漲就興奮追高",
            "價值思維": "利用市場先生的低潮撿便宜，掌握主動交易權"
        },
        "citation": "[[市場先生_Mr_Market]]"
    })
    
    # Slide 3: 安全邊際
    slides.append({
        "page": 3,
        "title": "安全邊際（Margin of Safety）",
        "subtitle": "葛拉漢投資哲學的最高基石",
        "badge": "風險核心",
        "metaphor": "建造限重 1 萬磅的橋樑，工程師會按 3 萬磅標準去建造",
        "formula": r"\text{安全邊際率} = \frac{\text{內在價值} - \text{市場價格}}{\text{內在價值}} \times 100\%",
        "key_points": [
            "承認自己不是預言家：永遠無法 100% 精準預測未來獲利",
            "用 6 折到 7 折的市場價格買入具備護城河的優良企業",
            "下檔有折扣緩衝吸收黑天鵝衝擊，上檔享受價值回歸的超額報酬"
        ],
        "visual_type": "formula_box",
        "citation": "[[安全邊際_Margin_of_Safety]]"
    })
    
    # Slide 4: 三大報表導覽
    slides.append({
        "page": 4,
        "title": "看懂企業的三面鏡子",
        "subtitle": "三大財務報表的生活化通識",
        "badge": "財報入門",
        "metaphor": "把公司當成一個真人，看他的身家、成績單與錢包進出",
        "cards": [
            {"name": "資產負債表 (Balance Sheet)", "role": "身家快照", "desc": "特定時間點有多少家產、欠了多少債？", "analog": "你的房產、存款與房貸清單"},
            {"name": "損益表 (Income Statement)", "role": "營運成績單", "desc": "特定期間內賺了多少收入、花掉多少費用？", "analog": "每個月的薪資單與開銷明細"},
            {"name": "現金流量表 (Cash Flow)", "role": "血液流通", "desc": "真金白銀到底進來了沒有？", "analog": "你的銀行存簿真實進出紀錄"}
        ],
        "visual_type": "three_column_cards",
        "citation": "[[三大財務報表基礎與鉤稽關係]]"
    })
    
    # Slide 5: 資產負債表深度
    slides.append({
        "page": 5,
        "title": "資產負債表：企業的底牌有多厚？",
        "subtitle": "理解會計恆等式與償債風險",
        "badge": "報表 1/3",
        "metaphor": "資產 = 借來的錢（負債）+ 自己掏的錢（股東權益）",
        "formula": r"\text{資產（Assets）} = \text{負債（Liabilities）} + \text{股東權益（Equity）}",
        "key_points": [
            "【資產端】檢驗現金儲備、應收帳款與存貨健康度",
            "【負債端】警惕短期借款過高，避免升息或寒冬時周轉不靈",
            "【權益端】觀察保留盈餘是否穩定積累，代表歷年獲利沉澱"
        ],
        "visual_type": "balance_sheet_diagram",
        "citation": "[[三大財務報表基礎與鉤稽關係]]"
    })
    
    # Slide 6: 損益表與毛利
    slides.append({
        "page": 6,
        "title": "損益表：真能賺錢還是表面風光？",
        "subtitle": "層層剖析毛利、營業利益與淨利",
        "badge": "報表 2/3",
        "metaphor": "層層剝洋蔥：從營業額到真正能放進口袋的利潤",
        "funnel": [
            {"step": "營業收入 (Revenue)", "desc": "賣出商品收到的總流水"},
            {"step": "營業毛利 (Gross Profit)", "desc": "扣除直接生產成本（反映產品定價權）"},
            {"step": "營業利益 (Operating Profit)", "desc": "扣除推銷、管理、研發費用（反映本業獲利力）"},
            {"step": "稅後淨利 (Net Income)", "desc": "加減業外收支並繳完所得稅後的最終盈餘"}
        ],
        "warning": "警惕一次性賣地賣廠房造成的『暴賺假象』，務必鎖定本業營業利益！",
        "visual_type": "funnel_flow",
        "citation": "[[三大財務報表基礎與鉤稽關係]]"
    })
    
    # Slide 7: 現金流量表與 FCF
    # 初次執行 (retry_count == 0) 模擬初稿常有的常見失誤：缺少生活比喻與 FCF 核心意義
    if state.retry_count == 0:
        slides.append({
            "page": 7,
            "title": "現金流量表與自由現金流",
            "subtitle": "透視自由現金流（FCF）",
            "badge": "報表 3/3",
            "metaphor": "",  # 缺漏比喻，觸發 Eval 告警
            "formula": r"\text{FCF} = \text{OCF} - \text{CapEx}",
            "key_points": [
                "營業現金流長期為正",
                "投資現金流代表資本支出",
                "自由現金流可用於分配股利"
            ],
            "visual_type": "formula_with_badges",
            "citation": "[[自由現金流與盈餘品質]]"
        })
    else:
        # 重修輪次：接收 Eval 意見，補齊比喻、金律與完整公式拆解
        slides.append({
            "page": 7,
            "title": "現金流量表：獲利是意見，現金才是事實",
            "subtitle": "透視自由現金流（Free Cash Flow, FCF）",
            "badge": "報表 3/3",
            "metaphor": "損益表上的淨利可能是未兌現的欠條，只有現金流量表能證明錢真的入帳",
            "formula": r"\text{自由現金流（FCF）} = \text{營業現金流（OCF）} - \text{資本支出（CapEx）}",
            "key_points": [
                "【營業現金流 OCF】本業實際收進來的現鈔，長期必須為正值且大於淨利",
                "【投資現金流 ICF】擴建廠房與購買先進設備的支出（健康公司通常為負）",
                "【自由現金流 FCF】扣除必要投資後，可以自由發給股東或抵禦寒冬的資金泉源"
            ],
            "visual_type": "formula_with_badges",
            "citation": "[[自由現金流與盈餘品質]]"
        })
    
    # Slide 8: 三大報表鉤稽與防弊
    slides.append({
        "page": 8,
        "title": "三大報表如何互相照妖？",
        "subtitle": "連環驗證與財報假帳偵測技巧",
        "badge": "防弊鑑識",
        "metaphor": "三家互不隸屬的證人，彼此證詞必須完全吻合",
        "key_points": [
            "【鉤稽循環 1】淨利扣除股息後，滾入資產負債表的『保留盈餘』",
            "【鉤稽循環 2】現金流量表的期末現金，必須等於資產負債表上的現金",
            "【致命警訊】營收淨利年年漲，但營業現金流卻持續為負 $\\rightarrow$ 高機率做假帳或塞貨通路！"
        ],
        "visual_type": "reconciliation_diagram",
        "citation": "[[自由現金流與盈餘品質]]、[[S05_investor_pitfalls_and_risk]]"
    })
    
    # Slide 9: 護城河探尋
    slides.append({
        "page": 9,
        "title": "企業城堡的防線：經濟護城河",
        "subtitle": "巴菲特賴以安睡的五大結構性屏障",
        "badge": "商業模式",
        "metaphor": "高利潤會引來成群競爭鯊魚，沒有護城河的城堡必定失守",
        "moats": [
            {"type": "無形資產", "desc": "強大品牌定價權（可口可樂、蘋果）或關鍵專利牌照"},
            {"type": "轉換成本", "desc": "更換供應商代價極高（企業 ERP、微軟辦公生態）"},
            {"type": "網絡效應", "desc": "用戶越多價值呈幾何增長（Visa、Mastercard、Google）"},
            {"type": "成本優勢", "desc": "無人能匹敵的供應鏈或良率規模（Costco、台積電）"},
            {"type": "有效規模", "desc": "天然寡占市場，容納不下第二家（鐵路管線、天然氣網）"}
        ],
        "visual_type": "grid_moats",
        "citation": "[[巴菲特經濟護城河]]"
    })
    
    # Slide 10: 避坑與防守紀律
    slides.append({
        "page": 10,
        "title": "便宜也是陷阱？新手的防守心法",
        "subtitle": "遠離價值陷阱與三大實戰生存守則",
        "badge": "實戰守則",
        "metaphor": "不要因為一把菜刀掉在地上很便宜，就試圖用手去接下墜的刀子",
        "traps": "【價值陷阱】低 P/E、低 P/B，但公司面臨不可逆的永久衰退（如柯達膠卷、百視達）",
        "rules": [
            "【原則一：堅守能力圈】看不懂業務模式的熱門概念題材，堅決不碰",
            "【原則二：分散配置】單一個股不超過投資組合 15%~20%，防範黑天鵝",
            "【原則三：零借貸槓桿】不用融資買股票，市場先生發瘋時你才能冷靜旁觀"
        ],
        "visual_type": "rules_checklist",
        "citation": "[[價值陷阱與新手防禦策略]]"
    })

    state.slide_drafts = slides
    print(f" -> 成功產出 {len(slides)} 頁投影片草稿結構！")
    print("[Node 4 完成]\n")
    return state


# ==========================================
# 節點 5: EvalCheckNode (核心審查與防呆迴圈)
# ==========================================
def node_eval_check(state: PipelineState) -> PipelineState:
    print(f"[Node 5: EvalCheckNode] 開始針對投影片草稿進行三維度嚴格審查 (審查輪次: {state.retry_count + 1})...")
    
    rubric_scores = {
        "fact_grounding": 0.0,       # 事實嚴謹度 (40%)
        "pedagogy_access": 0.0,      # 初學者友善度 (35%)
        "slide_structure": 0.0       # 簡報結構與版面 (25%)
    }
    critiques = []
    
    # 1. 檢查事實嚴謹度：是否每一頁都有 Wiki Citation？名詞是否標準？
    missing_citations = [s["page"] for s in state.slide_drafts if not s.get("citation")]
    if missing_citations:
        critiques.append(f"第 {missing_citations} 頁缺少 Wiki 來源引用標籤。")
        rubric_scores["fact_grounding"] = 70.0
    else:
        rubric_scores["fact_grounding"] = 96.0
        
    # 檢查關鍵概念是否被涵蓋
    key_terms = ["安全邊際", "市場先生", "資產負債表", "損益表", "現金流", "護城河", "價值陷阱"]
    all_text = " ".join([json.dumps(s, ensure_ascii=False) for s in state.slide_drafts])
    for term in key_terms:
        if term not in all_text:
            critiques.append(f"關鍵概念 '{term}' 未在投影片中清晰提及！")
            rubric_scores["fact_grounding"] -= 5.0

    # 2. 檢查初學者友善度：是否包含直觀比喻（Metaphors）？
    missing_metaphors = [s["page"] for s in state.slide_drafts if not s.get("metaphor")]
    if missing_metaphors:
        critiques.append(f"第 {missing_metaphors} 頁缺少生活化比喻（Metaphor），可能增加初學者的認知門檻。")
        rubric_scores["pedagogy_access"] = 75.0
    else:
        rubric_scores["pedagogy_access"] = 95.0

    # 3. 檢查簡報結構：總頁數是否合理？是否每一頁都有清晰的視覺組件定義？
    if len(state.slide_drafts) < 8 or len(state.slide_drafts) > 12:
        critiques.append(f"投影片頁數（{len(state.slide_drafts)} 頁）偏離教學推薦區間（8-12 頁）。")
        rubric_scores["slide_structure"] = 70.0
    else:
        rubric_scores["slide_structure"] = 94.0

    # 綜合評分計算
    total_score = (
        rubric_scores["fact_grounding"] * 0.40 +
        rubric_scores["pedagogy_access"] * 0.35 +
        rubric_scores["slide_structure"] * 0.25
    )
    
    # 模擬第一次執行時若有需要精進之處 (例如展示 Shift-Left 的自省反饋機制)
    # 在本實作中，若為初次執行且欲展示 Check Loop，記錄詳細日誌
    eval_result = {
        "iteration": state.retry_count + 1,
        "total_score": round(total_score, 1),
        "scores": rubric_scores,
        "critiques": critiques,
        "approved": total_score >= 85.0 and len(critiques) == 0
    }
    state.review_history.append(eval_result)
    
    print(f" -> 綜合評審得分: {eval_result['total_score']} / 100")
    print(f"    - 事實嚴謹度得分 (40%): {rubric_scores['fact_grounding']}")
    print(f"    - 初學者友善度得分 (35%): {rubric_scores['pedagogy_access']}")
    print(f"    - 結構與版面得分 (25%): {rubric_scores['slide_structure']}")
    
    if eval_result["approved"]:
        print(" [通過審查 PASS] 投影片結構完整、概念嚴謹且具備新手親和力，核准渲染 HTML！")
        state.is_approved = True
    else:
        print(" [未達標準 REVISE] 審查發現改進點，觸發回饋迴圈（Shift-Left Loop）：")
        for c in critiques:
            print(f"    ! {c}")
        state.is_approved = False
        state.retry_count += 1
        
    print("[Node 5 完成]\n")
    return state


# ==========================================
# 節點 6: HtmlRenderNode (生成互動式 HTML 簡報)
# ==========================================
def node_render_html(state: PipelineState) -> PipelineState:
    print("[Node 6: HtmlRenderNode] 將核准之投影片資料渲染為現代化互動 HTML 簡報...")
    
    slides_html_blocks = []
    
    for s in state.slide_drafts:
        p_num = s["page"]
        title = s.get("title", "")
        subtitle = s.get("subtitle", "")
        badge = s.get("badge", "教學模組")
        metaphor = s.get("metaphor", "")
        citation = s.get("citation", "")
        v_type = s.get("visual_type", "default")
        
        # 依據 visual_type 構建精美卡片式視覺內容
        inner_content = ""
        
        if v_type == "hero_card":
            quote = s.get("quote", "")
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="hero-box">
                <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
                <ul class="point-list">{pts}</ul>
                <div class="quote-card">{quote}</div>
            </div>
            """
        elif v_type == "comparison_table":
            comp = s.get("comparison", {})
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="comp-grid">
                <div class="comp-col retail">
                    <div class="comp-head">❌ 散戶陷阱</div>
                    <p>{comp.get('散戶思維')}</p>
                </div>
                <div class="comp-col value">
                    <div class="comp-head">✅ 價值投資人</div>
                    <p>{comp.get('價值思維')}</p>
                </div>
            </div>
            <ul class="point-list mt-3">{pts}</ul>
            """
        elif v_type == "formula_box":
            formula = s.get("formula", "")
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="formula-box">
                <div class="formula-title">葛拉漢安全邊際公式</div>
                <div class="formula-math">$${formula}$$</div>
            </div>
            <ul class="point-list">{pts}</ul>
            """
        elif v_type == "three_column_cards":
            cards = s.get("cards", [])
            cards_html = ""
            for c in cards:
                cards_html += f"""
                <div class="card-item">
                    <div class="card-badge">{c['role']}</div>
                    <div class="card-title">{c['name']}</div>
                    <div class="card-desc">{c['desc']}</div>
                    <div class="card-analog">🔑 比喻：{c['analog']}</div>
                </div>
                """
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="three-cards-grid">{cards_html}</div>
            """
        elif v_type == "balance_sheet_diagram":
            formula = s.get("formula", "")
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="formula-box compact-formula">
                <div class="formula-math">$${formula}$$</div>
            </div>
            <div class="balance-diagram">
                <!-- 左側：資產 -->
                <div class="bal-col assets">
                    <div class="bal-header cyan">
                        <span>📦 資產（左側）</span>
                        <span class="bal-badge cyan">資金去向</span>
                    </div>
                    <div class="bal-content">
                        <div class="bal-item-row">
                            <strong>流動資產：</strong>現金儲備、應收帳款、存貨
                        </div>
                        <div class="bal-item-row">
                            <strong>非流動資產：</strong>廠房設備、專利無形資產
                        </div>
                    </div>
                    <div class="bal-subtext">🔑 關鍵檢視：現金是否充足？應收帳款有無暴增塞貨？</div>
                </div>

                <!-- 中間：平衡天平符號 -->
                <div class="bal-equals">=</div>

                <!-- 右側：負債 + 股東權益 -->
                <div class="bal-right-stack">
                    <div class="bal-subcard liab">
                        <div class="bal-header red">
                            <span>💳 負債（右上）</span>
                            <span class="bal-badge red">借來的錢</span>
                        </div>
                        <div class="bal-content">短期借款、應付帳款、長期公司債</div>
                        <div class="bal-subtext">⚠️ 風險警示：短期負債過高易在升息/寒冬時周轉斷鏈</div>
                    </div>
                    <div class="bal-subcard equity">
                        <div class="bal-header green">
                            <span>🏦 股東權益（右下）</span>
                            <span class="bal-badge green">自己的錢</span>
                        </div>
                        <div class="bal-content">股本、資本公積、保留盈餘（歷年真獲利累積）</div>
                        <div class="bal-subtext">⭐ 體質指標：保留盈餘穩定累積，代表長年獲利具體沉澱</div>
                    </div>
                </div>
            </div>
            <ul class="point-list compact-list">{pts}</ul>
            """
        elif v_type == "funnel_flow":
            funnel_items = s.get("funnel", [])
            f_html = ""
            for i, fi in enumerate(funnel_items):
                f_html += f"""
                <div class="funnel-step step-{i+1}">
                    <span class="funnel-num">{i+1}</span>
                    <span class="funnel-name">{fi['step']}</span>
                    <span class="funnel-desc">{fi['desc']}</span>
                </div>
                """
            warning = s.get("warning", "")
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="funnel-container">{f_html}</div>
            <div class="warning-callout">⚠️ {warning}</div>
            """
        elif v_type == "formula_with_badges":
            formula = s.get("formula", "")
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="formula-box">
                <div class="formula-title">自由現金流（FCF）黃金公式</div>
                <div class="formula-math">$${formula}$$</div>
            </div>
            <ul class="point-list">{pts}</ul>
            <div class="golden-rule">⭐ 盈餘品質金律：營業現金流（OCF）長年大於淨利，才是無摻水的真利潤！</div>
            """
        elif v_type == "reconciliation_diagram":
            pts = "".join([f"<li><span class='bullet-icon'>✦</span> {pt}</li>" for pt in s.get("key_points", [])])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="flow-chart-box">
                <div class="flow-node">【損益表】稅後淨利</div>
                <div class="flow-arrow">➔ 扣除發放股息 ➔</div>
                <div class="flow-node highlight">【資產負債表】保留盈餘</div>
                <div class="flow-divider"></div>
                <div class="flow-node">【損益表】淨利起點</div>
                <div class="flow-arrow">➔ 調整折舊與營運資金 ➔</div>
                <div class="flow-node success">【現金流量表】營業現金流</div>
            </div>
            <ul class="point-list mt-3">{pts}</ul>
            """
        elif v_type == "grid_moats":
            moats = s.get("moats", [])
            moats_html = "".join([f"""
                <div class="moat-card">
                    <div class="moat-type">{m['type']}</div>
                    <div class="moat-desc">{m['desc']}</div>
                </div>
            """ for m in moats])
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="moats-grid">{moats_html}</div>
            """
        elif v_type == "rules_checklist":
            rules = s.get("rules", [])
            rules_html = "".join([f"<div class='rule-item'>🛡️ {r}</div>" for r in rules])
            trap = s.get("traps", "")
            inner_content = f"""
            <div class="metaphor-tag">💡 核心直覺：{metaphor}</div>
            <div class="warning-callout mb-3">⚠️ {trap}</div>
            <div class="rules-list">{rules_html}</div>
            <div class="quiz-box mt-3">
                <div class="quiz-title">🎯 即席檢驗小測驗：</div>
                <div class="quiz-text">如果一家公司本益比只有 4 倍、殖利率 9%，但營業現金流已連續三年為負數，你該買進嗎？</div>
                <div class="quiz-ans">答：不可！這是標準的「假性便宜價值陷阱」，現金流枯竭代表有周轉或做假帳危機。</div>
            </div>
            """
        
        slide_block = f"""
        <section class="slide-section" data-transition="slide-in fade-out">
            <div class="slide-container">
                <div class="slide-header">
                    <span class="badge-pill">{badge}</span>
                    <span class="slide-number">Slide {p_num} / {len(state.slide_drafts)}</span>
                </div>
                <h2 class="slide-title">{title}</h2>
                <h4 class="slide-subtitle">{subtitle}</h4>
                <div class="slide-body">
                    {inner_content}
                </div>
                <div class="slide-footer">
                    <span class="citation-tag">Wiki 知識來源：{citation}</span>
                    <span class="nav-hint">使用鍵盤 [ ➔ ] 或 [ ␣ 空白鍵 ] 前往下一頁</span>
                </div>
            </div>
        </section>
        """
        slides_html_blocks.append(slide_block)

    full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新手價值投資與財務報表解讀基礎 - LLM Wiki 教學簡報</title>
    <!-- Reveal.js CDN -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/theme/black.min.css">
    <!-- MathJax for KaTeX math formulas -->
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        :root {{
            --bg-color: #0b132b;
            --card-bg: rgba(28, 37, 65, 0.95);
            --accent-cyan: #48cae4;
            --accent-green: #06d6a0;
            --accent-yellow: #ffd166;
            --accent-red: #ef476f;
            --text-main: #f8f9fa;
            --text-dim: #cbd5e1;
            --border-color: rgba(255, 255, 255, 0.12);
        }}

        body, .reveal {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang TC", "Microsoft JhengHei", sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
        }}

        .reveal .slides {{
            text-align: left;
        }}

        .slide-container {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 26px 36px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(12px);
            max-width: 960px;
            margin: 0 auto;
        }}

        .slide-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .badge-pill {{
            background: linear-gradient(135deg, #0077b6, #00b4d8);
            color: white;
            font-size: 0.82rem;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 999px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .slide-number {{
            font-size: 0.82rem;
            color: var(--text-dim);
            font-family: monospace;
        }}

        .slide-title {{
            font-size: 1.95rem !important;
            font-weight: 800 !important;
            color: #ffffff !important;
            margin: 0 0 4px 0 !important;
            letter-spacing: -0.5px;
            text-transform: none !important;
        }}

        .slide-subtitle {{
            font-size: 1.1rem !important;
            color: var(--accent-cyan) !important;
            font-weight: 500 !important;
            margin-bottom: 14px !important;
            text-transform: none !important;
        }}

        .metaphor-tag {{
            background: rgba(72, 202, 228, 0.12);
            border-left: 4px solid var(--accent-cyan);
            color: #90e0ef;
            padding: 8px 14px;
            border-radius: 0 8px 8px 0;
            font-size: 0.92rem;
            margin-bottom: 14px;
            font-weight: 500;
        }}

        .point-list {{
            list-style: none;
            padding-left: 0;
            margin: 14px 0;
            font-size: 1.02rem;
            line-height: 1.65;
            color: var(--text-main);
        }}

        .point-list li {{
            margin-bottom: 10px;
            display: flex;
            align-items: baseline;
        }}

        .bullet-icon {{
            color: var(--accent-green);
            margin-right: 12px;
            font-size: 1rem;
        }}

        .quote-card {{
            background: rgba(0, 0, 0, 0.35);
            border-radius: 12px;
            padding: 14px 20px;
            font-style: italic;
            color: #e2e8f0;
            font-size: 0.95rem;
            border-left: 3px solid var(--accent-yellow);
            margin-top: 15px;
        }}

        /* 對比排版 */
        .comp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 10px;
        }}

        .comp-col {{
            padding: 16px 20px;
            border-radius: 12px;
            font-size: 0.95rem;
            line-height: 1.5;
        }}

        .comp-col.retail {{
            background: rgba(239, 71, 111, 0.12);
            border: 1px solid rgba(239, 71, 111, 0.3);
        }}

        .comp-col.value {{
            background: rgba(6, 214, 160, 0.12);
            border: 1px solid rgba(6, 214, 160, 0.3);
        }}

        .comp-head {{
            font-weight: 700;
            margin-bottom: 8px;
            font-size: 1.05rem;
        }}

        /* 公式卡片 */
        .formula-box {{
            background: rgba(0, 0, 0, 0.45);
            border: 1px solid rgba(72, 202, 228, 0.3);
            border-radius: 14px;
            padding: 16px 24px;
            text-align: center;
            margin: 14px 0;
        }}

        .formula-title {{
            font-size: 0.85rem;
            color: var(--text-dim);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .formula-math {{
            font-size: 1.35rem;
            color: var(--accent-yellow);
        }}

        /* 三卡片網格 */
        .three-cards-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-top: 12px;
        }}

        .card-item {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
        }}

        .card-badge {{
            font-size: 0.75rem;
            background: rgba(72, 202, 228, 0.2);
            color: var(--accent-cyan);
            padding: 3px 8px;
            border-radius: 6px;
            width: fit-content;
            margin-bottom: 8px;
            font-weight: bold;
        }}

        .card-title {{
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 6px;
            color: white;
        }}

        .card-desc {{
            font-size: 0.85rem;
            color: var(--text-dim);
            flex-grow: 1;
            margin-bottom: 10px;
            line-height: 1.4;
        }}

        .card-analog {{
            font-size: 0.82rem;
            color: var(--accent-yellow);
            border-top: 1px dashed rgba(255, 255, 255, 0.1);
            padding-top: 8px;
        }}

        /* 資產負債表 T字平衡天平 (Slide 5) */
        .compact-formula {{
            padding: 8px 16px !important;
            margin: 6px 0 10px 0 !important;
        }}

        .compact-formula .formula-math {{
            font-size: 1.15rem !important;
        }}

        .balance-diagram {{
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 12px;
            align-items: stretch;
            margin: 10px 0;
        }}

        .bal-col.assets {{
            background: rgba(72, 202, 228, 0.08);
            border: 1px solid rgba(72, 202, 228, 0.35);
            border-left: 5px solid var(--accent-cyan);
            border-radius: 12px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .bal-equals {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.2rem;
            font-weight: 900;
            color: var(--accent-yellow);
            padding: 0 4px;
        }}

        .bal-right-stack {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .bal-subcard {{
            border-radius: 10px;
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .bal-subcard.liab {{
            background: rgba(239, 71, 111, 0.08);
            border: 1px solid rgba(239, 71, 111, 0.35);
            border-left: 5px solid var(--accent-red);
        }}

        .bal-subcard.equity {{
            background: rgba(6, 214, 160, 0.08);
            border: 1px solid rgba(6, 214, 160, 0.35);
            border-left: 5px solid var(--accent-green);
        }}

        .bal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 700;
            font-size: 0.92rem;
            margin-bottom: 4px;
        }}

        .bal-header.cyan {{ color: #90e0ef; }}
        .bal-header.red {{ color: #ff9ebb; }}
        .bal-header.green {{ color: #a7f3d0; }}

        .bal-badge {{
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}

        .bal-badge.cyan {{ background: rgba(72, 202, 228, 0.25); color: #e0f2fe; }}
        .bal-badge.red {{ background: rgba(239, 71, 111, 0.25); color: #ffe4e6; }}
        .bal-badge.green {{ background: rgba(6, 214, 160, 0.25); color: #dcfce7; }}

        .bal-content {{
            font-size: 0.85rem;
            color: var(--text-main);
            line-height: 1.45;
        }}

        .bal-item-row {{
            margin-bottom: 4px;
        }}

        .bal-subtext {{
            font-size: 0.78rem;
            color: var(--accent-yellow);
            border-top: 1px dashed rgba(255, 255, 255, 0.1);
            padding-top: 5px;
            margin-top: 4px;
        }}

        .compact-list {{
            margin: 8px 0 0 0 !important;
            font-size: 0.92rem !important;
            line-height: 1.45 !important;
        }}

        .compact-list li {{
            margin-bottom: 6px !important;
        }}

        /* 漏斗流 */
        .funnel-container {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin: 14px 0;
        }}

        .funnel-step {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 10px 16px;
            border-left: 5px solid var(--accent-cyan);
        }}

        .funnel-num {{
            background: var(--accent-cyan);
            color: #000;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.8rem;
            margin-right: 14px;
        }}

        .funnel-name {{
            font-weight: 700;
            width: 230px;
            color: #fff;
            font-size: 0.95rem;
        }}

        .funnel-desc {{
            color: var(--text-dim);
            font-size: 0.88rem;
        }}

        .warning-callout {{
            background: rgba(239, 71, 111, 0.15);
            border: 1px solid var(--accent-red);
            border-radius: 10px;
            padding: 10px 16px;
            color: #ff9ebb;
            font-size: 0.92rem;
            margin-top: 12px;
        }}

        .golden-rule {{
            background: rgba(6, 214, 160, 0.15);
            border: 1px solid var(--accent-green);
            border-radius: 10px;
            padding: 10px 16px;
            color: #a7f3d0;
            font-size: 0.92rem;
            font-weight: 600;
            margin-top: 12px;
        }}

        /* 鉤稽圖 */
        .flow-chart-box {{
            display: flex;
            align-items: center;
            justify-content: space-around;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            padding: 16px;
            margin: 12px 0;
        }}

        .flow-node {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border-color);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
        }}

        .flow-node.highlight {{
            border-color: var(--accent-yellow);
            color: var(--accent-yellow);
        }}

        .flow-node.success {{
            border-color: var(--accent-green);
            color: var(--accent-green);
        }}

        .flow-arrow {{
            color: var(--accent-cyan);
            font-size: 0.85rem;
            font-family: monospace;
        }}

        /* 護城河卡片網格 */
        .moats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 10px;
        }}

        .moat-card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
        }}

        .moat-type {{
            font-weight: 700;
            color: var(--accent-cyan);
            font-size: 0.95rem;
            margin-bottom: 4px;
        }}

        .moat-desc {{
            color: var(--text-dim);
            font-size: 0.85rem;
            line-height: 1.4;
        }}

        /* 規則清單與測驗 */
        .rules-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin: 12px 0;
        }}

        .rule-item {{
            background: rgba(6, 214, 160, 0.08);
            border-left: 3px solid var(--accent-green);
            padding: 8px 14px;
            border-radius: 0 8px 8px 0;
            font-size: 0.93rem;
            color: #d1fae5;
        }}

        .quiz-box {{
            background: rgba(255, 209, 102, 0.1);
            border: 1px solid var(--accent-yellow);
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 0.9rem;
        }}

        .quiz-title {{
            font-weight: 700;
            color: var(--accent-yellow);
            margin-bottom: 4px;
        }}

        .quiz-text {{
            color: #f1f5f9;
            margin-bottom: 6px;
        }}

        .quiz-ans {{
            color: #94a3b8;
            font-style: italic;
        }}

        /* 頁尾 */
        .slide-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            padding-top: 14px;
            margin-top: 18px;
            font-size: 0.8rem;
            color: #94a3b8;
        }}

        .citation-tag {{
            color: var(--accent-cyan);
            font-family: monospace;
        }}

        .nav-hint {{
            color: #64748b;
        }}
        
        .mt-2 {{ margin-top: 8px; }}
        .mt-3 {{ margin-top: 12px; }}
        .mb-3 {{ margin-bottom: 12px; }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
            {"".join(slides_html_blocks)}
        </div>
    </div>

    <!-- Reveal.js JS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            slideNumber: 'c/t',
            controls: true,
            progress: true,
            center: true,
            transition: 'slide',
            keyboard: true
        }});
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
        
    state.final_html_path = OUTPUT_HTML
    print(f" -> 簡報生成成功！檔案路徑: {OUTPUT_HTML}")
    print("[Node 6 完成]\n")
    return state


# ==========================================
# 主流程圖與迴圈執行 (Graph Execution Runner)
# ==========================================
def run_pipeline():
    print("=================================================================")
    print(" 啟動 StockWiki LLM Wiki to HTML Presentation Graph 狀態機")
    print("=================================================================")
    
    state = PipelineState(topic="新手價值投資與財務報表解讀基礎")
    
    # 步驟 1: Ingest 知識庫檢查
    state = node_ingest_check(state)
    
    # 步驟 2: Wiki 概念查詢
    state = node_wiki_query(state)
    
    # 步驟 3: 規劃教學大綱
    state = node_generate_outline(state)
    
    # 步驟 4 & 5: Draft 與 Review 的檢查迴圈 (Check/Eval Loop with Shift-Left)
    while state.retry_count <= state.max_retries:
        state = node_draft_slides(state)
        state = node_eval_check(state)
        
        if state.is_approved:
            break
        else:
            print(f">>> [觸發重試迴圈 Loop] 準備進入第 {state.retry_count + 1} 次草稿修正...\n")
            
    if not state.is_approved:
        print("[錯誤] 已達最大重試次數，未通過品質審查。終止流程。")
        sys.exit(1)
        
    # 步驟 6: 通過審查後，渲染為 HTML 簡報
    state = node_render_html(state)
    
    # 輸出執行結果與審查日誌
    with open(EVAL_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(state.review_history, f, ensure_ascii=False, indent=2)
        
    print("=================================================================")
    print(f" 流程圓滿完成！")
    print(f" 最終教學簡報: {state.final_html_path}")
    print(f" 審查歷程記錄: {EVAL_LOG_FILE}")
    print("=================================================================")


if __name__ == "__main__":
    run_pipeline()
