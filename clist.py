import os
import re
import json
import time
import requests
from rapidfuzz import fuzz
from typing import List, Dict

# ===== USER CONFIG =====
CONFIG = {
    "simkl": {
        "client_id": "xxx",
        "client_secret": "xxx",
        "lists": ["watching", "plantowatch"]
    },
    "sonarr": [
        {"url": "http://localhost:8989", "api_key": "xxx"},
        {"url": "http://localhost:8990", "api_key": "xxx"}
    ],
    "radarr": [
        {"url": "http://localhost:7878", "api_key": "xxx"}
    ],
    "fuzzy_threshold": 100,
    "token_file": "simkl_token.json"
}
# =======================

def save_token(token):
    with open(CONFIG["token_file"], "w") as f:
        json.dump(token, f)

def load_token():
    if os.path.exists(CONFIG["token_file"]):
        with open(CONFIG["token_file"], "r") as f:
            return json.load(f)
    return None

def authenticate_simkl():
    print("🔑 Getting Simkl auth PIN...")
    r = requests.post("https://api.simkl.com/oauth/pin", json={"client_id": CONFIG["simkl"]["client_id"]})
    if not r.ok:
        raise Exception("Failed to get PIN")
    data = r.json()
    #print("Simkl response:", data)
    print(f"Go to: {data['verification_url']}")
    print(f"Enter code: {data['user_code']}")
    
    token_url = f"https://api.simkl.com/oauth/pin/{data['user_code']}/{CONFIG['simkl']['client_id']}"
    while True:
        print("Waiting for approval...")
        time.sleep(30)
        poll = requests.get(token_url)

        if poll.status_code == 200:
            token = poll.json()
            save_token(token)
            print("✅ Auth complete!")

            return token
        elif poll.status_code == 400:
            continue
        else:
            raise Exception(f"Auth failed: {poll.text}")

def get_auth_headers():
    token = load_token()
    if not token:
        token = authenticate_simkl()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token['access_token']}",
        "simkl-api-key": CONFIG['simkl']['client_id']
    }

def get_simkl_list() -> List[Dict]:
    all_items = []
    headers = get_auth_headers()
    desired_statuses = set(CONFIG["simkl"]["lists"])
    
    url = f"https://api.simkl.com/sync/all-items?extended=full"
    res = requests.post(url, headers=headers)
    if not res.ok:
        print("❌ Failed to fetch Simkl list")
        return []

    data = res.json()

    # Combine all 3 types: anime, shows, movies
    for category in ["anime", "shows", "movies"]:
        for entry in data.get(category, []):
            if entry.get("status") not in desired_statuses:
                continue
            item_data = entry.get("show") or entry.get("movie")
            if not item_data:
                continue

            ids = item_data.get("ids", {})
            title = item_data.get("title", "Unknown title")
            all_items.append({
                "title": title,
                "ids": ids,
                "type": category
            })

    return all_items

def get_sonarr_titles():
    all_titles = []
    for s in CONFIG["sonarr"]:
        try:
            r = requests.get(f"{s['url'].rstrip('/')}/api/v3/series",
                             headers={"X-Api-Key": s["api_key"]})
            for e in r.json():
                all_titles.append({
                    "title": e["title"],
                    "alternateTitles": e.get("alternateTitles", []),
                    "ids": {"tvdb": str(e.get("tvdbId", "")), "imdb": e.get("imdbId", "")}
                })
        except Exception as e:
            print(f"Sonarr error: {e}")
    return all_titles

def get_radarr_titles():
    all_titles = []
    for r in CONFIG["radarr"]:
        try:
            res = requests.get(f"{r['url'].rstrip('/')}/api/v3/movie",
                               headers={"X-Api-Key": r["api_key"]})
            for e in res.json():
                all_titles.append({
                    "title": e["title"],
                    "alternateTitles": e.get("alternateTitles", []),
                    "ids": {"tmdb": str(e.get("tmdbId", "")), "imdb": e.get("imdbId", "")}
                })
        except Exception as e:
            print(f"Radarr error: {e}")
    return all_titles

def match_by_ids(simkl, others):
    for other in others:
        for k in simkl["ids"]:
            if k in other["ids"] and simkl["ids"][k] and simkl["ids"][k] == other["ids"][k]:
                return True
    return False

def fuzzy_match(simkl, others, threshold):
    simkl_title = simkl["title"].lower()
    best_score = 0

    for other in others:
        titles_to_check = [other["title"].lower()]

        # Include alternate titles if they exist
        alt_titles = other.get("alternateTitles", [])
        for alt in alt_titles:
            if isinstance(alt, dict) and "title" in alt:
                titles_to_check.append(alt["title"].lower())
            elif isinstance(alt, str):  # fallback if alt is just a string
                titles_to_check.append(alt.lower())

        # Compare Simkl title against all Sonarr/Radarr title variants
        for title in titles_to_check:
            score = fuzz.ratio(simkl_title, title)
            if score >= threshold:
                return [True]
            best_score = max(best_score, score)

    return False, round(best_score, 1)

def color(x):
    num_match = re.search(r"[-+]?[0-9]*\.?[0-9]+", x)
    if not num_match:
        return x  # return original if no number found
    
    colored = f"""{"\033[92m" if float(num_match.group()) >= 80 else "\033[91m"}{x}\033[0m"""
    return colored

def main():
    print("📥 Fetching Simkl list...")
    simkl_items = get_simkl_list()

    print("📡 Fetching Sonarr/Radarr libraries...")
    stack = get_sonarr_titles() + get_radarr_titles()

    print("🔍 Comparing...")
    unmatched = []

    for item in simkl_items:
        if match_by_ids(item, stack):
            continue
        
        fuzzy_match_res = fuzzy_match(item, stack, CONFIG["fuzzy_threshold"])
        if fuzzy_match_res[0]:
            continue

        score = fuzzy_match_res[1]
        item['match_score'] = score
        item['title'] += color(f" ({score:.1f}%)")
        unmatched.append(item)

    print("\n📋 Unmatched Entries:")
    types = ["anime", "shows", "movies"]
    for category in types:
        group = [x for x in unmatched if x["type"] == category]
        if not group:
            continue

        group = sorted(group, key=lambda x: x["match_score"], reverse=True)
        print(f"\n{category.capitalize()}: {len(group)}")
        for entry in group:
            print(f"- {entry['title']}")

if __name__ == "__main__":
    main()