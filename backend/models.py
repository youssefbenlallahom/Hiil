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
    action: Literal['request_correction', 'reviewed', 'flag']
    note: str = Field(default='', max_length=2000)
    expected_updated_at: str | None = None
    checklist: list[Literal['identity', 'documents', 'declaration']] = Field(default_factory=list)

class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    field: str | None = Field(default=None, max_length=80)

class Citation(BaseModel):
    source_id: str
    quote: str = Field(min_length=1)

class GroundedAnswer(BaseModel):
    text: str
    citations: list[Citation]
    insufficient_evidence: bool

class ConversationMessage(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=100)

class ConversationResponse(BaseModel):
    reply: str
    status: str
    collected: dict[str, str] = Field(default_factory=dict)
    progress: dict = Field(default_factory=dict)
    justifications: list[dict] = Field(default_factory=list)
    form_path: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    mode: Literal['llm', 'guided', 'unavailable'] = 'guided'
    error_code: str | None = None
    can_generate: bool = False
