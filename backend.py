import hashlib
import shelve
import httpx
from datetime import datetime
from shelve import Shelf

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from starlette.responses import FileResponse
from typing_extensions import Annotated

DB_PATH: str = "locations.db"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    db = shelve.open(DB_PATH)
    try:
        yield db
    finally:
        db.close()


class Location(BaseModel):
    address: str
    lat: float
    lon: float
    street: str
    house_number: str  # may contain letters
    postcode: int
    city: str
    date: str = datetime.now().isoformat()
    visited: bool = False


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/location")
async def save_location(location: Location, db: Annotated[Shelf, Depends(get_db)]):
    # Create hash from address
    addr_hash = hashlib.sha3_256(location.address.encode()).hexdigest()
    db[addr_hash] = location
    return {"status": "success", "hash": addr_hash}


@app.get("/locations")
async def get_locations(db: Annotated[Shelf, Depends(get_db)]):
    csv_data = "street,house_number,plz,city,date\n"
    for loc in db.values():
        csv_data += (
            f"{loc.street},{loc.house_number},{loc.postcode},{loc.city},{loc.date}\n"
        )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=locations.csv"},
    )


@app.get("/debug")
async def debug(db: Annotated[Shelf, Depends(get_db)]):
    return db

async def submit_form(location: Location) -> bool:
    base_url = "https://bundescloud.die-linke.de"
    form_id = "211"
    share_hash = "eSAXf3aXTWW8wgxNFNG34wEJ"
    endpoint = f"/ocs/v2.php/apps/forms/api/v3/forms/{form_id}/submissions"

    answer_keys = {
        "lat": 634,
        "lon": 635,
        "city": 637,
        "date": 638,
        "street": 639,
        "house_number": 640,
        "plz": 641,
        "visited": 642,
        "visited_nextcloud_key": 643
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "OCS-APIRequest": "true"
    }
    
    # Map location data to form field IDs
    payload = {
	"answers": {
		answer_keys["lat"]: [
			location.lat
		],
		answer_keys["lon"]: [
			location.lon
		],
        answer_keys["city"]: [
            location.city
        ],
        answer_keys["date"]: [
            location.date
        ],
        answer_keys["street"]: [
            location.street
        ],
        answer_keys["house_number"]: [
            location.house_number
        ],
        answer_keys["plz"]: [
            location.postcode 
        ]

	},
        "shareHash": share_hash
    }

    if location.visited:
        payload["answers"][answer_keys["visited"]] = answer_keys["visited_nextcloud_key"]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url + endpoint,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Form submission failed: {str(e)}")