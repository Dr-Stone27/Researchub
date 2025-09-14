import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.main import app
from httpx import AsyncClient
import os

# Use a dedicated test database URL (set this in your .env or CI environment)
DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST", "postgresql+asyncpg://user:password@localhost/test_db")

engine_test = create_async_engine(DATABASE_URL_TEST, future=True)
AsyncSessionTest = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    # Create all tables at the start of the test session
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables at the end of the test session
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def async_session():
    async with AsyncSessionTest() as session:
        yield session

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac 