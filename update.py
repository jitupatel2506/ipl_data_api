#!/usr/bin/env python3
import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime  # ✅ Added for time formatting

# File paths
OUTPUT_FILE = "live_stream/auto_update_all_streams.json"
MANUAL_FILE = "live_stream/all_streams.json"

# Local filenames (CI will download these via curl)
LOCAL_FILES = ["fancode1.json", "fancode2.json", "fancode3.json"]

# Remote fallback URLs (used only if local files missing)
FANCODE_URLS = [
    "https://allinonereborn.online/fc/fancode.json",
    "https://allinonereborn.fun/fc/fancode.json",
    "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json",
    "https://raw.githubusercontent.com/Jitendraunatti/fancode/refs/heads/main/data/fancode.json",
]

# ✅ New SonyLiv JSON URL
SONYLIV_URL = "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json"


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
    except HTTPError as e:
        print(f"⚠️ HTTP error fetching {url}: {e.code} {e.reason}")
    except URLError as e:
        print(f"⚠️ URL error fetching {url}: {e.reason}")
    except Exception as e:
        print(f"⚠️ Error fetching/parsing {url}: {e}")
    return None


def load_json_sources():
    """Load matches from either local files (preferred) or remote URLs as fallback"""
    matches = []
    found_local = False

    for lf in LOCAL_FILES:
        if os.path.exists(lf):
            data = read_local_json(lf)
            if isinstance(data, dict):
                matches += data.get("matches", []) or []
                found_local = True
    if found_local:
        print("ℹ️ Loaded matches from local files:", [f for f in LOCAL_FILES if os.path.exists(f)])
        return matches

    print("ℹ️ No local files found; fetching from FanCode remote URLs.")
    for url in FANCODE_URLS:
        data = fetch_json_url(url)
        if isinstance(data, dict):
            matches += data.get("matches", []) or []

    return matches


def load_sonyliv_matches():
    """Fetch and normalize matches from SonyLiv JSON"""
    matches = []
    data = fetch_json_url(SONYLIV_URL)
    if isinstance(data, dict):
        raw_matches = data.get("matches", [])
        for m in raw_matches:
            category = (m.get("event_category") or "").lower()
            is_live = m.get("isLive", False)

            # ✅ Filter only live cricket/football/hockey
            if not is_live:
                continue
            if category not in ["cricket", "football", "hockey"]:
                continue

            title = m.get("event_name") or "Unknown Match"
            stream_url = m.get('dai_url')
            thumbnail = m.get("src") or "https://i.ibb.co/ygQ6gT3/sonyliv.png"

            item = {
                "channelNumber": int(m.get("contentId", 0)) or 900,
                "linkType": "app",
                "platform": "SonyLiv",
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

    print(f"ℹ️ SonyLiv matches fetched: {len(matches)}")
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
        "english": "English",  # skip appending
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
        m.get("India"),
        m.get("adfree_url"),
        m.get("dai_url"),
        m.get("daiUrl"),
        m.get("stream_url"),
        m.get("src"),
        m.get("srcUrl"),
        m.get("url"),
    ]
    for c in candidates:
        if not c:
            continue
        c_str = str(c).strip()
        if c_str:
            return c_str
    return ""


# ✅ Start time normalization function
def normalize_start_time(raw: str) -> str:
    """
    Input:  "07:30:00 PM 27-08-2025"
    Output: "2025-08-27 07:30 PM"
    """
    if not raw:
        return ""
    raw = raw.strip()
    try:
        dt = datetime.strptime(raw, "%I:%M:%S %p %d-%m-%Y")
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return raw  # fallback if format not matched


def normalize_match(m, idx, channel_number=600):
    title = (m.get("title") or m.get("match_name") or "").strip()
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

    # Proxy wrap if fancode
    if "fancode.com" in stream_url and not stream_url.startswith("https://allinonereborn.fun/fc/play.php?url="):
        stream_url = "https://allinonereborn.fun/fcw/stream_proxy.php?url=" + stream_url

    # Detect language
    lang = detect_language_from_url(stream_url)
    if lang and lang.lower() != "english":
        title = f"{title} - {lang}"

    # Kabaddi handling
    category = (m.get("category") or m.get("event_category") or "").lower()
    if "kabaddi" in category and "kabaddi" not in title.lower():
        title = f"{title} - Kabaddi"

    # Channel number
    match_id = m.get("match_id") or m.get("id") or m.get("matchId")
    if match_id:
        try:
            channel_num = int(match_id)
        except ValueError:
            channel_num = channel_number + idx
    else:
        channel_num = channel_number + idx

    # ✅ Thumbnail priority
    thumbnail = (
        m.get("src")
        or m.get("image")
        or "https://gitlab.com/appzombies/ipl_data_api/-/raw/main/cricket_league_vectors/all_live_streaming.png"
    )
    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "FanCode",
        "channelName": title.strip(),
        "subText": "Live Streaming Now",
        "startTime":"",
        #"startTime": normalize_start_time(m.get("startTime", "") or m.get("start_time", "")),  # ✅ Updated
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url.strip(),
        "match_id": match_id or str(channel_number + idx),  # keep match_id for dedupe
    }


def load_manual_items():
    if os.path.exists(MANUAL_FILE):
        try:
            with open(MANUAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"⚠️ Error loading manual file {MANUAL_FILE}: {e}")
    return []


def main():
    manual_items = load_manual_items()
    print("ℹ️ Manual items loaded:", len(manual_items))

    matches_all = load_json_sources()
    print(f"ℹ️ Total matches fetched from FanCode: {len(matches_all)}")

    sonyliv_matches = load_sonyliv_matches()

    seen = {}  # match_id -> set(languages)
    auto_items = []
    added = 0

    # FanCode normalize
    for m in matches_all:
        status = str(m.get("status") or "").strip().lower()
        category = str(m.get("category") or m.get("event_category") or "").strip().lower()

        if "live" not in status:
            continue
        if category not in ["cricket", "kabaddi", "football"]:
            continue

        item = normalize_match(m, added + 1)
        if not item:
            continue

        match_id = item.get("match_id")
        lang = detect_language_from_url(item["channelUrl"]).lower() or "default"

        if match_id:
            if match_id not in seen:
                seen[match_id] = {lang}
                auto_items.append(item)
                added += 1
            else:
                if lang not in seen[match_id]:
                    seen[match_id].add(lang)
                    auto_items.append(item)
                    added += 1
        else:
            auto_items.append(item)
            added += 1

    # SonyLiv add directly (already filtered live matches)
    auto_items.extend(sonyliv_matches)

    print("ℹ️ Auto items prepared:", len(auto_items))

    final_output = manual_items + auto_items
    final_output = list(reversed(final_output))

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        print("✅ JSON updated:", OUTPUT_FILE)
        print("Manual:", len(manual_items), "| Auto:", len(auto_items), "| Total:", len(final_output))
    except Exception as e:
        print("❌ Failed to write output file:", e)
        sys.exit(2)


if __name__ == "__main__":
    main()



