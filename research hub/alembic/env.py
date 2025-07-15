from logging.config import fileConfig

# Import create_async_engine for explicit async engine creation
from sqlalchemy.ext.asyncio import create_async_engine # <<<--- IMPORTANT CHANGE HERE ---
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection # <<<--- IMPORTANT CHANGE HERE ---
from sqlalchemy import pool

from alembic import context

import os
import sys

# Adjust the path to ensure your application's modules can be imported.
# Assuming 'alembic' folder is at the project root level, and your models
# are in 'backend/app/models.py', your Base is in 'backend/app/database.py'.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.insert(0, project_root)

# Now import your Base and models from their correct paths
# Adjust these imports to match your exact file structure
# Base is typically defined in database.py, not models.py
from backend.app.models import Base # <<<--- IMPORTANT CHANGE HERE ---
from backend.app import models # Assuming your models (like User) are defined in models.py


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# This is crucial: Alembic needs to know about your model definitions
target_metadata = Base.metadata # <<<--- IMPORTANT CHANGE HERE ---

# Set the database URL dynamically or explicitly here.
# Replace with your actual PostgreSQL connection string.
# Example: "postgresql+asyncpg://user:password@localhost:5432/mydatabase"
# You've already set this in your provided code, keeping it as is.
config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://postgres:password@localhost:5432/postgres")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    # This helper function will be called by both online and offline modes
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True # Good for autogenerate to detect type changes
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an AsyncEngine
    and associate an async connection with the context.

    """
    # Get the URL from the config
    connectable_url = config.get_main_option("sqlalchemy.url")

    # Explicitly create an AsyncEngine
    # This is the key change to ensure an async engine is used
    connectable: AsyncEngine = create_async_engine( # <<<--- IMPORTANT CHANGE HERE ---
        connectable_url,
        poolclass=pool.NullPool, # Use NullPool for migrations
    )

    # Use async context manager for the connection
    async with connectable.connect() as connection:
        # Run the synchronous migration logic within the async context
        # This handles the greenlet_spawn requirement
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # This is still necessary to run the async function in a sync context
    import asyncio
    asyncio.run(run_migrations_online())