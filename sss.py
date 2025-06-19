# filename: simkl_sync.py

import json, requests
from datetime import datetime, timezone
from clist import CONFIG, get_simkl_list, get_sonarr_titles, get_radarr_titles, match_by_ids, fuzzy_match, color, read_exclude_list_from_failed_file

FAILED_FILE = "failed.txt"

def route_by_type(instances, type_str):
    return [inst for inst in instances if inst.get("type") == type_str]

def post_to_sonarr(item, type_str):
    sonarr_list = route_by_type(CONFIG["sonarr"], type_str)
    for s in sonarr_list:
        try:
            tvdb_id = item["ids"].get("tvdb")
            if not tvdb_id:
                # Fallback: Try lookup
                print("No TVDb ID found: Using Lookup")
                lookup_url = f"{s['url'].rstrip('/')}/api/v3/series/lookup?term={requests.utils.quote(item['title'])}"
                res = requests.get(lookup_url, headers={"X-Api-Key": s["api_key"]})
                if res.ok and res.json():
                    best = res.json()[0]
                    tvdb_id = best.get("tvdbId")

            if not tvdb_id:
                raise Exception("No TVDb ID found (direct or fallback)")

            payload = {
                "title": item["title"],
                "qualityProfileId": s["profile_id"],
                "monitored": True,
                "addOptions": {"searchForMissingEpisodes": False},
                "tvdbId": tvdb_id,
                "images": [],
                "seasonFolder": True,
                "rootFolderPath": s["root"]
            }
            r = requests.post(f"{s['url'].rstrip('/')}/api/v3/series",
                              headers={"X-Api-Key": s["api_key"]},
                              json=payload)
            if r.status_code in (200, 201):
                print(f"- {item['title']} ({type_str}) added successfully")
                return True
            else:
                print(f"- {item['title']} ({type_str}) add failed: {r.status_code} {color(r.json()[0]['errorMessage'], _color='red')}")
        except Exception as e:
            print(f"- {item['title']} ({type_str}) add failed: {e}")
    return False

def post_to_radarr(item):
    radarr_list = route_by_type(CONFIG["radarr"], "movie")
    for r in radarr_list:
        try:
            tmdb_id = item["ids"].get("tmdb")
            if not tmdb_id:
                # Fallback: Try lookup
                lookup_url = f"{r['url'].rstrip('/')}/api/v3/movie/lookup?term={requests.utils.quote(item['title'])}"
                res = requests.get(lookup_url, headers={"X-Api-Key": r["api_key"]})
                if res.ok and res.json():
                    best = res.json()[0]
                    tmdb_id = best.get("tmdbId")

            if not tmdb_id:
                raise Exception("No TMDb ID found (direct or fallback)")

            payload = {
                "title": item["title"],
                "qualityProfileId": r["profile_id"],
                "monitored": True,
                "tmdbId": int(tmdb_id),
                "rootFolderPath": r["root"],
                "addOptions": {"searchForMovie": False}
            }
            res = requests.post(f"{r['url'].rstrip('/')}/api/v3/movie",
                                headers={"X-Api-Key": r["api_key"]},
                                json=payload)
            if res.status_code in (200, 201):
                print(f"- {item['title']} (movie) added successfully")
                return True
            else:
                print(f"- {item['title']} (movie) add failed: {res.status_code} {color(r.json()[0]['errorMessage'], _color='red')}")
        except Exception as e:
            print(f"- {item['title']} (movie) add failed: {e}")
    return False

def save_failed(timestamp, failures):
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        f.write(f"Last Check: {timestamp}\n\n")
        for category, items in failures.items():
            if not items:
                continue
            f.write(f"{category.capitalize()}: {len(items)}\n")
            for i in items:
                f.write(f"- {i['title']}\n")
            f.write("\n")

        # Write Excluded section from EXCLUDE list
        f.write(f"Excluded: {len(EXCLUDE)}\n")
        for title in EXCLUDE:
            f.write(f"- {title} ##########\n")
        f.write("\n")


def main():
    global EXCLUDE
    EXCLUDE = read_exclude_list_from_failed_file()
    print("📥 Fetching Simkl watchlist...")
    simkl_items = get_simkl_list(EXCLUDE)
    print("📡 Fetching Sonarr/Radarr libraries...")
    sonarr_stack = get_sonarr_titles()
    radarr_stack = get_radarr_titles()
    combined_stack = sonarr_stack + radarr_stack

    failures = {"anime": [], "tv shows": [], "movies": []}

    for item in simkl_items:
        typ = item["type"]
        anime_type = item.get("anime_type", "")
        type_str = typ

        # Fix type for anime
        if typ == "anime":
            if anime_type == "movie":
                type_str = "movies"
            else:
                type_str = "anime"
        elif typ == "shows":
            type_str = "tv"
        elif typ == "movies":
            type_str = "movies"

        if match_by_ids(item, combined_stack):
            continue

        match, _ = fuzzy_match(item, combined_stack, CONFIG["fuzzy_threshold"])
        if match:
            continue

        # Add via proper route
        success = False
        if type_str in ("anime", "tv"):
            success = post_to_sonarr(item, type_str)
        elif type_str == "movies":
            success = post_to_radarr(item)

        if not success:
            key = "tv shows" if type_str == "tv" else type_str
            failures[key].append(item)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    save_failed(now, failures)
    print(f"✅ Done. Failures logged to `{FAILED_FILE}`")

if __name__ == "__main__":
    main()
