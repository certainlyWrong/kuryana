from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ─── Error ─────────────────────────────────────────────────────────────────────


class ErrorDescription(BaseModel):
    title: str
    info: str


class ErrorResponse(BaseModel):
    error: bool = True
    code: int
    description: Union[str, ErrorDescription]


# ─── Search ────────────────────────────────────────────────────────────────────


class SearchDrama(BaseModel):
    slug: str
    thumb: str
    mdl_id: Optional[str] = None
    title: str = ""
    ranking: Optional[str] = None
    type: Optional[str] = None
    year: Optional[int] = None
    series: Union[str, bool] = False
    rating: Optional[float] = None


class SearchPerson(BaseModel):
    slug: str
    thumb: str
    name: str
    nationality: str


class SearchResults(BaseModel):
    dramas: List[SearchDrama] = []
    people: List[SearchPerson] = []


class SearchResponse(BaseModel):
    query: str
    results: SearchResults
    scrape_date: datetime


# ─── Shared ─────────────────────────────────────────────────────────────────────


class CastPreview(BaseModel):
    name: str
    profile_image: str
    slug: str
    link: str


class RelatedContentItem(BaseModel):
    title: str
    link: str
    description: str
    slug: str


# ─── Drama ─────────────────────────────────────────────────────────────────────


class DramaOthers(BaseModel):
    model_config = ConfigDict(extra="allow")

    related_content: Optional[List[RelatedContentItem]] = None


class DramaData(BaseModel):
    link: str
    title: str = ""
    complete_title: str = ""
    sub_title: Optional[str] = None
    year: Optional[str] = None
    rating: Union[float, str] = ""
    poster: str = ""
    synopsis: str = ""
    casts: List[CastPreview] = []
    next_episode_airing: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw next-episode data from MDL's inline JS. Only present for currently airing dramas.",
    )
    current_episode: Optional[str] = None
    details: Optional[Dict[str, str]] = Field(
        default=None,
        description="Dynamic key-value pairs from the drama detail sidebar (e.g. Native Title, Also Known As, Genres).",
    )
    others: Optional[DramaOthers] = Field(
        default=None,
        description="Additional metadata sections. Keys are dynamic (e.g. 'also_known_as', 'genres'). 'related_content' is always typed.",
    )


class DramaResponse(BaseModel):
    slug_query: str
    data: DramaData
    scrape_date: datetime


# ─── Cast ──────────────────────────────────────────────────────────────────────


class CastRole(BaseModel):
    name: Optional[str] = None
    type: str = ""


class CastMember(BaseModel):
    name: str
    profile_image: str
    slug: str
    link: str
    role: Optional[CastRole] = None


class CastData(BaseModel):
    link: str
    title: str = ""
    poster: str = ""
    casts: Dict[str, List[CastMember]] = Field(
        default={},
        description="Cast grouped by credit category (e.g. 'Main Role', 'Support Role', 'Director').",
    )


class CastResponse(BaseModel):
    slug_query: str
    data: CastData
    scrape_date: datetime


# ─── Episodes ──────────────────────────────────────────────────────────────────


class Episode(BaseModel):
    title: str
    image: str
    link: str
    rating: str
    air_date: Optional[str] = None


class EpisodesData(BaseModel):
    link: str
    title: str = ""
    episodes: List[Episode] = []


class EpisodesResponse(BaseModel):
    slug_query: str
    data: EpisodesData
    scrape_date: datetime


# ─── Reviews ───────────────────────────────────────────────────────────────────


class Reviewer(BaseModel):
    name: str
    user_link: str
    user_image: str
    info: str


