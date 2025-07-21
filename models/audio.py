from pydantic import BaseModel


class AudioMetadata(BaseModel):
    sample_rate: int
    channels: int
    format: str
    # Add more fields as needed for future NLP or audio processing
