# -*- coding: utf-8 -*-
"""
npb_name_map.py — NPB選手名のローマ字slug/表示名マップ

pykakasiは人名（特に名乗り読み・異体字）を誤読しやすいため、
既知選手は手動マップで正確なローマ字（given-family順）を付与する。
未登録選手はKANJI_NORMで異体字を正規化した上でpykakasiにフォールバック。

キー: NPB成績表の表記（半角スペース区切り、family given）
値:   (slug, display)   slug=given-family小文字ハイフン, display="Given Family"
"""

# 異体字・旧字 → 常用字（pykakasiフォールバック時の誤読防止）
KANJI_NORM = {
    "髙": "高", "﨑": "崎", "𠮷": "吉", "德": "徳", "濵": "浜", "濱": "浜",
    "曻": "昇", "槇": "槙", "邊": "辺", "邉": "辺", "齋": "斎", "齊": "斉",
    "桒": "桑", "栁": "柳", "祐": "祐", "悧": "利", "塚": "塚", "眞": "真",
}

# 既知選手マップ（2026 規定到達者 + 主要救援）
NAME_MAP = {
    # --- Central batters ---
    "佐藤 輝明": ("teruaki-sato", "Teruaki Sato"),
    "度会 隆輝": ("ryuki-watarai", "Ryuki Watarai"),
    "坂倉 将吾": ("shogo-sakakura", "Shogo Sakakura"),
    "森下 翔太": ("shota-morishita", "Shota Morishita"),
    "村松 開人": ("kaito-muramatsu", "Kaito Muramatsu"),
    "大山 悠輔": ("yusuke-oyama", "Yusuke Oyama"),
    "中野 拓夢": ("takumu-nakano", "Takumu Nakano"),
    "岩田 幸宏": ("yukihiro-iwata", "Yukihiro Iwata"),
    "菊池 涼介": ("ryosuke-kikuchi", "Ryosuke Kikuchi"),
    "細川 成也": ("seiya-hosokawa", "Seiya Hosokawa"),
    "佐野 恵太": ("keita-sano", "Keita Sano"),
    "小園 海斗": ("kaito-kozono", "Kaito Kozono"),
    # --- Pacific batters ---
    "小川 龍成": ("ryusei-ogawa", "Ryusei Ogawa"),
    "辰己 涼介": ("ryosuke-tatsumi", "Ryosuke Tatsumi"),
    "水野 達稀": ("tatsuki-mizuno", "Tatsuki Mizuno"),
    "藤原 恭大": ("kyota-fujiwara", "Kyota Fujiwara"),
    "村林 一輝": ("kazuki-murabayashi", "Kazuki Murabayashi"),
    "西川 史礁": ("mishou-nishikawa", "Mishou Nishikawa"),
    "周東 佑京": ("yuki-shuto", "Yuki Shuto"),
    "太田 椋": ("ryo-ota", "Ryo Ota"),
    "近藤 健介": ("kensuke-kondo", "Kensuke Kondo"),
    "西川 龍馬": ("ryoma-nishikawa", "Ryoma Nishikawa"),
    "牧原 大成": ("taisei-makihara", "Taisei Makihara"),
    "栗原 陵矢": ("ryoya-kurihara", "Ryoya Kurihara"),
    "森 友哉": ("tomoya-mori", "Tomoya Mori"),
    "浅村 栄斗": ("hideto-asamura", "Hideto Asamura"),
    "宗 佑磨": ("yuma-so", "Yuma So"),
    "柳田 悠岐": ("yuki-yanagita", "Yuki Yanagita"),
    "黒川 史陽": ("fumiya-kurokawa", "Fumiya Kurokawa"),
    "渡部 聖弥": ("seiya-watanabe", "Seiya Watanabe"),
    "中川 圭太": ("keita-nakagawa", "Keita Nakagawa"),
    "紅林 弘太郎": ("kotaro-kurebayashi", "Kotaro Kurebayashi"),
    "郡司 裕也": ("yuya-gunji", "Yuya Gunji"),
    "清宮 幸太郎": ("kotaro-kiyomiya", "Kotaro Kiyomiya"),
    "万波 中正": ("chusei-manami", "Chusei Manami"),
    "寺地 隆成": ("ryusei-terachi", "Ryusei Terachi"),
    "山川 穂高": ("hotaka-yamakawa", "Hotaka Yamakawa"),
    # --- Central pitchers ---
    "髙橋 遥人": ("haruto-takahashi", "Haruto Takahashi"),
    "栗林 良吏": ("ryoji-kuribayashi", "Ryoji Kuribayashi"),
    "大野 雄大": ("yudai-ono", "Yudai Ono"),
    "東 克樹": ("katsuki-azuma", "Katsuki Azuma"),
    "柳 裕也": ("yuya-yanagi", "Yuya Yanagi"),
    "山野 太一": ("taichi-yamano", "Taichi Yamano"),
    "村上 頌樹": ("shoki-murakami", "Shoki Murakami"),
    "金丸 夢斗": ("yumeto-kanemaru", "Yumeto Kanemaru"),
    "石田 裕太郎": ("yutaro-ishida", "Yutaro Ishida"),
    "床田 寛樹": ("hiroki-tokoda", "Hiroki Tokoda"),
    "髙橋 宏斗": ("hiroto-takahashi", "Hiroto Takahashi"),
    "才木 浩人": ("hiroto-saiki", "Hiroto Saiki"),
    "山﨑 康晃": ("yasuaki-yamasaki", "Yasuaki Yamasaki"),
    "大勢": ("taisei", "Taisei"),
    "田中 瑛斗": ("akito-tanaka", "Akito Tanaka"),
    "中川 虎大": ("kodai-nakagawa", "Kodai Nakagawa"),
    "星 知弥": ("tomoya-hoshi", "Tomoya Hoshi"),
    # --- Pacific pitchers ---
    "平良 海馬": ("kaima-taira", "Kaima Taira"),
    "田中 晴也": ("seiya-tanaka", "Seiya Tanaka"),
    "細野 晴希": ("haruki-hosono", "Haruki Hosono"),
    "上沢 直之": ("naoyuki-uesawa", "Naoyuki Uesawa"),
    "毛利 海大": ("kaito-mori", "Kaito Mori"),
    "荘司 康誠": ("kosei-shoji", "Kosei Shoji"),
    "九里 亜蓮": ("aren-kuri", "Aren Kuri"),
    "瀧中 瞭太": ("ryota-takinaka", "Ryota Takinaka"),
    "松本 晴": ("sei-matsumoto", "Sei Matsumoto"),
    "武内 夏暉": ("natsuki-takeuchi", "Natsuki Takeuchi"),
    "伊藤 大海": ("hiromi-ito", "Hiromi Ito"),
    "有原 航平": ("kohei-arihara", "Kohei Arihara"),
    "渡邉 勇太朗": ("yutaro-watanabe", "Yutaro Watanabe"),
    "達 孝太": ("kota-tatsu", "Kota Tatsu"),
    "寺西 成騎": ("naruki-teranishi", "Naruki Teranishi"),
    "横山 陸人": ("rikuto-yokoyama", "Rikuto Yokoyama"),
    "藤平 尚真": ("shoma-fujihira", "Shoma Fujihira"),
    "鈴木 翔天": ("shoten-suzuki", "Shoten Suzuki"),
    "田中 正義": ("masayoshi-tanaka", "Masayoshi Tanaka"),
}
