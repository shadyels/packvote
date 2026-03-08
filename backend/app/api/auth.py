from fastapi import APIRouter

from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserCreate) -> UserResponse:
    # TODO: implement in auth step
    raise NotImplementedError


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin) -> TokenResponse:
    # TODO: implement in auth step
    raise NotImplementedError


@router.get("/me", response_model=UserResponse)
async def get_me() -> UserResponse:
    # TODO: implement in auth step
    raise NotImplementedError
