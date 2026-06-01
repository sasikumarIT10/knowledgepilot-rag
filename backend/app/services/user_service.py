"""User service for authentication and user management."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password, create_token_pair
from app.db.models import User
from app.schemas.auth import RegisterRequest, TokenResponse


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, data: RegisterRequest) -> User:
        """Create a new user."""
        user = User(
            email=data.email.lower(),
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password."""
        user = await self.get_by_email(email)
        
        if user is None:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user

    async def create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        token_pair = create_token_pair(user.id, user.email)
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes in seconds
        )

    async def update(
        self,
        user: User,
        full_name: str | None = None,
        email: str | None = None,
    ) -> User:
        """Update user information."""
        if full_name is not None:
            user.full_name = full_name
        
        if email is not None:
            user.email = email.lower()
        
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password."""
        if not verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        return True

    async def delete(self, user: User) -> None:
        """Delete user account."""
        await self.db.delete(user)
        await self.db.flush()
