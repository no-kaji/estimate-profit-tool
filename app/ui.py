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
   - テキスト: ホバーで拡大(迫るような元気な印象)
   - 背景: ホバーした項目の上端が波打って盛り上がるように現れる
   参考: https://b-risk.jp/blog/2021/11/hover-reference/ (テキストの拡大)
        https://kekenta-it-blog.com/icon-hover-animations-guide/ (アイコンの回転)
   Streamlitの内部DOM構造は確認できないため、複数のセレクタ候補を併記している。 */
section[data-testid="stSidebarNav"] a,
div[data-testid="stSidebarNavItems"] a,
nav[data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] li a {
    position: relative;
    isolation: isolate;
    overflow: visible !important;
}

/* 上端が波打つ背景(::beforeで疑似要素として敷き、ホバー時にせり上がらせる) */
section[data-testid="stSidebarNav"] a::before,
div[data-testid="stSidebarNavItems"] a::before,
nav[data-testid="stSidebarNav"] a::before,
section[data-testid="stSidebar"] li a::before {
    content: "";
    position: absolute;
    inset: 0 4px -4px 4px;
    z-index: -1;
    border-radius: 10px;
    background: var(--accent-soft, #eceafc);
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'%3E%3Cpath d='M0,14 C 8,2 17,2 25,14 C 33,26 42,26 50,14 C 58,2 67,2 75,14 C 83,26 92,26 100,14 L100,100 L0,100 Z'/%3E%3C/svg%3E");
    mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'%3E%3Cpath d='M0,14 C 8,2 17,2 25,14 C 33,26 42,26 50,14 C 58,2 67,2 75,14 C 83,26 92,26 100,14 L100,100 L0,100 Z'/%3E%3C/svg%3E");
    -webkit-mask-size: 100% 100%;
    mask-size: 100% 100%;
    -webkit-mask-repeat: no-repeat;
    mask-repeat: no-repeat;
    opacity: 0;
    transform: translateY(10px) scaleY(0.85);
    transform-origin: bottom;
    transition: opacity 0.25s ease, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
section[data-testid="stSidebarNav"] a:hover::before,
div[data-testid="stSidebarNavItems"] a:hover::before,
nav[data-testid="stSidebarNav"] a:hover::before,
section[data-testid="stSidebar"] li a:hover::before,
section[data-testid="stSidebarNav"] a[aria-current="page"]::before,
div[data-testid="stSidebarNavItems"] a[aria-current="page"]::before,
nav[data-testid="stSidebarNav"] a[aria-current="page"]::before,
section[data-testid="stSidebar"] li a[aria-current="page"]::before {
    opacity: 1;
    transform: translateY(0) scaleY(1);
}

/* アイコン: ホバーで回転 */
section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a [data-testid^="stIcon"] {
    display: inline-block;
    transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"] {
    transform: rotate(18deg) scale(1.15);
}

/* テキスト: ホバーで拡大(迫る) */
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
    transform: scale(1.08);
}

@media (prefers-reduced-motion: reduce) {
    section[data-testid="stSidebarNav"] a::before,
    div[data-testid="stSidebarNavItems"] a::before,
    nav[data-testid="stSidebarNav"] a::before,
    section[data-testid="stSidebar"] li a::before,
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
