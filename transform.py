#!/usr/bin/env python3
import json
import os
import sys
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime  # For time formatting

# File paths
OUTPUT_FILE = "live_stream/auto_update_all_streams.json"
MANUAL_FILE = "live_stream/all_streams.json"
LOCAL_FILES = ["fancode1.json", "fancode2.json", "fancode3.json"]

CRICHD_SELECTED_URL = "https://raw.githubusercontent.com/jitupatel2506/crichd-auto-fetch/refs/heads/main/crichd-auto-fetch/auto_crichd_selected_api.json"

FANCODE_URLS = [
    "https://allinonereborn.online/fc/fancode.json",
    "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json",
    "https://raw.githubusercontent.com/jitendra-unatti/fancode/refs/heads/main/data/fancode.json",
]

SONYLIV_URL = "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json"


def read_local_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fetch_json_url(url, timeout=10):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="ignore"))
    except:
        return None


def load_json_sources():
    matches = []
    found_local = False

    for lf in LOCAL_FILES:
        if os.path.exists(lf):
            data = read_local_json(lf)
            if isinstance(data, dict):
                matches += data.get("matches", []) or []
                found_local = True

    if found_local:
        return matches

    for url in FANCODE_URLS:
        data = fetch_json_url(url)
        if not data:
            continue

        if isinstance(data, dict):
            if "matches" in data:
                matches += data["matches"]
            else:
                matches.append(data)

        elif isinstance(data, list):
            matches += data

    return matches


def load_sonyliv_matches():
    matches = []
    data = fetch_json_url(SONYLIV_URL)
    if isinstance(data, dict):
        raw_matches = data.get("matches", [])
        for m in raw_matches:
            category = (m.get("event_category") or "").lower()
            is_live = m.get("isLive", False)

            if not is_live:
                continue
            if category not in ["cricket", "football", "hockey"]:
                continue

            title = m.get("event_name") or "Unknown Match"
            stream_url = m.get("video_url")
            thumbnail = m.get("src") or "https://i.ibb.co/ygQ6gT3/sonyliv.png"

            raw_content_id = str(m.get("contentId", ""))
            digits = re.search(r"\d+", raw_content_id)
            channel_number = int(digits.group()) if digits else 900

            item = {
                "channelNumber": channel_number,
                "linkType": "app",
                "platform": "SonyLiv",
                "channelName": title.strip(),
                "subText": "Live Streaming Now",
                "startTime": "",
                "drm_licence": "",
                "ownerInfo": "Stream provided by public source",
                "thumbnail": thumbnail,
                "channelUrl": stream_url,
                "match_id": raw_content_id or str(channel_number),
            }

            matches.append(item)

    return matches


def detect_language_from_url(url: str) -> str:
    languages = {
        "hindi": "Hindi",
        "malayalam": "Malayalam",
        "telugu": "Telugu",
        "tamil": "Tamil",
        "kannada": "Kannada",
        "bangla": "Bangla",
        "marathi": "Marathi",
        "gujarati": "Gujarati",
        "punjabi": "Punjabi",
        "odia": "Odia",
        "english": "English",
    }
    if not url:
        return ""
    url_lower = url.lower()
    for key, lang in languages.items():
        if key in url_lower:
            return lang
    return ""


def pick_stream_url(m):
    candidates = [
        m.get("adfree_url"),
        m.get("adfree_stream"),
        m.get("dai_url"),
        m.get("daiUrl"),
        m.get("stream_url"),
        m.get("video_url"),
    ]

    if isinstance(m.get("STREAMING_CDN"), dict):
        cdn = m["STREAMING_CDN"]
        for key in ["Primary_Playback_URL", "fancode_cdn", "dai_google_cdn"]:
            if cdn.get(key):
                candidates.append(cdn[key])

    for c in candidates:
        if not c:
            continue
        c_str = str(c).strip()
        if c_str and "http" in c_str:
            return c_str
    return ""


def clean_title(title: str) -> str:
    if not title:
        return ""
    return title.strip().rstrip("-").strip()


