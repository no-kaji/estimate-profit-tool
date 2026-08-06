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

/* サイドバーのナビゲーション項目: アイコン(線形Material Symbols)がホバーで揺れて動き、
   下端に波打つ下線が現れる。Streamlitの内部DOM構造は確認できないため、
   複数のセレクタ候補を併記して当たるようにしている。 */
section[data-testid="stSidebarNav"] a,
div[data-testid="stSidebarNavItems"] a,
nav[data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] li a {
    position: relative;
    transition: background-color 0.15s ease;
    overflow: visible !important;
}
section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a [data-testid^="stIcon"],
section[data-testid="stSidebarNav"] a span:first-child,
div[data-testid="stSidebarNavItems"] a span:first-child,
nav[data-testid="stSidebarNav"] a span:first-child,
section[data-testid="stSidebar"] li a span:first-child {
    display: inline-block;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"],
section[data-testid="stSidebarNav"] a:hover span:first-child,
div[data-testid="stSidebarNavItems"] a:hover span:first-child,
nav[data-testid="stSidebarNav"] a:hover span:first-child,
section[data-testid="stSidebar"] li a:hover span:first-child {
    transform: scale(1.22) rotate(-8deg) translateY(-1px);
}

/* ホバー時に波打つ下線(SVGの波パターンを横スクロールさせて「波打つ」動きを表現) */
section[data-testid="stSidebarNav"] a::after,
div[data-testid="stSidebarNavItems"] a::after,
nav[data-testid="stSidebarNav"] a::after,
section[data-testid="stSidebar"] li a::after {
    content: "";
    position: absolute;
    left: 10px;
    right: 10px;
    bottom: 2px;
    height: 6px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='8' viewBox='0 0 24 8'%3E%3Cpath d='M0 4 Q6 0 12 4 T24 4' stroke='%236a5fd3' fill='none' stroke-width='1.6'/%3E%3C/svg%3E");
    background-repeat: repeat-x;
    background-size: 24px 8px;
    opacity: 0;
    transform: translateY(3px);
    transition: opacity 0.2s ease, transform 0.2s ease;
    pointer-events: none;
}
section[data-testid="stSidebarNav"] a:hover::after,
div[data-testid="stSidebarNavItems"] a:hover::after,
nav[data-testid="stSidebarNav"] a:hover::after,
section[data-testid="stSidebar"] li a:hover::after {
    opacity: 0.8;
    transform: translateY(0);
    animation: nav-wave-scroll 0.9s linear infinite;
}
@keyframes nav-wave-scroll {
    from { background-position-x: 0; }
    to { background-position-x: 24px; }
}
@media (prefers-reduced-motion: reduce) {
    section[data-testid="stSidebarNav"] a:hover::after,
    div[data-testid="stSidebarNavItems"] a:hover::after,
    nav[data-testid="stSidebarNav"] a:hover::after,
    section[data-testid="stSidebar"] li a:hover::after {
        animation: none;
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
