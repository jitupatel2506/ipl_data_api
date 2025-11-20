#!/usr/bin/env python3
import json
import os
import sys
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime  # ✅ Added for time formatting

# File paths
OUTPUT_FILE = "live_stream/auto_worldwide_football.json"
MANUAL_FILE = "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/live_stream/football_streaming.json"
# Local filenames (CI will download these via curl)
LOCAL_FILES = ["football1.json", "football2.json"]
CRICHD_SELECTED_URL = "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/live_stream/football_streaming.json"
# Remote fallback URLs (used only if local files missing)
FANCODE_URLS = [
    "https://allinonereborn.fun/fc/fancode.json",
    "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json",
    "https://raw.githubusercontent.com/jitendra-unatti/fancode/refs/heads/main/data/fancode.json",
]

# ✅ SonyLiv JSON URL
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

            # ✅ Only football & live matches
            if not is_live:
                continue
            if category != "football":
                continue

            title = m.get("event_name") or "Unknown Match"
            stream_url = m.get('video_url')
            thumbnail = m.get("src") or "https://i.ibb.co/ygQ6gT3/sonyliv.png"

            # ✅ FIX: safely convert contentId to int or fallback to 900
            raw_content_id = str(m.get("contentId", ""))
            if raw_content_id.isdigit():
                channel_number = int(raw_content_id)
            else:
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
                "category": category,
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
        m.get("video_url"),
    ]
    for c in candidates:
        if not c:
            continue
        c_str = str(c).strip()
        if c_str:
            return c_str
    return ""


def normalize_start_time(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    try:
        dt = datetime.strptime(raw, "%I:%M:%S %p %d-%m-%Y")
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return raw  # fallback if format not matched


def shorten_name(title: str, tournament: str) -> str:
    if not title:
        return tournament or "Unknown"

    teams = re.split(r"\s+vs\s+", title, flags=re.IGNORECASE)
    short_teams = []

    for team in teams:
        clean_team = re.sub(r"[^A-Za-z0-9\s]", "", team)
        words = clean_team.split()

        if len(words) == 1:
            short_teams.append(words[0][:3].upper())
        elif len(words) == 2:
            w1, w2 = words
            if len(w2) >= 5:
                short_teams.append(w1[0].upper() + w2[0].upper())
            else:
                short_teams.append(w1[0].upper() + w2[:2].upper())
        else:
            short_teams.append("".join(w[0].upper() for w in words[:3]))

    short_title = " vs ".join(short_teams)

    clean_tournament = re.sub(r"[^A-Za-z0-9\s]", "", tournament or "")
    year_match = re.search(r"\b(20\d{2})\b", clean_tournament)
    year = year_match.group(1) if year_match else ""
    words = clean_tournament.replace(",", "").split()
    initials = "".join(w[0].upper() for w in words if not w.isdigit())[:4]
    short_tournament = f"{initials} {year}".strip()

    return f"{short_title} - {short_tournament}".strip()


def clean_title(title: str) -> str:
    if not title:
        return ""
    title = title.strip()
    if title.endswith("-"):
        title = title[:-1].strip()
    return title


def normalize_match(m, idx, channel_number=600):
    title = ((m.get("title", "")) or (m.get("match_name")) or "").strip()
    tournament = (m.get("tournament") or m.get("competition") or "").strip()

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

    short_title = shorten_name(title, tournament)
    short_title = clean_title(short_title)

    lang = detect_language_from_url(stream_url)
    if lang and lang.lower() != "english":
        short_title = f"{short_title} - {lang}"

    category = (m.get("category") or m.get("event_category") or "").lower()
    if category != "football":
        return None

    match_id = m.get("match_id") or m.get("id") or m.get("matchId")
    if match_id:
        try:
            channel_num = int(match_id)
        except ValueError:
            channel_num = channel_number + idx
    else:
        channel_num = channel_number + idx

    thumbnail = (
        m.get("src")
        or m.get("image")
        or "https://i.ibb.co/ygQ6gT3/default.png"
    )

    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "FanCode",
        "channelName": short_title.strip(),
        "subText": "Live Streaming Now",
        "startTime": "",
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url.strip(),
        "match_id": match_id or str(channel_number + idx),
        "category": category,
    }


def load_crichd_selected_items():
    data = fetch_json_url(CRICHD_SELECTED_URL)
    if isinstance(data, list):
        print(f"ℹ️ Crichd selected items fetched: {len(data)}")
        for item in data:
            item["thumbnail"] = "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/cricket_league_vectors/football_new.png"
        return item
    return []


def load_manual_items():
    if MANUAL_FILE.startswith("http://") or MANUAL_FILE.startswith("https://"):
        data = fetch_json_url(MANUAL_FILE)
        if isinstance(data, list):
            for item in data:
                item["thumbnail"] = "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/cricket_league_vectors/football_new.png"
            print(f"ℹ️ Manual items fetched from remote: {len(data)}")
            return data
        return []

    if os.path.exists(MANUAL_FILE):
        try:
            with open(MANUAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        item["thumbnail"] = "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/cricket_league_vectors/football_new.png"
                    print(f"ℹ️ Manual items loaded from local: {len(data)}")
                    return data
        except Exception as e:
            print(f"⚠️ Error loading manual file {MANUAL_FILE}: {e}")
    return []


def main():
    manual_items = load_manual_items()
    print("ℹ️ Manual items loaded:", len(manual_items))
    crichd_selected_items = load_crichd_selected_items()

    matches_all = load_json_sources()
    print(f"ℹ️ Total matches fetched from FanCode: {len(matches_all)}")

    sonyliv_matches = load_sonyliv_matches()

    seen = {}
    auto_items = []
    added = 0

    for m in matches_all:
        status = str(m.get("status") or "").strip().lower()
        category = str(m.get("category") or m.get("event_category") or "").strip().lower()

        if "live" not in status:
            continue
        if category != "football":
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

    auto_items.extend(sonyliv_matches)

    auto_items = sorted(auto_items, key=lambda x: 0 if "football" in x.get("category", "").lower() else 1)

    print("ℹ️ Auto items prepared:", len(auto_items))

    final_output = manual_items + auto_items
    final_output = list(reversed(final_output))

      for item in final_output:
        url = item.get("channelUrl", "")
        if url.startswith("https://in-mc-fdlive.fancode.com/"):
            item["channelUrl"] = url.replace(
                "https://in-mc-flive.fancode.com/",
                "https://in-mc-pdlive.fancode.com/"  
            )
            #"http://147.93.107.176:8080/fancode/"
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
