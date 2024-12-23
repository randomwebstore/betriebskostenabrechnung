from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from fastapi.responses import Response


from datetime import datetime
import shelve
import hashlib
from pydantic import BaseModel


db = shelve.open("locations.db")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Location(BaseModel):
    address: str
    lat: float
    lon: float
    street: str
    house_number: str  # may contain letters
    postcode: int
    city: str
    date: str = datetime.now().isoformat()


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/location")
async def save_location(location: Location):
    # Create hash from address
    addr_hash = hashlib.sha3_256(location.address.encode()).hexdigest()
    db[addr_hash] = location
    return {"status": "success", "hash": addr_hash}


@app.get("/locations")
async def get_locations():
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
