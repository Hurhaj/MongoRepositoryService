from typing import List

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient


class Location(BaseModel):
    latitude: float
    longitude: float


class RoutePoints(BaseModel):
    latitude: float
    longitude: float
    altitude: float


class Activity(BaseModel):
    ID: str
    sport_type: str
    date: str
    distance: int
    time: str
    max_speed: int
    average_speed: int
    data: List[RoutePoints]


# mongo connection
connection_string = "mongodb+srv://user:user@cluster0.hbniblw.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(connection_string)
db = client["userdata"]

# initialize FastAPI
app = FastAPI()


@app.get("/")
def index():
    return {"data": "MongoRepository service ran successfully -version 0.0.2"}


@app.post("/mongo")
async def put(user: str):
    return {"working": "repository"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
