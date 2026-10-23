from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    file_name: str
    storage_path: str | None
    file_type: str
    extracted_text: str | None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)