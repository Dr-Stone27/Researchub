from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler

from .routers import notifications
from .routers import guides
from .routers import dashboard
from .routers import users
from .routers import tags
from .routers import research
from .routers import library
import logging
import sys
from app.settings import settings
import os
from fastapi.security import OAuth2PasswordBearer
# Sentry placeholder (uncomment and configure if needed)
# import sentry_sdk
# sentry_sdk.init(dsn="your_sentry_dsn_here")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

from app.database import engine
from app.models import Base 

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

"""
Configure CORS using origins from centralized settings.
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



# Add this after creating the FastAPI app instance


# Warn if CORS is insecure in production
env = os.getenv("ENV", "development")
if env == "production" and (not settings.cors_origins or "*" in [str(origin) for origin in settings.cors_origins]):
    logging.warning("CORS is set to allow all origins in production! This is a security risk. Set CORS_ORIGINS to trusted domains only.")

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return await request_validation_exception_handler(request, exc)



app.include_router(notifications.router,tags=["notifications"])
app.include_router(guides.router,  tags=["guides"])
app.include_router(dashboard.router , tags=["dashboard"])
app.include_router(users.router, tags=["users"])
app.include_router(tags.router , tags=["tags"])
app.include_router(research.router, tags=["research"])
app.include_router(library.router, tags=["library"])



@app.get("/")
def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the Local Engineering Research Resource Hub API"}

# Global error handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.detail} (status: {exc.status_code}) at {request.url}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Global error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc} at {request.url}")
    # Optionally send to Sentry here
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}) 


