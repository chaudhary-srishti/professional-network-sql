"""Request and response models. Response models double as the OpenAPI contract at /docs.

Routers return ``dict(record)`` from asyncpg and FastAPI validates it against these models,
so uuid/datetime/array/numeric types serialize consistently.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- users
class _UserProfile(BaseModel):
    name: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    bio: str | None = None
    profile_picture: str | None = None
    cover_photo: str | None = None
    location_street: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    location_postal_code: str | None = None
    location_longitude: float | None = None
    location_latitude: float | None = None


class UserCreate(_UserProfile):
    email: str


class UserUpdate(_UserProfile):
    """email and super_admin are intentionally absent — not client-updatable."""


class UserOut(_UserProfile):
    id: UUID
    email: str
    super_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None


# --------------------------------------------------------------------------- organizations
class _OrgFields(BaseModel):
    name: str | None = None
    description: str | None = None
    overview: str | None = None
    logo: str | None = None
    cover_photo: str | None = None
    size: str | None = None
    categories: list[str] | None = None
    location_street: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    location_postal_code: str | None = None
    location_longitude: float | None = None
    location_latitude: float | None = None


class OrganizationCreate(_OrgFields):
    name: str


class OrganizationUpdate(_OrgFields):
    """firm_url is server-generated and never client-updatable."""


class OrganizationOut(_OrgFields):
    id: UUID
    firm_url: str
    categories: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MemberAdd(BaseModel):
    user_id: UUID
    role: str = "member"


class MemberOut(BaseModel):
    organization_id: UUID
    user_id: UUID
    role: str
    added_at: datetime


# --------------------------------------------------------------------------- links
class ConnectionCreate(BaseModel):
    target_id: UUID
    personal_note: str | None = None


class ConnectionOut(BaseModel):
    id: UUID
    requester_id: UUID
    target_id: UUID
    status: str
    personal_note: str | None = None
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime


class ConnectionEdgeOut(BaseModel):
    id: UUID
    user_id: UUID
    other_user_id: UUID
    direction: str
    status: str
    created_at: datetime


class FollowCreate(BaseModel):
    organization_id: UUID


class FollowOut(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    created_at: datetime


class MemberRequestCreate(BaseModel):
    organization_id: UUID
    personal_note: str | None = None


class MemberRequestOut(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    status: str
    personal_note: str | None = None
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- posts / articles
class PostCreate(BaseModel):
    firm_id: UUID | None = None
    hashtags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    shared_post_id: UUID | None = None
    shared_article_id: UUID | None = None


class PostUpdate(BaseModel):
    hashtags: list[str] | None = None
    images: list[str] | None = None
    shared_post_id: UUID | None = None
    shared_article_id: UUID | None = None


class PostFeedOut(BaseModel):
    id: UUID
    author_id: UUID
    author_name: str | None = None
    author_title: str | None = None
    author_picture: str | None = None
    firm_id: UUID | None = None
    firm_name: str | None = None
    firm_url: str | None = None
    firm_logo: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    shared_post_id: UUID | None = None
    shared_article_id: UUID | None = None
    like_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime


class ArticleCreate(BaseModel):
    firm_id: UUID | None = None
    cover_image: str | None = None
    images: list[str] = Field(default_factory=list)


class ArticleUpdate(BaseModel):
    cover_image: str | None = None
    images: list[str] | None = None


class ArticleFeedOut(BaseModel):
    id: UUID
    author_id: UUID
    author_name: str | None = None
    author_title: str | None = None
    author_picture: str | None = None
    firm_id: UUID | None = None
    firm_name: str | None = None
    firm_url: str | None = None
    firm_logo: str | None = None
    cover_image: str | None = None
    images: list[str] = Field(default_factory=list)
    like_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- engagement
class CommentCreate(BaseModel):
    body: str = ""


class CommentOut(BaseModel):
    id: UUID
    author_id: UUID
    firm_id: UUID | None = None
    post_id: UUID | None = None
    article_id: UUID | None = None
    body: str
    like_count: int
    created_at: datetime
    updated_at: datetime


class LikeResult(BaseModel):
    liked: bool
    like_count: int


# --------------------------------------------------------------------------- stats
class UserStatsOut(BaseModel):
    user_id: UUID
    name: str | None = None
    posts_count: int
    articles_count: int
    comments_count: int
    connections_count: int
    pending_requests_count: int
    following_count: int
    likes_received_count: int


class FirmStatsOut(BaseModel):
    firm_id: UUID
    name: str | None = None
    members_count: int
    followers_count: int
    pending_member_requests_count: int
    posts_count: int
    articles_count: int
