from pydantic import BaseModel, Field
from datetime import datetime
import os

class FileSchema(BaseModel):
    filetype: str
    original_filename: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def generate_filename(self) -> str:
        """Generate a filename based on filetype and timestamp."""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S%f")
        return f"{timestamp_str}_{self.original_filename}"

    def generate_annotation_filename(self) -> str:
        """Generate an annotation filename based on filetype and timestamp."""
        timestamp_str = self.timestamp.strftime("%Y%m%d%H%M%S%f")
        base_name = os.path.splitext(self.original_filename)[0]
        return f"{timestamp_str}_{base_name}_annot.txt"

class AMQPMessage(BaseModel):
    ticket_number: str
    

class ForwardMessage(AMQPMessage):
    email: str
    soundfile_minio_path: str
    

class FeedbackMessage(ForwardMessage):
    annotations_minio_path: str
    