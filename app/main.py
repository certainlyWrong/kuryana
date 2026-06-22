import asyncio
from typing import Any, Dict, List

import primp
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.lib.msgspec_json import MsgSpecJSONResponse
from app.schemas import (
    CastResponse,
    DramaResponse,
    DramalistResponse,
    EpisodesResponse,
    ErrorResponse,
    ListResponse,
    PersonResponse,
    PhotosResponse,
    ReviewsResponse,
    ScheduleResponse,
    SearchResponse,
    SeasonalDrama,
)
from app.utils import fetch_func, search_func

app = FastAPI(
    title="Kuryana",
    description="A simple MyDramaList.com scraper API.",
    default_response_class=MsgSpecJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_error_responses = {
    400: {"model": ErrorResponse, "description": "Page error returned by MDL"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


@app.get("/")
async def index() -> Dict[str, Any]:
    return {"message": "A Simple and Basic MDL Scraper API"}


@app.get(
    "/search/q/{query}",
    response_model=SearchResponse,
    tags=["search"],
    summary="Search dramas and people",
)
async def search(query: str, response: Response) -> Dict[str, Any]:
    code, r = await search_func(query=query)

    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}",
    response_model=DramaResponse,
    tags=["drama"],
    summary="Drama details",
    responses=_error_responses,
)
async def fetch(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=drama_id, t="drama")

    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/cast",
    response_model=CastResponse,
    tags=["drama"],
    summary="Drama full cast",
    responses=_error_responses,
)
async def fetch_cast(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/cast", t="cast")

    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/episodes",
    response_model=EpisodesResponse,
    tags=["drama"],
    summary="Drama episodes",
    responses=_error_responses,
)
async def fetch_episodes(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/episodes", t="episodes")

    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/reviews",
    response_model=ReviewsResponse,
    tags=["drama"],
    summary="Drama reviews",
    responses=_error_responses,
)
async def fetch_reviews(
    drama_id: str, response: Response, page: int = 1
) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/reviews?page={page}", t="reviews")

    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/photos",
    response_model=PhotosResponse,
    tags=["drama"],
    summary="Drama photos",
    responses=_error_responses,
)
async def fetch_drama_photos(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/photos", t="photos")

    response.status_code = code
    return r


@app.get(
    "/people/{person_id}",
    response_model=PersonResponse,
    tags=["people"],
    summary="Person details",
    responses=_error_responses,
)
async def person(person_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"people/{person_id}", t="person")

    response.status_code = code
    return r


@app.get(
    "/people/{person_id}/photos",
    response_model=PhotosResponse,
    tags=["people"],
    summary="Person photos",
    responses=_error_responses,
)
async def fetch_person_photos(person_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"people/{person_id}/photos", t="photos")

    response.status_code = code
    return r


@app.get(
    "/dramalist/{user_id}",
    response_model=DramalistResponse,
    tags=["user"],
    summary="User drama list",
    responses=_error_responses,
)
async def dramalist(user_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"dramalist/{user_id}", t="dramalist")

    response.status_code = code
    return r


@app.get(
    "/list/{list_id}",
    response_model=ListResponse,
    tags=["list"],
    summary="MDL curated list",
    responses=_error_responses,
)
async def lists(list_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"list/{list_id}", t="lists")

    response.status_code = code
    return r


@app.get(
    "/seasonal/{year}/{quarter}",
    response_model=List[SeasonalDrama],
    tags=["calendar"],
    summary="Seasonal drama list",
    description="Dramas airing in the given quarter. `quarter`: 1 = Jan–Mar · 2 = Apr–Jun · 3 = Jul–Sep · 4 = Oct–Dec.",
)
async def mdlSeasonal(year: int, quarter: int, response: Response) -> Any:
    def _fetch() -> primp.Response:
        client = primp.Client(impersonate="chrome", impersonate_os="linux")
        return client.post(
            "https://mydramalist.com/v1/calendar/quarter",
            data={"quarter": quarter, "year": year},
        )

    r = await asyncio.to_thread(_fetch)
    response.status_code = r.status_code

    if not r.ok:
        return []

    try:
        return r.json()
    except Exception:
        response.status_code = 502
        return []


@app.get(
    "/schedule",
    response_model=ScheduleResponse,
    tags=["calendar"],
    summary="Current week episode schedule",
    description="Episode schedule for the current week, organised by day (0 = Monday … 6 = Sunday).",
)
async def mdlSchedule(response: Response) -> Any:
    def _fetch() -> primp.Response:
        client = primp.Client(impersonate="chrome", impersonate_os="linux")
        return client.post("https://mydramalist.com/v1/calendar/week")

    r = await asyncio.to_thread(_fetch)
    response.status_code = r.status_code

    if not r.ok:
        return {}

    try:
        return r.json()
    except Exception:
        response.status_code = 502
        return {}
