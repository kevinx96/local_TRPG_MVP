"""Epilogue lines shown after a good ending; each reflects a choice the player made (written by the design lead)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
GOOD = ["ignis_defeated", "ignis_purified", "draco_defeated", "draco_defeated_with_ignis"]
TRUE_ENDINGS = ["draco_defeated", "draco_defeated_with_ignis"]

EPILOGUES = [
    {"id": "king_confession", "endings": TRUE_ENDINGS,
     "text": "国王エドワードは十年前の過ちを民の前で打ち明け、竜の谷へ和解の使者を送った。"},
    {"id": "ignis_returns", "endings": GOOD, "requirements": {"flag": "ignis_purified"},
     "text": "正気を取り戻したイグニスは竜の谷へ帰り、二度と人里を焼くことはなかった。"},
    {"id": "mina_done", "endings": GOOD, "requirements": {"flag": "mina_quest_done"},
     "text": "ミーナは師匠のもとで修行を続け、のちに『虹晶の魔法使い』と呼ばれるようになった。"},
    {"id": "mina_alone", "endings": GOOD, "requirements": {"all": [{"flag": "met_mina"}, {"not_flag": "mina_quest_done"}]},
     "text": "洞窟で出会った見習い魔法使いは、自力で王都へ帰り着いたらしい。師匠にこっぴどく叱られたそうだ。"},
    {"id": "warlock", "endings": GOOD, "requirements": {"flag": "warlock_rescue_available"},
     "text": "青いローブの魔法使いは今日も魔法店で気だるげに店番をしている。窓辺には、溶けない氷の花が一輪飾られている。"},
    {"id": "robin", "endings": GOOD, "requirements": {"flag": "recruited_robin"},
     "text": "ロビンは礼の一言もなく姿を消した。ただ、王都の貧しい家々の戸口に、ときおり金貨が置かれるようになった。"},
    {"id": "sarah", "endings": GOOD, "requirements": {"flag": "sarah_moss_done"},
     "text": "サラの母親は光苔の薬で快復した。道具屋には今日も明るい声が響いている。"},
    {"id": "gald_saved", "endings": GOOD, "requirements": {"flag": "saved_gald"},
     "text": "行商人ガルドは王都と麓の村を結ぶ交易路を開き、『英雄の荷車』を名乗って今日も旅を続けている。"},
    {"id": "gald_abandoned", "endings": GOOD, "requirements": {"flag": "abandoned_gald"},
     "text": "闇の森の街道で、壊れた荷車だけが見つかった。持ち主の行方は分からない。"},
    {"id": "robert", "endings": GOOD, "requirements": {"flag": "robert_hammer_returned"},
     "text": "ローベルトは父の形見のハンマーを手に、再び竜の鱗をも断つ剣を打ち始めた。"},
    {"id": "riku_returned", "endings": GOOD, "requirements": {"flag": "riku_returned"},
     "text": "麓の村は少しずつ再建されている。リクは毎朝、村の入口で旅人に手を振っている。"},
    {"id": "riku_abandoned", "endings": GOOD, "requirements": {"flag": "riku_abandoned"},
     "text": "麓の村が再建されても、長老はあの夜のことを決して語ろうとしなかった。"},
    {"id": "goblin_returned", "endings": GOOD, "requirements": {"flag": "returned_lost_goblin_box"},
     "text": "迷子のゴブリンは箱を抱えて一族のもとへ帰った。それ以来、闇の森の小鬼たちは旅人を襲わなくなったという。"},
    {"id": "goblin_betrayed", "endings": GOOD, "requirements": {"flag": "betrayed_lost_goblin"},
     "text": "闇の森では今も、人間を恨むゴブリンたちが旅人を待ち伏せている。"},
    {"id": "fire_seed_removed", "endings": GOOD, "requirements": {"flag": "fire_seed_removed"},
     "text": "胸の火種は消え去った。骸骨の魔法使いザンザスの行方を知る者はいない。"},
    {"id": "xanxus_core", "endings": GOOD, "requirements": {"flag": "xanxus_took_core"},
     "text": "紅竜の心臓を手にしたザンザスは、どこかで新たな企みを巡らせているという。"},
    {"id": "king_trust_only", "endings": ["ignis_defeated", "ignis_purified"], "requirements": {"flag": "king_trust"},
     "text": "国王は祝宴の席で、時おり将軍の横顔を静かに見つめていた。"},
]


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    pack = json.loads(text)
    pack["epilogues"] = EPILOGUES
    indent = 2 if '\n  "' in text[:200] else None
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    for name in PACKS:
        apply(ROOT / "host/prompt/processed" / name)
