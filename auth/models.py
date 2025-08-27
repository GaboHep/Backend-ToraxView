from sqlalchemy import Column, Integer, String, Text, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # "radiologo" o "administrador"
    registros = relationship(
        "Registro",
        back_populates="user",
        # si vas a depender del CASCADE del DB, usa passive_deletes=True
        passive_deletes=True
    )


class Registro(Base):
    __tablename__ = "registros"

    key = Column(String, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # <— clave
        nullable=False
    )
    inference_date = Column(Date)
    birth_date = Column(Date)
    gender = Column(String)
    city = Column(String)
    parish = Column(String)
    canton = Column(String)
    precision = Column(Float)
    resultados = Column(Text)   # JSON serializado como string
    feedback = Column(Text)
    image = Column(Text)        # base64 de la imagen

    user = relationship("User", back_populates="registros", passive_deletes=True)