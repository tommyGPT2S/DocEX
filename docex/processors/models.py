from datetime import datetime, UTC
from sqlalchemy import Column, String, Boolean, JSON, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from uuid import uuid4

from docex.db.connection import get_base

Base = get_base()

# Processor and ProcessingOperation models have been moved to db/models.py 