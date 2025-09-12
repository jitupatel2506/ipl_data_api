#!/usr/bin/env python3
import json
import os
import sys
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# File paths
OUTPUT_FILE = "live_stream/auto_update_all_streams.json"
MANUAL_FILE = "live_stream/all_streams.json"
LOCAL_FILES = ["fancode1.json", "fancode2.json", "fancode3.json"]

# Correct FanCode URL
FANCODE_URLS = [
    "https://allinonereborn.fun/fc/fancode.json",
    "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json",
    "https://raw.githubusercontent.com/jitendra-unatti/fancode/main/data/fancode.json",
]

# CrichD selected items
CRICHD_SELECTED_URL = "https://raw.githubusercontent.com/jitupatel2506/crichd-auto-fetch/main/crichd-auto-fetch/auto_crichd_selected_api.json"

# SonyLiv JSON
SONYLIV_URL = "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json"

VALID_CATEGORIES = ["cricket", "kabaddi", "football", "motogp"]  # Add more if needed

def read_local_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read local {path}: {e}")
        return None

def fetch_json_url(url, timeout=10):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
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
        print("ℹ️ Loaded matches from local files")
        return matches

    # Fetch from remote FanCode URLs
    for url in FANCODE_URLS:
        data = fetch_json_url(url)
        if not data:
            continue
        if isinstance(data, dict):
            matches += data.get("matches", []) or []
        elif isinstance(data, list):
            matches += data
    return matches

def load_sonyliv_matches():
    matches = []
    data = fetch_json_url(SONYLIV_URL)
    if isinstance(data, dict):
        for m in data.get("matches", []):
            category = (m.get("event_category") or "").lower()
            if not m.get("isLive", False):
                continue
            title = m.get("event_name") or "Unknown Match"
            stream_url = m.get("video_url")
            thumbnail = m.get("src") or "https://i.ibb.co/ygQ6gT3/sonyliv.png"
            item = {
                "channelNumber": int(m.get("contentId", 0)) or 900,
                "platform": "SonyLiv",
                "linkType": "app",
                "channelName": title.strip(),
                "subText": "Live Streaming Now",
                "startTime": "",
                "drm_licence": "",
                "ownerInfo": "Stream provided by public source",
                "thumbnail": thumbnail,
                "channelUrl": stream_url,
                "match_id": str(m.get("contentId")),
            }
            matches.append(item)
    return matches

def detect_language_from_url(url: str) -> str:
    if not url:
        return ""
    url_lower = url.lower()
    languages = ["hindi","malayalam","telugu","tamil","kannada","bangla","marathi","gujarati","punjabi","odia"]
    for lang in languages:
        if lang in url_lower:
            return lang.capitalize()
    return ""

def pick_stream_url(m):
    # Prioritize streaming URLs
    candidates = [
        m.get("adfree_url"),
        m.get("adfree_stream"),
        m.get("dai_url"),
        m.get("daiUrl"),
        m.get("stream_url"),
        m.get("video_url")
    ]
    # Nested STREAMING_CDN
    if isinstance(m.get("STREAMING_CDN"), dict):
        for key in ["Primary_Playback_URL","fancode_cdn","dai_google_cdn"]:
            if m["STREAMING_CDN"].get(key):
                candidates.append(m["STREAMING_CDN"][key])
    for c in candidates:
        if c and isinstance(c, str) and c.strip().startswith("http"):
            return c.strip()
    return ""

def normalize_match(m, idx, channel_number=600):
    title = m.get("title") or m.get("match_name") or "Unknown Match"
    tournament = m.get("tournament") or m.get("competition") or ""
    stream_url = pick_stream_url(m)
    if not stream_url:
        return None
    category = (m.get("category") or m.get("event_category") or "").lower()
    short_title = f"{title.strip()}"
    lang = detect_language_from_url(stream_url)
    if lang:
        short_title += f" - {lang}"
    if "kabaddi" in category:
        short_title += " - Kabaddi"
    if "football" in category:
        short_title += " - Football"
    thumbnail = m.get("src") or m.get("image") or "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/cricket_league_vectors/all_live_streaming_inonly.png"
    match_id = str(m.get("match_id") or m.get("id") or channel_number + idx)
    try:
        channel_num = int(match_id)
    except:
        channel_num = channel_number + idx
    return {
        "channelNumber": channel_num,
        "platform": "FanCode",
        "linkType": "app",
        "channelName": short_title.strip(),
        "subText": "Live Streaming Now",
        "startTime": "",
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url,
        "match_id": match_id
    }

def load_crichd_selected_items():
    data = fetch_json_url(CRICHD_SELECTED_URL)
    return data if isinstance(data, list) else []

def load_manual_items():
    if os.path.exists(MANUAL_FILE):
        try:
            with open(MANUAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except:
            pass
    return []

def main():
    manual_items = load_manual_items()
    crichd_items = load_crichd_selected_items()
    fan_matches = load_json_sources()
    sonyliv_matches = load_sonyliv_matches()

    auto_items = []
    seen = {}
    idx = 1
    for m in fan_matches:
        status = str(m.get("status") or "").lower()
        category = (m.get("category") or m.get("event_category") or "").lower()
        if "live" not in status:
            continue
        # Allow all categories in VALID_CATEGORIES
        if category not in VALID_CATEGORIES:
            continue
        item = normalize_match(m, idx)
        if not item:
            continue
        mid = item["match_id"]
        lang = detect_language_from_url(item["channelUrl"]).lower() or "default"
        if mid not in seen:
            seen[mid] = {lang}
            auto_items.append(item)
            idx += 1
        else:
            if lang not in seen[mid]:
                seen[mid].add(lang)
                auto_items.append(item)
                idx += 1

    auto_items.extend(sonyliv_matches)

    final_output = manual_items + crichd_items + auto_items
    final_output = list(reversed(final_output))

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON updated: {OUTPUT_FILE}")
    print("Manual:", len(manual_items), "| Auto:", len(auto_items), "| Total:", len(final_output))

if __name__ == "__main__":
    main()
