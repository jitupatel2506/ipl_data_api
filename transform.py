#!/usr/bin/env python3
import json
import os
import sys
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime  # ✅ Added for time formatting

# File paths
OUTPUT_FILE = "live_stream/auto_update_all_streams.json"
MANUAL_FILE = "live_stream/all_streams.json"

# Local filenames (CI will download these via curl)
LOCAL_FILES = ["fancode1.json", "fancode2.json", "fancode3.json"]

# Remote fallback URLs (used only if local files missing)
REMOTE_FILES = {
    "fancode1.json": "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/fancode1.json",
    "fancode2.json": "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/fancode2.json",
    "fancode3.json": "https://raw.githubusercontent.com/appzombies/AllZombies/refs/heads/main/fancode3.json",
}

# ------------------------------
# Helper functions
# ------------------------------
def shorten_name(m: dict) -> str:
    """
    Matches me se team1, team2 aur tournament use karke short name banata hai.
    Agar team1/2 na ho to title split karega.
    """
    team1 = (m.get("team1") or m.get("team_1") or "").strip()
    team2 = (m.get("team2") or m.get("team_2") or "").strip()
    title = (m.get("title") or m.get("match_name") or "").strip()
    tournament = (m.get("tournament") or m.get("competition_name") or "").strip()

    # Agar team1 aur team2 diye hue hain
    teams = []
    if team1 and team2:
        teams = [team1, team2]
    elif title:  # fallback on title
        teams = re.split(r"\s+vs\s+", title, flags=re.IGNORECASE)

    short_teams = []
    for team in teams:
        team = team.strip()
        if not team:
            continue
        words = team.split()
        if len(words) == 1:
            short_teams.append(words[0][:3].upper())
        else:
            initials = "".join(w[0].upper() for w in words if w)
            short_teams.append(initials[:3])

    short_title = " vs ".join(short_teams) if short_teams else (title or "UNK vs UNK")

    # --- Tournament Shorten ---
    year_match = re.search(r"\b(20\d{2})\b", tournament)
    year = year_match.group(1) if year_match else ""

    words = tournament.replace(",", "").split()
    initials = "".join(w[0].upper() for w in words if not w.isdigit())
    short_tournament = f"{initials} {year}".strip()

    return f"{short_title} - {short_tournament}" if short_tournament else short_title


def detect_language_from_url(url: str) -> str:
    """Detect language hint from URL"""
    url = url.lower()
    if "hindi" in url:
        return "Hindi"
    if "tamil" in url:
        return "Tamil"
    if "telugu" in url:
        return "Telugu"
    if "bengali" in url:
        return "Bengali"
    if "kannada" in url:
        return "Kannada"
    return "English"


def pick_stream_url(m: dict) -> str:
    """Pick a valid stream URL from dict"""
    for key in ["url", "channelUrl", "link", "stream_url"]:
        if key in m and m[key]:
            return m[key]
    return ""


def normalize_match(m, idx, channel_number=600):
    title = shorten_name(m)

    stream_url = pick_stream_url(m)
    if not stream_url:
        return None

    # Proxy wrap if fancode
    if "fancode.com" in stream_url and not stream_url.startswith("https://allinonereborn.fun/fcw/stream_proxy.php?url="):
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
        "startTime": "",
        "drm_licence": "",
        "ownerInfo": "Stream provided by public source",
        "thumbnail": thumbnail,
        "channelUrl": stream_url.strip(),
        "match_id": match_id or str(channel_number + idx),
    }


def load_json_file(fname: str):
    """Load local file if exists, else remote"""
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8") as f:
            return json.load(f)
    if fname in REMOTE_FILES:
        try:
            req = Request(REMOTE_FILES[fname], headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return []
    return []


def main():
    all_matches = []
    for fname in LOCAL_FILES:
        data = load_json_file(fname)
        if isinstance(data, list):
            all_matches.extend(data)

    output = []
    for idx, m in enumerate(all_matches, start=1):
        norm = normalize_match(m, idx)
        if norm:
            output.append(norm)

    # Add timestamp
    final_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "matches": output,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {OUTPUT_FILE} with {len(output)} matches.")


if __name__ == "__main__":
    main()
