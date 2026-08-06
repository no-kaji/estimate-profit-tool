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

/* サイドバー背景(ナビゲーション場)の右の枠線を、上から下まで連続した波形にする。
   個別の項目ではなく、サイドバー全体の右端の線として実装し、いずれかの項目に
   ホバーしている間、波が流れるようにアニメーションする。 */
section[data-testid="stSidebar"] {
    position: relative;
}
section[data-testid="stSidebar"]::after {
    content: "";
    position: absolute;
    top: 0;
    right: -3px;
    bottom: 0;
    width: 7px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='7' height='28' viewBox='0 0 7 28'%3E%3Cpath d='M3.5,0 C6.5,3.5 0.5,10.5 3.5,14 C6.5,17.5 0.5,24.5 3.5,28' stroke='%236a5fd3' fill='none' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: repeat-y;
    background-size: 7px 28px;
    opacity: 0.35;
    transition: opacity 0.3s ease;
    pointer-events: none;
    z-index: 5;
}
section[data-testid="stSidebar"]:hover::after {
    opacity: 1;
    animation: sidebar-border-wave-flow 1.6s linear infinite;
}
@keyframes sidebar-border-wave-flow {
    from { background-position-y: 0; }
    to { background-position-y: 28px; }
}

/* アイコン: ホバーしている間、回転し続ける(参考CodePenのfa-syncのような継続回転) */
section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a [data-testid^="stIcon"] {
    display: inline-block;
    transform-origin: center;
}
section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"] {
    animation: nav-icon-spin 1s linear infinite;
}
@keyframes nav-icon-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
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
    section[data-testid="stSidebar"]::after,
    section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
    div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
    nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
    section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"] {
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
