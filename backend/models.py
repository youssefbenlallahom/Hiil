from typing import Literal
from pydantic import BaseModel, Field

class ExtractedField(BaseModel):
    key: Literal['company_name', 'company_id', 'new_address', 'current_address', 'representative', 'decision_date']
    value: str
    page: int = Field(ge=1)
    evidence: str

class Extraction(BaseModel):
    kind: Literal['declaration', 'decision', 'registry', 'other']
    fields: list[ExtractedField]

class Answer(BaseModel):
    text: str
    source_ids: list[str]

class NewCase(BaseModel):
    company: str = Field(min_length=2, max_length=120)

class Confirmation(BaseModel):
    key: Literal['company_name', 'company_id', 'new_address', 'current_address', 'representative', 'decision_date']
    value: str = Field(min_length=1, max_length=500)

class Review(BaseModel):
    action: Literal['request_correction', 'reviewed']
    note: str = Field(default='', max_length=2000)

class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

class DocumentReview(BaseModel):
    kind: Literal['declaration', 'decision', 'registry', 'other']
    fields: list[ExtractedField] = Field(max_length=30)

class CorrectionResponse(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
