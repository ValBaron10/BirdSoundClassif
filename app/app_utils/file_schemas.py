from pydantic import BaseModel, Field
from datetime import datetime
import os
from pydantic import EmailStr, field_validator
import uuid
from fastapi import UploadFile
from pydantic import ValidationError

class UploadRecord(BaseModel):
    email: EmailStr
    file: UploadFile
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('file')
    def validate_file(cls, v):
        if v.content_type not in ["audio/wav"]:
            raise ValueError("Le fichier doit être un fichier audio .wav ou .mp3")
        return v

    def generate_filename(self) -> str:
        """Generate a filename based on filetype and timestamp."""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S%f")
        return f"{timestamp_str}_{self.file.filename}"

    def generate_annotation_filename(self) -> str:
        """Generate an annotation filename based on filetype and timestamp."""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S%f")
        base_name = os.path.splitext(self.file.filename)[0]
        return f"{timestamp_str}_{base_name}_annot.txt"
    
    def generate_spectrogram_filename(self) -> str:
        """Generate a spectrogram filename based on filetype and timestamp."""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S%f")
        base_name = os.path.splitext(self.file.filename)[0]
        return f"{timestamp_str}_{base_name}_spectro.png"

    def get_audio_path(self, root_folder: str) -> str:
        """Generate the path for the audio file."""
        return f"audio/{self.generate_filename()}"

    def get_annotation_path(self, root_folder: str) -> str:
        """Generate the path for the annotation file."""
        return f"annotations/{self.generate_annotation_filename()}"

    def get_spectrogram_path(self, root_folder: str) -> str:
        """Generate the path for the spectrogram file."""
        return f"spectrograms/{self.generate_spectrogram_filename()}"
    
       
