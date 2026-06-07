"""Travel quest module: multi-step route-based quests with POI discovery."""

import math
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from .config import load_json, save_json, is_in_idle_window
from .task_manager import load_tasks, save_tasks, get_user_state, save_user_state


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── POI management ───────────────────────────────────────────────────────────


def get_pois() -> list[dict[str, Any]]:
    return load_json("pois.json")


def save_pois(pois: list[dict[str, Any]]) -> None:
    save_json("pois.json", pois)


def add_poi_interactive() -> None:
    """Interactively add a new POI."""
    pois = get_pois()
    print("── 添加兴趣点(POI) ──")
    name = input("名称: ").strip()
    if not name:
        print("已取消。")
        return
    ptype = input("类型(alley/community/landmark/trail/shop/garden/art/other): ").strip() or "other"
    lat_str = input("纬度(可选): ").strip()
    lon_str = input("经度(可选): ").strip()
    tags_str = input("标签(逗号分隔): ").strip()
    actions_str = input("趣味动作(逗号分隔): ").strip()

    poi = {
        "id": f"poi_{uuid.uuid4().hex[:6]}",
        "name": name,
        "type": ptype,
        "lat": float(lat_str) if lat_str else 0.0,
        "lon": float(lon_str) if lon_str else 0.0,
        "tags": [t.strip() for t in tags_str.split(",")] if tags_str else [],
        "fun_actions": [a.strip() for a in actions_str.split(",")] if actions_str else ["停下来观察周围"],
    }
    pois.append(poi)
    save_pois(pois)
    print(f"✓ 兴趣点「{name}」已添加。")


# ── OSM query (optional) ────────────────────────────────────────────────────


def _query_osm(lat: float, lon: float, radius_m: int = 3000) -> list[dict[str, Any]]:
    """Query OpenStreetMap Overpass API for non-commercial POIs nearby."""
    import requests

    radius = radius_m
    query = f"""
    [out:json][timeout:15];
    (
      node["historic"~"wayside_shrine|memorial|monument"](around:{radius},{lat},{lon});
      node["leisure"~"park|garden|playground"](around:{radius},{lat},{lon});
      node["highway"~"pedestrian"](around:{radius},{lat},{lon});
      node["tourism"~"artwork|viewpoint"](around:{radius},{lat},{lon});
      node["natural"~"peak|spring|tree"](around:{radius},{lat},{lon});
      way["leisure"~"park|garden"](around:{radius},{lat},{lon});
      way["highway"~"pedestrian"](around:{radius},{lat},{lon});
    );
    out center;
    """

    try:
        resp = requests.get(
            "https://overpass-api.de/api/interpreter",
            params={"data": query},
            timeout=20,
            headers={"User-Agent": "IsekaiDailySystem/1.0"},
        )
        data = resp.json()
        elements = data.get("elements", [])
        results: list[dict[str, Any]] = []
        for el in elements[:10]:
            tags = el.get("tags", {})
            name = tags.get("name", tags.get("historic", tags.get("leisure", "未知地点")))
            lat_el = el.get("lat") or (el.get("center", {}).get("lat", lat))
            lon_el = el.get("lon") or (el.get("center", {}).get("lon", lon))
            results.append({
                "id": f"osm_{el.get('id', uuid.uuid4().hex[:6])}",
                "name": str(name),
                "type": tags.get("leisure", tags.get("highway", tags.get("historic", "other"))),
                "lat": lat_el,
                "lon": lon_el,
                "tags": list(tags.values())[:3],
                "fun_actions": ["探索这个OSM发现的地点", "拍一张照片记录", "观察周围的细节"],
            })
        return results
    except Exception as e:
        print(f"[OSM] 查询失败: {e}")
        return []


