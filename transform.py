#!/usr/bin/env python3
import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime

# File paths
OUTPUT_FILE = "crichd-auto-fetch/auto_fetch_crichd_api.json"

# URLs
FANCODE_URL = "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/fancode.json"
SONYLIV_URL = "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/sonyliv.json"
CRICHD_SELECTED_URL = "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/crichd_selected.json"


# ---------------------- HELPERS ----------------------

def fetch_json_url(url):
    """Fetch JSON from URL with headers."""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def build_match_title(m):
    """
    Build a clean title like: 'IND vs SA - Asia Cup 2025'
    Works for FanCode, SonyLiv, Crichd.
    """
    team1 = (m.get("team_1") or m.get("team1") or m.get("homeTeam") or "").strip()
    team2 = (m.get("team_2") or m.get("team2") or m.get("awayTeam") or "").strip()
    title = (m.get("title") or m.get("match_name") or "").strip()

    # If title missing, build from team names
    if not title:
        if team1 and team2:
            title = f"{team1} vs {team2}"
        else:
            title = "Unknown Match"

    # Tournament / competition / league info
    competition = (
        m.get("competition") or
        m.get("tournament") or
        m.get("league") or
        m.get("competition_name") or
        m.get("event_category") or
        ""
    ).strip()

    if competition and competition.lower() not in title.lower():
        title = f"{title} - {competition}"

    return title


# ---------------------- NORMALIZE ----------------------

def normalize_match(m, idx, channel_number=600):
    """Normalize FanCode match object into common schema."""
    title = build_match_title(m)
    channel_num = channel_number + idx

    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "FanCode",
        "channelName": title.strip(),
        "subText": "Stream provided by public source",
        "startTime": m.get("startTime") or datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "drm_licence": "",
        "channelUrl": m.get("channelUrl", ""),
        "imageUrl": m.get("src", "")
    }


def normalize_sonyliv(m, idx, channel_number=700):
    """Normalize SonyLiv match object."""
    title = build_match_title(m)
    channel_num = channel_number + idx

    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "SonyLiv",
        "channelName": title.strip(),
        "subText": "Stream provided by public source",
        "startTime": m.get("startTime") or datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "drm_licence": "",
        "channelUrl": m.get("channelUrl", ""),
        "imageUrl": m.get("src", "")
    }


def normalize_crichd_selected(m, idx, channel_number=800):
    """Normalize Crichd selected items (manual list)."""
    title = build_match_title(m)
    channel_num = channel_number + idx

    return {
        "channelNumber": channel_num,
        "linkType": "app",
        "platform": "CricHD",
        "channelName": title.strip(),
        "subText": "Stream provided by public source",
        "startTime": m.get("startTime") or datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "drm_licence": "",
        "channelUrl": m.get("channelUrl", ""),
        "imageUrl": m.get("src", "")
    }


# ---------------------- LOADERS ----------------------

def load_fancode_matches():
    data = fetch_json_url(FANCODE_URL)
    if isinstance(data, list):
        return [normalize_match(m, i) for i, m in enumerate(data)]
    return []


def load_sonyliv_matches():
    data = fetch_json_url(SONYLIV_URL)
    if isinstance(data, list):
        return [normalize_sonyliv(m, i) for i, m in enumerate(data)]
    return []


def load_crichd_selected_items():
    data = fetch_json_url(CRICHD_SELECTED_URL)
    if isinstance(data, list):
        return [normalize_crichd_selected(m, i) for i, m in enumerate(data)]
    return []


# ---------------------- MAIN ----------------------

def main():
    all_matches = []
    all_matches.extend(load_fancode_matches())
    all_matches.extend(load_sonyliv_matches())
    all_matches.extend(load_crichd_selected_items())

    print(f"✅ Total matches collected: {len(all_matches)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_matches, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
