from __future__ import annotations

from copy import deepcopy
from typing import Any

from .item_mechanics import item_combat_spec
from .world_state import current_location_id


class ShopError(ValueError):
    pass


def require_exploration(session: dict[str, Any]) -> None:
    if session.get("game_over"):
        raise ShopError("物語はここで終わりました。")
    if session.get("combat") or session.get("combat_start_requested"):
        raise ShopError("戦闘中です。")


def item_category(item: dict[str, Any]) -> str:
    if item.get("key_item"):
        return "key"
    if item.get("category") in {"consumable", "equipment", "material", "key"}:
        return item["category"]
    spec = item_combat_spec(item)
    if spec.get("kind") in {"weapon", "armor", "equipment", "passive"} or spec.get("consumable") is False:
        return "equipment"
    if spec.get("kind"):
        return "consumable"
    # TODO(design): 携帯食、錆びた王冠没有 combat.kind，保留未分组，等待指定 category。
    return ""


def _shop(session: dict[str, Any], shop_id: str) -> dict[str, Any]:
    require_exploration(session)
    shop = next((s for s in session.get("scenario_pack", {}).get("shops", []) if s["id"] == shop_id), None)
    if not shop or shop["location_id"] != current_location_id(session):
        raise ShopError("この行動は現在選択できません。")
    return shop


def _stock(session: dict[str, Any], shop: dict[str, Any]) -> dict[str, Any]:
    stock = session.setdefault("shop_stock", {}).setdefault(shop["id"], {})
    for entry in shop["items"]:
        stock.setdefault(entry["item_id"], entry.get("stock"))
    return stock


def _owned(session: dict[str, Any], item_id: str) -> dict[str, Any]:
    from .state import _enrich_item

    for raw in session["character"].get("inventory", []):
        item = _enrich_item(raw if isinstance(raw, dict) else {"name": raw}, session["scenario_pack"])
        if item_id in (item.get("id"), item.get("name")) and item.get("quantity", 1) > 0:
            return item
    raise ShopError("道具が見つかりません。")


def _sell_price(session: dict[str, Any], shop: dict[str, Any], item: dict[str, Any]) -> int:
    # Half of the cheapest price in any shop, so buying low in one shop and selling in another never profits.
    prices = [int(offer["price"]) for s in session["scenario_pack"].get("shops", []) for offer in s["items"]
              if offer["item_id"] == item.get("id")]
    return min(prices) // 2 if prices else 5


def public_shop(session: dict[str, Any], shop_id: str) -> dict[str, Any]:
    from .state import _enrich_item, action_requirement_status

    shop = _shop(session, shop_id)
    stock = _stock(session, shop)
    catalog = {item["id"]: item for item in session["scenario_pack"].get("items", [])}
    public = {key: deepcopy(shop.get(key)) for key in
              ("id", "location_id", "keeper_npc", "title", "greeting", "buy_line", "sell_line", "poor_line", "buys")}
    npc = next((npc for npc in session["scenario_pack"].get("npcs", []) if npc["id"] == shop["keeper_npc"]), {})
    public["portrait_image"] = npc.get("portrait_image") or npc.get("image", "")
    public["gold"] = session["character"].get("gold", 0)
    public["items"] = []
    for offer in shop["items"]:
        item = _enrich_item(catalog[offer["item_id"]], session["scenario_pack"])
        enabled, reason = action_requirement_status({"requirements": offer.get("requirements", {})}, session)
        public["items"].append({**item, "item_id": offer["item_id"], "price": offer["price"],
                                "stock": stock[offer["item_id"]], "enabled": enabled, "reason": reason})
    public["sell_items"] = []
    if shop.get("buys"):
        for raw in session["character"].get("inventory", []):
            item = _enrich_item(raw if isinstance(raw, dict) else {"name": raw}, session["scenario_pack"])
            if not item.get("key_item") and not item.get("non_removable") and not item_combat_spec(item).get("non_removable"):
                public["sell_items"].append({**item, "item_id": item.get("id") or item["name"],
                                             "price": _sell_price(session, shop, item), "stock": item["quantity"]})
    return public


def trade(session: dict[str, Any], shop_id: str, item_id: str, quantity: int, *, selling: bool = False) -> dict[str, Any]:
    from .state import apply_state_delta, action_requirement_status

    shop = _shop(session, shop_id)
    if type(quantity) is not int or quantity < 1:
        raise ShopError("この行動は条件を満たしていません。")
    stock = _stock(session, shop)
    if selling:
        item = _owned(session, item_id)
        if not shop.get("buys") or item.get("key_item") or item.get("non_removable") or item_combat_spec(item).get("non_removable"):
            raise ShopError("この行動は現在選択できません。")
        if quantity > item["quantity"]:
            raise ShopError("道具が見つかりません。")
        delta = {"gold_change": _sell_price(session, shop, item) * quantity,
                 "inventory_remove": [{"name": item["name"], "quantity": quantity}]}
    else:
        offer = next((entry for entry in shop["items"] if entry["item_id"] == item_id), None)
        if not offer:
            raise ShopError("道具が見つかりません。")
        if stock[item_id] is not None and quantity > stock[item_id]:
            raise ShopError("売り切れ")
        if session["character"].get("gold", 0) < offer["price"] * quantity:
            raise ShopError(shop["poor_line"])
        enabled, reason = action_requirement_status({"requirements": offer.get("requirements", {})}, session)
        if not enabled:
            raise ShopError(reason)
        item = next(item for item in session["scenario_pack"]["items"] if item["id"] == item_id)
        delta = {"gold_change": -offer["price"] * quantity,
                 "inventory_add": [{"id": item_id, "name": item["name"], "quantity": quantity}]}
        if offer.get("equip_on_buy"):
            delta["equip_item"] = item["name"]
        if stock[item_id] is not None:
            stock[item_id] -= quantity
    apply_state_delta(session, delta)
    return delta


def use_item(session: dict[str, Any], item_id: str) -> str:
    from . import combat
    from .state import apply_state_delta, record_state_event

    require_exploration(session)
    item = _owned(session, item_id)
    spec = item_combat_spec(item)
    kind = spec.get("kind")
    if kind not in {"heal", "restore"}:
        raise ShopError("この行動は現在選択できません。")
    resource = "hp" if kind == "heal" else str(spec.get("resource") or "mp").lower()
    if resource not in {"hp", "mp", "sp"}:
        raise ShopError("未対応の回復対象です。")
    actor = session["character"]
    missing = actor[f"max_{resource}"] - actor[resource]
    if missing <= 0:
        raise ShopError("これ以上回復する必要はない。")
    formula = spec.get("healing" if kind == "heal" else "amount") or spec.get("formula") or "10"
    amount, _ = combat._roll_formula(str(formula), actor, combat.random)
    actual = min(missing, max(0, amount))
    delta = {f"{resource}_change": actual}
    if spec.get("consumable", True):
        delta["inventory_remove"] = [{"name": item["name"], "quantity": 1}]
    apply_state_delta(session, delta)
    text = f"{item['name']}を使った。{resource.upper()}が{actual}回復した。"
    record_state_event(session, "item_used", text, {"item_id": item_id, "resource": resource, "amount": actual})
    return text
