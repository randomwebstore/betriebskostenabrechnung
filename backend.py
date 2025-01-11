import hashlib
import shelve
from datetime import datetime
from os import getenv
from shelve import Shelf

import requests
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.responses import FileResponse
from typing_extensions import Annotated

EVENT_ID: int = 8566
DB_PATH: str = "locations.db"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def login(session):
    req = session.post(
        "https://api.die-linke.app/api/v1/session/login/",
        json={
            "identifier": getenv("AKTIVISTI_USERNAME"),
            "password": getenv("AKTIVISTI_PASSWORD"),
            "long_session": True,
        },
    )
    req.raise_for_status()
    return req.cookies.get_dict()["csrftoken"]


async def get_db():
    db = shelve.open(DB_PATH)
    try:
        yield db
    finally:
        db.close()


def get_session():
    session = requests.Session()
    csrftoken: str = login(session)
    return session, csrftoken


def add_location(
    location: dict,
    lat: float,
    lng: float,
):
    address = f"{location['street']} {location['house_number']}, {location['postcode']} {location['city']}"
    session, csrftoken = get_session()
    session.post(
        "https://api.die-linke.app/api/v1/posters/",
        headers={
            "x-csrftoken": csrftoken,
            "Referer": "https://web.die-linke.app/",
        },
        json={
            "location_description": address,
            "location": {"lat": lat, "lng": lng},
            "status": "DAMAGED",
            "mounted_on": "OTHER",
            "event": EVENT_ID,
        },
    )


class Location(BaseModel):
    address: str
    lat: float
    lon: float
    street: str
    house_number: str  # may contain letters
    postcode: int
    city: str
    date: str | None = None
    valid: bool = False


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/location")
async def save_location(location: Location, db: Annotated[Shelf, Depends(get_db)]):
    # Create hash from address
    addr_hash = hashlib.sha3_256(location.address.encode()).hexdigest()

    if addr_hash not in db and not location.valid:
        print("Fresh address, adding to map")
        add_location(location.dict(), location.lat, location.lon)

    print(f"Saved location {location} with hash {addr_hash}")
    location.date = datetime.now().isoformat()
    db[addr_hash] = location.model_dump()
    return {"status": "success", "hash": addr_hash}


@app.get("/locations")
async def get_locations(db: Annotated[Shelf, Depends(get_db)]):
    csv_data = "street,house_number,plz,city,date,valid\n"
    for loc in db.values():
        csv_data += f"{loc['street']},{loc['house_number']},{loc['postcode']},{loc['city']},{loc['date']},{loc['valid']}\n"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=locations.csv"},
    )


@app.get("/debug")
async def debug(db: Annotated[Shelf, Depends(get_db)]):
    return db