class ReviewRatings(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall: float = 0.0


class Review(BaseModel):
    reviewer: Reviewer
    review: List[str] = []
    ratings: ReviewRatings = Field(default_factory=ReviewRatings)


class ReviewsData(BaseModel):
    link: str
    title: str = ""
    poster: str = ""
    reviews: List[Review] = []


class ReviewsResponse(BaseModel):
    slug_query: str
    data: ReviewsData
    scrape_date: datetime


# ─── Photos ────────────────────────────────────────────────────────────────────


class Photo(BaseModel):
    link: str = Field(description="Link to the photo detail page on MDL.")
    image: str = Field(description="Thumbnail URL (suffix _3m.jpg).")
    full_image: str = Field(description="Full-size URL (suffix _3f.jpg).")


class PhotosData(BaseModel):
    link: str
    title: Optional[str] = None
    photos: List[Photo] = []


class PhotosResponse(BaseModel):
    slug_query: str
    data: PhotosData
    scrape_date: datetime


# ─── Person ────────────────────────────────────────────────────────────────────


class WorkTitle(BaseModel):
    link: str
    name: str


class WorkRole(BaseModel):
    name: Optional[str] = None
    type: str = ""


class WorkItem(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    year: Union[int, str] = Field(description="Release year or 'TBA'.")
    title: WorkTitle
    rating: Union[float, str] = ""
    role: Optional[WorkRole] = Field(
        default=None, description="Character role. Present for actors."
    )
    type: Optional[str] = Field(
        default=None, description="Credit type. Present for directors/writers."
    )
    episodes: Optional[int] = None


class PersonData(BaseModel):
    link: str
    name: str = ""
    about: str = ""
    profile: str = ""
    works: Dict[str, List[WorkItem]] = Field(
        default={},
        description="Works grouped by category (e.g. 'Drama', 'Movie', 'Special').",
    )
    details: Optional[Dict[str, str]] = Field(
        default=None,
        description="Dynamic key-value pairs from the person detail sidebar (e.g. Born, Nationality, Height).",
    )


class PersonResponse(BaseModel):
    slug_query: str
    data: PersonData
    scrape_date: datetime


# ─── DramaList ─────────────────────────────────────────────────────────────────


class DramalistItem(BaseModel):
    name: str
    id: str
    score: str
    episode_seen: str
    episode_total: str


class DramalistCategory(BaseModel):
    items: List[DramalistItem] = []
    stats: Dict[str, str] = {}


class DramalistData(BaseModel):
    link: str
    list: Dict[str, DramalistCategory] = Field(
        default={},
        description="Drama list grouped by watch status (e.g. 'Currently Watching', 'Completed', 'Dropped').",
    )


class DramalistResponse(BaseModel):
    slug_query: str
    data: DramalistData
    scrape_date: datetime


# ─── List ──────────────────────────────────────────────────────────────────────


class ListShowItem(BaseModel):
    title: str
    image: str
    rank: str = ""
    url: str = ""
    slug: Optional[str] = None
    type: str
    year: str
    episodes: Optional[int] = None
    short_summary: str = ""


class ListPersonItem(BaseModel):
    name: str
    type: str
    image: str
    slug: str
    url: str
    nationality: str = ""
    details: str = ""


class ListData(BaseModel):
    link: str
    title: str = ""
    description: str = ""
    list: List[Union[ListPersonItem, ListShowItem]] = Field(
        default=[],
        description="List items. Each entry is either a show or a person. Person entries always carry type='person'.",
    )


class ListResponse(BaseModel):
    slug_query: str
    data: ListData
    scrape_date: datetime


# ─── Seasonal ──────────────────────────────────────────────────────────────────


class SeasonalDrama(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    title: str
    episodes: int
    ranking: int
    popularity: int
    country: str
    content_type: str
    type: str
    synopsis: str
    released_at: str
    url: str
    genres: str
    thumbnail: str
    cover: str
    rating: float
    timezone: str
    add_status: bool


# ─── Schedule ──────────────────────────────────────────────────────────────────


class ScheduleRelationship(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    title: str


class ScheduleResponse(BaseModel):
    items: List[List[Any]] = Field(
        description=(
            "7 sublists indexed by day of the week (0 = Monday … 6 = Sunday). "
            "Each entry references drama IDs from 'relationships'."
        )
    )
    relationships: List[ScheduleRelationship] = Field(
        description="Full drama objects referenced by the items lists."
    )
