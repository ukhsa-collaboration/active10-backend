from app.api import v1_router, nhs_login
from fastapi import FastAPI, status

app = FastAPI(
    title="Active10 - Auth Microservice",
    version="1.0.0",
    description="This is the authentication microservice for the Active10 application.",
)


@app.get("/", status_code=status.HTTP_200_OK, tags=["Root"])
def read_root():
    return {"message": "Welcome to Active10 - Auth Microservice!"}


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return {"status": "Healthy"}


app.include_router(v1_router.routes, prefix="/api")
app.include_router(nhs_login.router)