# ── Travel quest generation ──────────────────────────────────────────────────


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon points."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _route_distance(pois: list[dict[str, Any]]) -> float:
    """Calculate total route distance following POI order (straight lines)."""
    dist = 0.0
    for i in range(len(pois) - 1):
        dist += _haversine(
            pois[i].get("lat", 0), pois[i].get("lon", 0),
            pois[i + 1].get("lat", 0), pois[i + 1].get("lon", 0),
        )
    return dist


def generate_travel(user_lat: float = 0.0, user_lon: float = 0.0, preferred_duration: int = 60) -> dict[str, Any] | None:
    """Generate a multi-step travel quest.

    Args:
        user_lat: User's current latitude.
        user_lon: User's current longitude.
        preferred_duration: Target total duration in minutes (30-120).
    """
    # Check existing travel quests
    existing = [t for t in load_tasks() if t.get("type") == "travel" and t.get("status") == "active"]
    if existing:
        print(f"⚠ 已有 {len(existing)} 个活跃旅行任务。生成新任务将覆盖旧任务。")
        ans = input("确认覆盖？(y/n): ").strip().lower()
        if ans != "y":
            print("已取消。")
            return None
        for t in existing:
            t["status"] = "expired"
        save_tasks(load_tasks())

    # Get POIs
    pois = get_pois()
    cfg = load_json("config.json")
    if cfg.get("use_osm_api", False) and user_lat != 0.0:
        print("[OSM] 正在查询附近兴趣点...")
        osm_pois = _query_osm(user_lat, user_lon)
        pois = pois + osm_pois

    if len(pois) < 3:
        print("✗ 兴趣点不足（至少需要3个）。请先通过 add_poi 添加或开启 OSM API。")
        return None

    # Select 3~5 POIs
    num_stops = random.randint(3, min(5, len(pois)))
    selected = random.sample(pois, num_stops)

    # Sort by distance from user (if coordinates available)
    if user_lat != 0.0 or user_lon != 0.0:
        selected.sort(key=lambda p: _haversine(user_lat, user_lon, p.get("lat", 0), p.get("lon", 0)))
    else:
        random.shuffle(selected)

    # Build steps
    steps: list[dict[str, Any]] = []
    total_time = 0
    total_dist = 0.0

    # Distance between consecutive POIs
    for i, poi in enumerate(selected):
        action = random.choice(poi.get("fun_actions", ["探索此地"]))
        step_time = random.randint(5, 15)
        step_dist = 0.0
        if i > 0:
            step_dist = _haversine(
                selected[i - 1].get("lat", 0), selected[i - 1].get("lon", 0),
                poi.get("lat", 0), poi.get("lon", 0),
            )

        steps.append({
            "index": i,
            "poi_id": poi["id"],
            "poi_name": poi["name"],
            "action": action,
            "estimated_minutes": step_time,
            "segment_distance_m": int(step_dist),
            "completed": False,
            "reward_exp": 10,
            "reward_gold": 5,
        })
        total_time += step_time
        total_dist += step_dist

    # Add travel from user to first POI
    if user_lat != 0.0 and user_lon != 0.0 and steps:
        d = _haversine(user_lat, user_lon, selected[0].get("lat", 0), selected[0].get("lon", 0))
        steps[0]["segment_distance_m"] = int(d)
        total_dist += d

    # Bonus for completing all steps
    bonus_exp = num_stops * 15
    bonus_gold = num_stops * 10

    # Expiration: 24-48 hours
    expires_hours = random.randint(24, 48)

    title_prefixes = ["远征", "探索行", "秘境巡礼", "微旅行"]
    prefix = random.choice(title_prefixes)
    quest_name = f"{prefix}「{' → '.join(s['poi_name'] for s in steps)}」"

    task = {
        "id": str(uuid.uuid4())[:8],
        "type": "travel",
        "name": quest_name,
        "description": f"一段 {num_stops} 站的短途旅行，总计约 {total_time} 分钟",
        "condition": f"完成全部 {num_stops} 个站点的动作",
        "exp": bonus_exp,
        "gold": bonus_gold,
        "estimated_minutes": total_time,
        "walk_distance_m": int(total_dist),
        "steps": steps,
        "total_steps": num_stops,
        "completed_steps": 0,
        "expires_at": _iso(_now() + timedelta(hours=expires_hours)),
        "status": "active",
        "created_at": _iso(_now()),
        "completed_at": None,
        "place": selected[0]["name"] if selected else "未知起点",
    }

    # If there are coords, add bonus for idle window generation
    if is_in_idle_window():
        task["gold"] = int(task["gold"] * 1.2)
        task["exp"] = int(task["exp"] * 1.2)

    # Save
    tasks = load_tasks()
    # Expire any existing travel quests
    for t in tasks:
        if t.get("type") == "travel" and t.get("status") == "active":
            t["status"] = "expired"
    tasks.append(task)
    save_tasks(tasks)

    return task