def normalize_match(m, idx, channel_number=600):
    title = ((m.get("title") or m.get("match_name") or "")).strip()

    if not title:
        t1 = (m.get("team_1") or m.get("team1") or "").strip()
        t2 = (m.get("team_2") or m.get("team2") or "").strip()
        if t1 and t2:
            title = f"{t1} vs {t2}"

    if not title:
        title = "Unknown Match"

    stream_url = pick_stream_url(m)
    if not stream_url:
        return None

    match_id = m.get("match_id") or m.get("id") or m.get("matchId")

    try:
        channel_num = int(match_id)
    except:
        channel_num = channel_number + idx

    thumbnail = (
        m.get("src")
        or m.get("image")
        or "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/cricket_league_vectors/all_live_streaming_inonly.png"
    )

    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "FanCode",
        "channelName": clean_title(title),
        "subText": "Live tv guide",
        "startTime": "",
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url.strip(),
        "match_id": match_id or str(channel_number + idx),
    }


def normalize_fancode3_match(m, idx, channel_number=700):
    title = (m.get("title", "Unknown Match")).strip()
    start_time = m.get("startTime", "").strip()
    image = m.get("image") or "https://i.ibb.co/ygQ6gT3/default.png"
    stream_url = m.get("adfree_stream", "").strip()
    match_id = str(m.get("match_id") or channel_number + idx)

    if not stream_url:
        return None

    return {
        "channelNumber": channel_number + idx,
        "linkType": "app",
        "platform": "FanCode",
        "channelName": clean_title(title),
        "subText": "Live tv guide",
        "startTime": start_time,
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": image,
        "channelUrl": stream_url,
        "match_id": match_id,
    }


def merge_fancode3_matches(auto_items, fancode3_matches):
    existing = {item["match_id"]: item for item in auto_items}
    for idx, m in enumerate(fancode3_matches, start=1):
        item = normalize_fancode3_match(m, idx)
        if not item:
            continue
        match_id = item["match_id"]
        if match_id in existing:
            existing[match_id].update(item)
        else:
            existing[match_id] = item
    return list(existing.values())


def load_crichd_selected_items():
    data = fetch_json_url(CRICHD_SELECTED_URL)
    return data if isinstance(data, list) else []


def load_manual_items():
    if os.path.exists(MANUAL_FILE):
        try:
            with open(MANUAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []


def main():
    manual_items = load_manual_items()
    crichd_selected_items = load_crichd_selected_items()

    matches_all = load_json_sources()
    sonyliv_matches = load_sonyliv_matches()

    seen = {}
    auto_items = []
    added = 0

    for m in matches_all:
        status = str(m.get("status") or "").lower()
        category = str(m.get("category") or m.get("event_category") or "").lower()

        if "live" not in status:
            continue
        if category not in ["cricket", "kabaddi", "football"]:
            continue

        item = normalize_match(m, added + 1)
        if not item:
            continue

        match_id = item.get("match_id")

        if match_id:
            if match_id not in seen:
                seen[match_id] = True
                auto_items.append(item)
                added += 1
        else:
            auto_items.append(item)
            added += 1

    auto_items.extend(sonyliv_matches)

    fancode3_raw = fetch_json_url(FANCODE_URLS[2])
    if isinstance(fancode3_raw, list):
        auto_items = merge_fancode3_matches(auto_items, fancode3_raw)

    priority_items = [m for m in auto_items if "Football" in m["channelName"] or "Kabaddi" in m["channelName"]]
    other_items = [m for m in auto_items if m not in priority_items]
    auto_items = priority_items + other_items

    final_output = manual_items + crichd_selected_items + auto_items
 #   final_output = list(reversed(final_output))

    # 🔥 Convert ALL channelName → Server 1, Server 2, Server 3...
    for i, item in enumerate(final_output, start=1):
        item["channelName"] = f"Server {i}"

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        print("Updated:", OUTPUT_FILE)
    except Exception as e:
        print("Write error:", e)
        sys.exit(2)


if __name__ == "__main__":
    main()

