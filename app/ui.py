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
   - アイコン・テキスト: ホバーで同じ中心軸(transform-origin: center)で拡大する
     (位置がずれないよう、上下方向の移動は行わない)
   - 文字を囲む背景ボックスは一切表示しない(現在のページであっても囲まない)
   - 境界線のホバー演出は行わない
   Streamlitの内部DOM構造は確認できないため、複数のセレクタ候補を併記している。 */

/* Streamlit標準の「現在のページ」を示す背景ボックスも含め、ナビ項目の背景ボックスは
   常に非表示にする(文字の囲いは不要という指示のため)。DOM構造を実機確認できないため、
   a要素自身だけでなく親のli/div、内側のすべての子要素にもワイルドカードで適用し、
   どの階層に背景が付いていても確実に消す。 */
section[data-testid="stSidebarNav"] li,
section[data-testid="stSidebarNav"] li *,
div[data-testid="stSidebarNavItems"] li,
div[data-testid="stSidebarNavItems"] li *,
nav[data-testid="stSidebarNav"] li,
nav[data-testid="stSidebarNav"] li *,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] li * {
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
}
section[data-testid="stSidebarNav"] a,
div[data-testid="stSidebarNavItems"] a,
nav[data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] li a {
    position: relative;
    isolation: isolate;
    overflow: visible !important;
}
section[data-testid="stSidebarNav"] a[aria-current="page"] p,
div[data-testid="stSidebarNavItems"] a[aria-current="page"] p,
nav[data-testid="stSidebarNav"] a[aria-current="page"] p {
    font-weight: 800 !important;
}

/* アイコン: ホバーで拡大(中心軸で拡大するため上下にずれない)。
   Material Symbolsのアイコンがどの要素で描画されているか確認できないため、
   考えられる候補(testid付きspan、svg、リンク直下の1つ目のspan)をすべて併記する。 */
section[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a [data-testid^="stIcon"],
section[data-testid="stSidebarNav"] a svg,
div[data-testid="stSidebarNavItems"] a svg,
nav[data-testid="stSidebarNav"] a svg,
section[data-testid="stSidebar"] li a svg,
section[data-testid="stSidebarNav"] a span:first-child,
div[data-testid="stSidebarNavItems"] a span:first-child,
nav[data-testid="stSidebarNav"] a span:first-child,
section[data-testid="stSidebar"] li a span:first-child {
    display: inline-block;
    transition: transform 0.25s ease;
    transform-origin: center;
}
section[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
div[data-testid="stSidebarNavItems"] a:hover [data-testid^="stIcon"],
nav[data-testid="stSidebarNav"] a:hover [data-testid^="stIcon"],
section[data-testid="stSidebar"] li a:hover [data-testid^="stIcon"],
section[data-testid="stSidebarNav"] a:hover svg,
div[data-testid="stSidebarNavItems"] a:hover svg,
nav[data-testid="stSidebarNav"] a:hover svg,
section[data-testid="stSidebar"] li a:hover svg,
section[data-testid="stSidebarNav"] a:hover span:first-child,
div[data-testid="stSidebarNavItems"] a:hover span:first-child,
nav[data-testid="stSidebarNav"] a:hover span:first-child,
section[data-testid="stSidebar"] li a:hover span:first-child {
    transform: scale(1.2);
}

/* テキスト: ホバーで拡大(アイコンと同じくtransform-origin: centerで、上下にずれない) */
section[data-testid="stSidebarNav"] a p,
div[data-testid="stSidebarNavItems"] a p,
nav[data-testid="stSidebarNav"] a p,
section[data-testid="stSidebar"] li a span:last-child {
    display: inline-block;
    transition: transform 0.25s ease;
    transform-origin: center;
}
section[data-testid="stSidebarNav"] a:hover p,
div[data-testid="stSidebarNavItems"] a:hover p,
nav[data-testid="stSidebarNav"] a:hover p,
section[data-testid="stSidebar"] li a:hover span:last-child {
    transform: scale(1.1);
}

@media (prefers-reduced-motion: reduce) {
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
