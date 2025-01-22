import requests
import json
from pathlib import Path
from os import getenv

USERNAME = getenv("LINKE_USERNAME")
PASSWORD = getenv("LINKE_PASSWORD")

session = requests.Session()

events = [7970, 8023, 8456, 8269, 7662]


def login():
    req = session.post(
        "https://api.die-linke.app/api/v1/session/login/",
        json={
            "identifier": USERNAME,
            "password": PASSWORD,
            "long_session": True,
        },
    )
    req.raise_for_status()
    return req.cookies.get_dict()


csrftoken = login()["csrftoken"]


def get_areas(event_id: int):
    req = session.get(
        f"https://api.die-linke.app/api/v1/event-areas/?event={event_id}",
        headers={
            "x-csrftoken": csrftoken,
            "Referer": "https://web.die-linke.app/",
        },
    )
    req.raise_for_status()
    return req.json()


def get_completion_notes(area_id: int):
    req = session.get(
        f"https://api.die-linke.app/api/v1/completion-notes/?event_area={area_id}",
        headers={
            "x-csrftoken": csrftoken,
            "Referer": "https://web.die-linke.app/",
        },
    )
    req.raise_for_status()
    return req.json()


heatmap: dict[str, str] = {}
areas: dict[str, str] = {}
for event in events:
    for area in get_areas(event)["data"]:
        completions = get_completion_notes(area["id"])["data"]
        for street in area["area_details"]["streets"]:
            for address in street["addresses"]:
                heatmap[address["osm_id"]] = {
                    "street": street["name"],
                    "house_number": address["house_number"],
                    "geometry": address["geometry"],
                }

        for completion in completions:
            heatmap[int(completion["target_id"])]["completed"] = completion["completed"]


output = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": [],
}

for item in heatmap.values():
    output["features"].append(
        {
            "type": "Feature",
            "properties": {
                "street": item["street"],
                "house_number": item["house_number"],
                "completed": item.get("completed", False),
                "test": 1,
            },
            "geometry": item["geometry"],
        }
    )

Path("output.json").write_text(json.dumps(output, indent=2))
