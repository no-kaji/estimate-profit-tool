from __future__ import annotations


def generate_personal_seal_svg(name: str, color: str = "#c0392b") -> str:
    """個人印鑑(印影)をSVGで生成する。日本語フォントの同梱が不要なブラウザ側描画にする。"""
    label = (name or "印")[:4]
    return f"""
<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" width="96" height="96">
  <circle cx="60" cy="60" r="54" fill="none" stroke="{color}" stroke-width="5"/>
  <circle cx="60" cy="60" r="44" fill="none" stroke="{color}" stroke-width="2"/>
  <text x="60" y="68" text-anchor="middle"
        font-family="'Hiragino Mincho ProN','Yu Mincho',serif"
        font-size="30" fill="{color}">{label}</text>
</svg>
""".strip()


def generate_company_seal_svg(company_name: str, color: str = "#c0392b") -> str:
    """社判(角印イメージ)をSVGで生成する。"""
    label = (company_name or "社印")[:6]
    return f"""
<svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect x="8" y="8" width="124" height="124" fill="none" stroke="{color}" stroke-width="5"/>
  <text x="70" y="80" text-anchor="middle"
        font-family="'Hiragino Mincho ProN','Yu Mincho',serif"
        font-size="26" fill="{color}">{label}</text>
</svg>
""".strip()


def seal_img_tag(svg: str, size: int = 90) -> str:
    """SVG文字列をst.markdown(unsafe_allow_html=True)で表示できる<img>タグに変換する。"""
    import base64

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{encoded}" width="{size}" height="{size}" alt="印影">'
