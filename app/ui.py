from __future__ import annotations

import streamlit as st

_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'M PLUS Rounded 1c', 'Hiragino Maru Gothic ProN', 'Yu Gothic UI', sans-serif !important;
}

/* ボタン */
div[data-testid="stButton"] button,
div[data-testid="stFormSubmitButton"] button,
div[data-testid="stDownloadButton"] button {
    border-radius: 999px !important;
    font-weight: 700 !important;
    padding: 0.5rem 1.4rem !important;
    border: 1.5px solid rgba(58, 53, 100, 0.15) !important;
    transition: transform 0.05s ease-in-out;
}
div[data-testid="stButton"] button:hover,
div[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-1px);
}
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #6a5fd3, #8f7ff0) !important;
    border: none !important;
}

/* 入力欄・セレクトボックス */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] {
    border-radius: 14px !important;
}

/* カード・コンテナ・エキスパンダー
   角丸が実際の枠線(details/summary等の内側要素)ではなく外側の透明なラッパーにしか
   掛かっておらず、四隅が欠けて見える不具合があったため、実際に背景・枠線を描画している
   要素(details, summary, 直下のdiv)にも明示的にborder-radius+overflow:hiddenを適用する。 */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stExpander"],
div[data-testid="stForm"] {
    border-radius: 18px !important;
    overflow: hidden;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stExpander"] details,
div[data-testid="stExpander"] > div,
div[data-testid="stForm"] > div {
    border-radius: 18px !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    border-radius: 18px 18px 0 0 !important;
}

/* メトリクス(収支サマリ): 既定だと数値が大きすぎるため縮小する */
div[data-testid="stMetric"] {
    background: rgba(122, 108, 224, 0.08);
    border-radius: 16px;
    padding: 10px 14px;
}
div[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
}

/* タブ */
button[data-baseweb="tab"] {
    border-radius: 999px 999px 0 0 !important;
}

/* サイドバー */
section[data-testid="stSidebar"] {
    border-radius: 0 20px 20px 0;
}

/* サイドバーのナビゲーション項目
   - アイコン(線形Material Symbols): ホバーで回転
   - テキスト: ホバーで上にUP(迫るような元気な印象)
   - 文字を囲む背景ボックスは一切表示しない(現在のページであっても囲まない)
   - ナビゲーションバー右の枠線が、ホバーした項目の高さの位置だけ盛り上がって波打つ
   参考: https://b-risk.jp/blog/2021/11/hover-reference/ (テキストが迫る)
        https://kekenta-it-blog.com/icon-hover-animations-guide/ (アイコンの回転)
   Streamlitの内部DOM構造は確認できないため、複数のセレクタ候補を併記している。 */

/* Streamlit標準の「現在のページ」を示す背景ボックスも含め、ナビ項目の背景ボックスは
   常に非表示にする(文字の囲いは不要という指示のため)。 */
section[data-testid="stSidebarNav"] a,
div[data-testid="stSidebarNavItems"] a,
nav[data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] li a,
section[data-testid="stSidebarNav"] a[aria-current="page"],
div[data-testid="stSidebarNavItems"] a[aria-current="page"],
nav[data-testid="stSidebarNav"] a[aria-current="page"],
section[data-testid="stSidebar"] li a[aria-current="page"] {
    position: relative;
    isolation: isolate;
    overflow: visible !important;
    background: transparent !important;
    box-shadow: none !important;
}
section[data-testid="stSidebarNav"] a[aria-current="page"] p,
div[data-testid="stSidebarNavItems"] a[aria-current="page"] p,
nav[data-testid="stSidebarNav"] a[aria-current="page"] p {
    font-weight: 800 !important;
}

/* サイドバー(ナビゲーション場)の右の枠線は常時は細い直線。
   ホバーした項目の高さの位置だけ、その枠線自体が右に膨れ上がる
   (枠線と地続きの丸みとして生えさせることで、独立した図形ではなく
   「枠が動いている」ように見せる)。全体が揺れる演出ではなく、
   あくまでホバーした一か所だけが膨らむ。 */
section[data-testid="stSidebar"] {
    position: relative;
    border-right: 2px solid rgba(106, 95, 211, 0.3);
}
section[data-testid="stSidebarNav"] a::after,
div[data-testid="stSidebarNavItems"] a::after,
nav[data-testid="stSidebarNav"] a::after,
section[data-testid="stSidebar"] li a::after {
    content: "";
    position: absolute;
    top: 50%;
    right: -2px;
    width: 20px;
    height: 60%;
    background: #6a5fd3;
    border-radius: 50%;
    transform: translateY(-50%) scaleX(0);
    transform-origin: left center;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    pointer-events: none;
    z-index: 5;
}
section[data-testid="stSidebarNav"] a:hover::after,
div[data-testid="stSidebarNavItems"] a:hover::after,
nav[data-testid="stSidebarNav"] a:hover::after,
section[data-testid="stSidebar"] li a:hover::after {
    transform: translateY(-50%) scaleX(1);
}

/* アイコン: ホバーで立体的な影を伴って浮き上がるシャドウ効果 */
section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a [data-testid^="stIcon"] {
    display: inline-block;
    transition: transform 0.3s ease, filter 0.3s ease;
}
section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"] {
    transform: translateY(-4px);
    filter: drop-shadow(0 6px 8px rgba(106, 95, 211, 0.45));
}

/* テキスト: ホバーで上にUP+拡大(迫る) */
section[data-testid="stSidebarNav"] a p,
div[data-testid="stSidebarNavItems"] a p,
nav[data-testid="stSidebarNav"] a p,
section[data-testid="stSidebar"] li a span:last-child {
    display: inline-block;
    transition: transform 0.2s ease;
    transform-origin: left center;
}
section[data-testid="stSidebarNav"] a:hover p,
div[data-testid="stSidebarNavItems"] a:hover p,
nav[data-testid="stSidebarNav"] a:hover p,
section[data-testid="stSidebar"] li a:hover span:last-child {
    transform: translateY(-3px) scale(1.1);
}

@media (prefers-reduced-motion: reduce) {
    section[data-testid="stSidebarNav"] a::after,
    div[data-testid="stSidebarNavItems"] a::after,
    nav[data-testid="stSidebarNav"] a::after,
    section[data-testid="stSidebar"] li a::after,
    section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
    div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
    nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
    section[data-testid="stSidebar"] li a [data-testid^="stIcon"] {
        transition: none;
    }
}

/* 見出しのアクセントカラー */
h1, h2, h3 {
    color: #362f66;
}
</style>
"""


def apply_theme() -> None:
    st.markdown(_THEME_CSS, unsafe_allow_html=True)
