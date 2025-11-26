from sqlalchemy import Boolean, Column, Integer, String, ForeignKey

from database import Base

class test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, index=True)
    is_active = Column(Boolean, default=True)