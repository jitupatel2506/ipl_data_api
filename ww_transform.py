#!/usr/bin/env python3
import json
import os
import sys
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

OUTPUT_FILE = "live_stream/auto_worldwide_update_all_streams.json"
MANUAL_FILE = "live_stream/all_streams_worldwide.json"
LOCAL_FILES = ["fancode1.json", "fancode2.json", "fancode3.json"]
CRICHD_SELECTED_URL = (
    "https://raw.githubusercontent.com/jitupatel2506/crichd-auto-fetch/refs/heads/main/crichd-auto-fetch/auto_crichd_selected_api.json"
)
FANCODE_URLS = [
    "https://allinonereborn.online/fc/fancode.json",
    "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json",
    "https://raw.githubusercontent.com/jitendra-unatti/fancode/main/data/fancode.json",
]
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
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"⚠️ Error fetching {url}: {e}")
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
        print("ℹ️ Loaded matches from local files:", [f for f in LOCAL_FILES if os.path.exists(f)])
        return matches
    print("ℹ️ No local files found; fetching from FanCode remote URLs.")
    for url in FANCODE_URLS:
        data = fetch_json_url(url)
        if isinstance(data, dict):
            matches += data.get("matches", []) or []
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
            if category not in ["cricket", "football", "hockey", "kabaddi"]:
                continue
            title = m.get("event_name") or "Unknown Match"
            stream_url = m.get("video_url")
            thumbnail = m.get("src") or "https://i.ibb.co/ygQ6gT3/sonyliv.png"

            raw_content_id = str(m.get("contentId", ""))
            if raw_content_id.isdigit():
                channel_number = int(raw_content_id)
            else:
                digits = re.search(r"\d+", raw_content_id)
                channel_number = int(digits.group()) if digits else 900

            matches.append(
                {
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
            )
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
        "english": "English",
    }
    if not url:
        return ""
    lower = url.lower()
    for key, lang in languages.items():
        if key in lower:
            return lang
    return ""


def pick_stream_url(m):
    for key in ["India", "adfree_url", "dai_url", "daiUrl", "stream_url", "video_url"]:
        c = m.get(key)
        if c and str(c).strip():
            return str(c).strip()
    return ""


def shorten_name(title: str, tournament: str) -> str:
    if not title:
        return tournament or "Unknown"
    teams = re.split(r"\s+vs\s+", title, flags=re.IGNORECASE)
    short_teams = []
    for team in teams:
        clean = re.sub(r"[^A-Za-z0-9\s]", "", team)
        words = clean.split()
        if len(words) == 1:
            short_teams.append(words[0][:3].upper())
        elif len(words) == 2:
            w1, w2 = words
            short_teams.append(w1[0].upper() + w2[0].upper())
        else:
            short_teams.append("".join(w[0].upper() for w in words[:3]))
    short_title = " vs ".join(short_teams)
    clean_tournament = re.sub(r"[^A-Za-z0-9\s]", "", tournament or "")
    year = re.search(r"\b(20\d{2})\b", clean_tournament)
    year = year.group(1) if year else ""
    initials = "".join(w[0].upper() for w in clean_tournament.split() if not w.isdigit())[:4]
    return f"{short_title} - {initials} {year}".strip()


def normalize_match(m, idx, channel_number=600):
    title = ((m.get("title") or m.get("match_name")) or "").strip()
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
    lang = detect_language_from_url(stream_url)
    if lang and lang.lower() != "english":
        short_title = f"{short_title} - {lang}"

    category = (m.get("category") or m.get("event_category") or "").lower()
    if "kabaddi" in category and "kabaddi" not in short_title.lower():
        short_title += " - Kabaddi"
    if "football" in category and "football" not in short_title.lower():
        short_title += " - Football"

    match_id = str(m.get("match_id") or m.get("id") or m.get("matchId") or "")
    try:
        channel_num = int(match_id) if match_id.isdigit() else channel_number + idx
    except ValueError:
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
        "channelName": short_title.strip(),
        "subText": "Live Streaming Now",
        "startTime": "",
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url,
        "match_id": match_id or str(channel_num),
        "category": category,
    }


def load_crichd_selected_items():
    data = fetch_json_url(CRICHD_SELECTED_URL)
    if isinstance(data, list):
        print(f"ℹ️ Crichd selected items fetched: {len(data)}")
        for item in data:
            item["thumbnail"] = (
                "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/"
                "cricket_league_vectors/all_live_streaming_worldwide.png"
            )
        return data
    return []


def load_manual_items():
    if os.path.exists(MANUAL_FILE):
        try:
            with open(MANUAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        item["thumbnail"] = (
                            "https://gitlab.com/ranginfotech89/ipl_data_api/-/raw/main/stream_categories/"
                            "cricket_league_vectors/all_live_streaming_worldwide.png"
                        )
                    return data
        except Exception as e:
            print(f"⚠️ Error loading manual file {MANUAL_FILE}: {e}")
    return []


def main():
    manual_items = load_manual_items()
    print("ℹ️ Manual items loaded:", len(manual_items))
    crichd_items = load_crichd_selected_items()
    matches_all = load_json_sources()
    print(f"ℹ️ Total matches fetched from FanCode: {len(matches_all)}")
    sonyliv_items = load_sonyliv_matches()

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
        mid = item["match_id"]
        lang = detect_language_from_url(item["channelUrl"]).lower() or "default"
        if mid not in seen:
            seen[mid] = {lang}
            auto_items.append(item)
            added += 1
        elif lang not in seen[mid]:
            seen[mid].add(lang)
            auto_items.append(item)
            added += 1

    auto_items.extend(sonyliv_items)
    auto_items.sort(key=lambda x: 0 if x.get("category", "").lower() in ["football", "kabaddi"] else 1)
    print("ℹ️ Auto items prepared:", len(auto_items))

    final_output = list(reversed(manual_items + crichd_items + auto_items))

    for item in final_output:
        url = item.get("channelUrl", "")
        if url.startswith("https://in-mc-fdlive.fancode.com/"):
            item["channelUrl"] = url.replace(
                "https://in-mc-fdlive.fancode.com/",
                "http://147.93.107.176:8080/fancode/",
            )

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    print("✅ JSON updated:", OUTPUT_FILE)
    print("Manual:", len(manual_items), "| Auto:", len(auto_items), "| Total:", len(final_output))


if __name__ == "__main__":
    main()
