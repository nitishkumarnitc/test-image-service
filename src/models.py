from pydantic import BaseModel, Field, constr, conint
from typing import List, Optional

class CreateUploadRequest(BaseModel):
    user_id: constr(min_length=1)
    filename: constr(min_length=1)
    content_type: constr(min_length=3)
    size: conint(ge=1)
    tags: Optional[List[str]] = None

class CompleteUploadRequest(BaseModel):
    user_id: constr(min_length=1)
