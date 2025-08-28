from app.api import nhs_login
from app.api.v1 import user
from fastapi import FastAPI, status

from app.schemas.common import MessageResponse

app = FastAPI(
    title="Active10 - User Management Microservice",
    version="1.0.0",
    description="This is the User Management Microservice for the Active10 application.",
)


@app.get(
    "/", response_model=MessageResponse, status_code=status.HTTP_200_OK, tags=["Root"]
)
def read_root():
    return {"message": "Welcome to Active10 - User Management Microservice!"}


@app.get(
    "/health",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
)
def health_check():
    return {"message": "Healthy"}


app.include_router(user.router)
app.include_router(nhs_login.router)
