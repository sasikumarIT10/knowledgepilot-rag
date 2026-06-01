"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, CurrentUser
from app.core.security import verify_token, create_token_pair
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: DbSession,
):
    """Register a new user."""
    user_service = UserService(db)
    
    # Check if user exists
    existing_user = await user_service.get_by_email(data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    user = await user_service.create(data)
    
    # Generate tokens
    tokens = await user_service.create_tokens(user)
    
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: DbSession,
):
    """Login with email and password."""
    user_service = UserService(db)
    
    # Authenticate user
    user = await user_service.authenticate(data.email, data.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Generate tokens
    tokens = await user_service.create_tokens(user)
    
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: DbSession,
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    token_data = verify_token(data.refresh_token, token_type="refresh")
    
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Get user
    user_service = UserService(db)
    user = await user_service.get_by_id(token_data.user_id)
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Generate new tokens
    token_pair = create_token_pair(user.id, user.email)
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type="bearer",
        expires_in=30 * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: CurrentUser,
):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout():
    """Logout current user.
    
    Note: With JWT, logout is handled client-side by removing the token.
    This endpoint can be used for audit logging or token blacklisting.
    """
    return {"message": "Successfully logged out"}
