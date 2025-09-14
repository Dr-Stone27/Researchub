import os
import sys

# Add the backend directory to the Python path to allow importing app.models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from app.models import Base # This should be the Base/DeclarativeBase from your app.models file

# Define a dummy in-memory SQLite engine to get the DDL.
# We don't actually connect to PostgreSQL here, just use a compatible dialect.
engine = create_engine("postgresql+asyncpg://postgres:password@localhost:5432/postgres")

# Iterate through all tables defined in your Base.metadata
print("-- SQL to create tables based on your models.py --")
print("-- Execute this in pgAdmin for your database --\n")
for table in Base.metadata.sorted_tables:
    print(CreateTable(table).compile(engine))
    print(";\n") # Add semicolon for easier execution in pgAdmin

print("-- End of SQL schema generation --")