def travel_steps(task_id: str) -> list[dict[str, Any]] | None:
    """Get detailed steps for a travel quest."""
    task = None
    for t in load_tasks():
        if t.get("id") == task_id:
            task = t
            break
    if not task:
        print("✗ 任务不存在。")
        return None
    if task.get("type") != "travel":
        print("✗ 该任务不是旅行任务。")
        return None
    return task.get("steps", [])


def complete_travel_step(task_id: str, step_index: int) -> dict[str, Any] | None:
    """Complete one step of a travel quest with immediate reward."""
    tasks = load_tasks()
    task = None
    for t in tasks:
        if t.get("id") == task_id:
            task = t
            break

    if not task or task.get("type") != "travel":
        print("✗ 旅行任务不存在。")
        return None
    if task.get("status") != "active":
        print("✗ 任务已过期或已完成。")
        return None

    steps: list[dict[str, Any]] = task.get("steps", [])
    if step_index < 0 or step_index >= len(steps):
        print(f"✗ 无效步骤索引。有效范围: 0-{len(steps) - 1}")
        return None
    if steps[step_index].get("completed"):
        print("✗ 该步骤已完成。")
        return None

    steps[step_index]["completed"] = True
    task["completed_steps"] = task.get("completed_steps", 0) + 1
    step_reward = {
        "exp": steps[step_index].get("reward_exp", 10),
        "gold": steps[step_index].get("reward_gold", 5),
    }

    # Award immediate reward
    state = get_user_state()
    state["exp"] = state.get("exp", 0) + step_reward["exp"]
    state["gold"] = state.get("gold", 0) + step_reward["gold"]

    # Check if all steps are done
    all_done = all(s.get("completed") for s in steps)
    if all_done:
        task["status"] = "completed"
        task["completed_at"] = _iso(_now())
        # Award bonus
        state["exp"] = state.get("exp", 0) + task.get("exp", 0)
        state["gold"] = state.get("gold", 0) + task.get("gold", 0)
        step_reward["bonus"] = True
        step_reward["bonus_exp"] = task.get("exp", 0)
        step_reward["bonus_gold"] = task.get("gold", 0)

        # Auto-add new places to places.json
        places = load_json("places.json")
        place_names = {p["name"] for p in places}
        new_count = 0
        for s in steps:
            pname = s["poi_name"]
            if pname not in place_names:
                places.append({
                    "name": pname,
                    "type": "discovered",
                    "distance_m": s.get("segment_distance_m", 500),
                    "known_npcs": [],
                    "memo": f"旅行探索发现 - {_now().strftime('%Y-%m-%d')}",
                })
                place_names.add(pname)
                new_count += 1
        if new_count:
            save_json("places.json", places)
            print(f"✓ {new_count} 个新地点已添加到地点簿！")

    save_user_state(state)
    save_tasks(tasks)
    return step_reward


def cancel_travel(task_id: str) -> bool:
    """Cancel a travel quest (mark as expired)."""
    tasks = load_tasks()
    for t in tasks:
        if t.get("id") == task_id and t.get("type") == "travel" and t.get("status") == "active":
            t["status"] = "expired"
            save_tasks(tasks)
            return True
    return False
