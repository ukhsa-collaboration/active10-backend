from pydantic import BaseModel


class CuratedWalksSearch(BaseModel):
    page: int
    amount: int  # [5 .. 50]
    lat: float | None = None
    lon: float | None = None
    postcode: str | None = None
    radius: float | None = None
    attributes: list[str] | None = None
    name: str | None = None
    minDuration: float | None = None
    maxDuration: float | None = None
    minDistance: float | None = None
    maxDistance: float | None = None
    premiumLevel: int | None = None  # [0 .. 1]
    sort: str | None = None
    username: str | None = None


class CuratedWalkRetrieve(BaseModel):
    includeSteps: bool | None = True
    includeRelated: bool | None = False


class DynamicRoutesCircularCollection(BaseModel):
    categorise: bool | None = None
    distances: list[float] | None = None
    max_paths: int | None = 1  # [1 .. 4]
    start_point: list[float] | None = None  # [lat, lon] it looks it's required
    postcode: str | None = None
    title_unit_format: str | None = None  # km, miles
    store: bool | None = False
    distance_influence: float | None = None  # [1 .. 100]
    amble_influence: float | None = None  # [1 .. 100]
    tranquil_city_influence: float | None = None  # [1 .. 100]
    air_quality_influence: float | None = None  # [1 .. 100]
    foot_network_influence: float | None = None  # [1 .. 100]
    details: list[str] | None = None  # list of enums
    locale: str | None = "en"
    points_encoded: bool | None = True
    profile: str | None = None  # greenest, foot
