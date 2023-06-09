import json
from typing import List

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, parse_obj_as
from pymongo import MongoClient
import requests as req


class Location(BaseModel):
    latitude: float
    longitude: float

    def to_dict(self):
        return self.dict()

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
    return {"data": "MongoRepository service ran successfully -version 0.0.52"}


@app.post("/syncreq")
async def syncreq(lis : List[SynchronizationRequest]):
    docs = await returnAllUsersDocuments(lis[0].user)
    diffsend = []
    diffneed = []
    if lis[0].ID == "none":
        return SynchronizationAnswer(activities=docs, IDs=diffneed)
    for doc in docs:
        if not any(obj.ID == doc.ID for obj in lis):
            diffsend.append(doc)
    for li in lis:
        if not any(obj.ID == li.ID for obj in docs):
            diffneed.append(li.ID)
    return SynchronizationAnswer(activities=diffsend,IDs=diffneed)




@app.post("/newactivities")
async def newactivities(newac: List[Activity]):
    elevations = []
    for e in newac:
        newA = await getElevation(e.data)
        print(newA)
        e.data = newA
        el = []
        for i in newA:
            el.append(i.altitude)
        elevations.append(Elevationresponse(elevations=el,ID=e.ID))
    await writeAll(newac)
    return elevations


@app.post("/synccheck")
async def synccheck(syncc: List[Elevationcheck]):
    docs = await returnAllUsersDocuments(syncc[0].user)
    if not docs == "error":
        els = []
        for doc in docs:
            if not any(obj.ID == doc.ID for obj in syncc):
                return "Fail"
        for li in syncc:
            if not any(obj.ID == li.ID for obj in docs):
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
        return Synccontrolanswer(elevations=els,msg="OK")

@app.post("/delete")
async def delete(deleteid: str, user: str):
    ans = await delete(deleteid)
    return  ans


async def returnAllUsersDocuments(user: str):
    filters = {"user": user}
    try:
        documents = db["users"].find(filters)
        docs = []
        for doc in documents:
            docs.append(doc)
        activitites = []
        for ds in docs:
            activity = Activity.parse_obj(ds)
            activitites.append(activity)
        #activity_list = parse_obj_as(List[Activity], documents)
        return activitites
    except Exception as e:
        return e


async def writeAll(activitys: List[Activity]):
    activity_dicts = [activity.dict() for activity in activitys]
    try:
        news = db["users"].insert_many(activity_dicts)
        return "done"
    except Exception as e:
        return "error"


async def delete(ID : str):
    filters = {"ID": ID}
    try:
        delete = db["users"].delete_one(filters)
        if delete.deleted_count > 0:
            return "done"
        else:
            return "error"
    except Exception as e:
        print(e)
async def getElevation(lis:List[RoutePoints]):
    lys: List[RoutePoints]
    lys= lis
    locations = []
    for li in lis:
        locations.append(Location(latitude=li.latitude,longitude=li.longitude))
    try:
        my_json = json.dumps([obj.dict() for obj in locations])
        ans = req.post(elevation_api, data=my_json)
    except Exception as e:
        print(e)
    content = ans.text
    print(content)
    try:
        obj = json.loads(content)
        print(obj)
        elevations = obj["eleva"]
        for elevation, point in zip(elevations, lys):
            point.altitude = elevation
        print(lys)
        return lys
    except Exception as e:
        return e
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
