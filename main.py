import json
from typing import List

import requests as req
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
    user: str
    sport_type: str
    date: str
    distance: int
    time: str
    max_speed: int
    average_speed: int
    data: List[RoutePoints]

    def to_dict(self):
        return self.dict()


class SynchronizationRequest(BaseModel):
    ID: str
    user: str


class SynchronizationAnswer(BaseModel):
    activities: List[Activity]
    IDs: List[str]


class Elevationcheck(BaseModel):
    ID: str
    user: str
    elevationversion: bool


class Elevationresponse(BaseModel):
    elevations: List[float]
    ID: str


class Synccontrolanswer(BaseModel):
    elevations: List[Elevationresponse]
    msg: str


# mongo connection
connection_string = "mongodb+srv://user:user@cluster0.hbniblw.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(connection_string)
db = client["userdata"]
elevation_api = "https://elevationmicroservice.azurewebsites.net/elevation"
# initialize FastAPI
app = FastAPI()


@app.get("/")
def index():
    return {"data": "MongoRepository service ran successfully -version 0.0.46"}


@app.post("/syncreq")
async def syncreq(lis: List[SynchronizationRequest]):
    docs = await returnAllUsersDocuments(lis[0].user)
    diffsend = []
    diffneed = []
    for doc in docs:
        if not any(obj.ID == doc.ID for obj in lis):
            diffsend.append(doc)
    for li in lis:
        if not any(obj.ID == li.ID for obj in docs):
            diffneed.append(li.ID)
    return SynchronizationAnswer(activities=diffsend, IDs=diffneed)


@app.post("/newactivities")
async def newactivities(newac: List[Activity]):
    elevations = []
    for e in newac:
        newA = await getElevation(e.data)
        e.data = newA
        el = []
        for i in newA:
            el.append(i.altitude)
        elevations.append(Elevationresponse(elevations=el, ID=e.ID))
    await writeAll(newac)
    return elevations


@app.post("/synccheck")
async def synccheck(syncc: List[Elevationcheck], token: str):
    docs = await returnAllUsersDocuments(syncc[0].user)
    if not docs == "error":
        els = []
        for doc in docs:
            if any(obj.ID == doc.ID for obj in syncc):
                return "Fail"
        for li in syncc:
            if any(obj.ID == li.ID for obj in docs):
                return "Fail"
        for el in syncc:
            if not el.elevationversion:
                obe: Activity
                for ob in docs:
                    if el.ID == ob.ID:
                        obe = ob
                        break
                newA = await getElevation(obe.data)
                el = []
                for i in newA:
                    el.append(i.altitude)
                els.append(Elevationresponse(elevations=el, ID=el.ID))
        return Synccontrolanswer(elevations=els, msg="OK")


@app.post("/delete")
async def delete(deleteid: str, user: str):
    ans = await delete(deleteid)
    return ans


async def returnAllUsersDocuments(user: str):
    filters = {"user": user}
    try:
        documents = db["users"].find(filters)
        return documents
    except Exception as e:
        return "error"


async def writeAll(activitys: List[Activity]):
    activity_dicts = [activity.dict() for activity in activitys]
    try:
        news = db["users"].insert_many(activity_dicts)
        return "done"
    except Exception as e:
        return "error"


async def delete(ID: str):
    filters = {"ID": ID}
    try:
        delete = db["users"].delete_one(filters)
        return "done"
    except Exception as e:
        return "error"


async def getElevation(lis: List[RoutePoints]):
    locations = []
    for li in lis:
        locations.append(Location(latitude=li.latitude, longitude=li.longitude))
    try:
        ans = req.post(elevation_api, data=locations)
    except Exception as e:
        print(e)
    content = ans.text
    try:
        obj = json.loads(content)
        if obj.error:
            return "error"
        else:
            for ob in obj:
                lis.altitude = ob
            return lis
    except Exception as e:
        return "error"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
