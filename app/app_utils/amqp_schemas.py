from pydantic import BaseModel



class AMQPMessage(BaseModel):
    ticket_number: str
    
    def generate_ticket_number(self):
        self.ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number
    

class InferenceMessage(AMQPMessage):
    email: str
    soundfile_minio_path: str
    annotations_minio_path: str
    spectrogram_minio_path: str
    

class FeedbackMessage(InferenceMessage):
    classification_score: float