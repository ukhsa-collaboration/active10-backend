from fastapi import APIRouter

router = APIRouter(prefix="/walking_plans", tags=["walking plans"])


@router.post("/")
async def create_walking_plan():
    pass


@router.get("/{user_id}")
async def get_walking_plans_by_user():
    pass


@router.get("/walking_plans/{user_id}/{plan_id}")
async def get_walking_plan_by_id():
    pass


@router.put("/{plan_id}")
async def update_walking_plan(plan_id):
    pass


@router.delete("/{user_id}/{plan_id}")
async def delete_walking_plan(plan_id):
    pass
