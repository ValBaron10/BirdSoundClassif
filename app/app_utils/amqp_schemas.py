from pydantic import BaseModel



class AMQPMessage(BaseModel):
    ticket_number: str
    

class InferenceMessage(AMQPMessage):
    email: str
    soundfile_minio_path: str
    annotations_minio_path: str
    spectrogram_minio_path: str
    

class FeedbackMessage(InferenceMessage):
    classification_score: float | None = None