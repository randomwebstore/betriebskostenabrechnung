import hashlib
import shelve
from datetime import datetime
from shelve import Shelf

from fastapi import Depends, FastAPI
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
    date: str | None = None
    valid: bool = False


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/location")
async def save_location(location: Location, db: Annotated[Shelf, Depends(get_db)]):
    # Create hash from address
    addr_hash = hashlib.sha3_256(location.address.encode()).hexdigest()
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
