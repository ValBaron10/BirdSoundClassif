from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base

class Bird(Base):
    __tablename__ = 'birds'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class ServiceCall(Base):
    __tablename__ = 'service_calls'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    audio_path: Mapped[str] = mapped_column(String, nullable=False)
    audio_length: Mapped[float] = mapped_column(Float, nullable=True)
    inference_results: Mapped[list["InferenceResult"]] = relationship(
        "InferenceResult", back_populates="service_call"
    )
    user_inputs: Mapped[list["UserInput"]] = relationship(
        "UserInput", back_populates="service_call"
    )

class InferenceResult(Base):
    __tablename__ = 'inference_results'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_call_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('service_calls.id', ondelete='CASCADE')
    )
    annotation_path: Mapped[str] = mapped_column(String, nullable=False)
    spectrogram_path: Mapped[str] = mapped_column(String, nullable=False)
    bird_id: Mapped[int] = mapped_column(Integer, nullable=True)
    classification_score: Mapped[float] = mapped_column(Float, nullable=True)
    service_call: Mapped["ServiceCall"] = relationship(
        "ServiceCall", back_populates="inference_results"
    )

class UserInput(Base):
    __tablename__ = 'user_inputs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_call_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('service_calls.id', ondelete='CASCADE')
    )
    annotation_path: Mapped[str] = mapped_column(String, nullable=True)
    bird_id: Mapped[int] = mapped_column(Integer, nullable=True)
    service_call: Mapped["ServiceCall"] = relationship(
        "ServiceCall", back_populates="user_inputs"
    )