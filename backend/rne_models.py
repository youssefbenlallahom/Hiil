"""Typed conversation state. Only reviewed data can reach the PDF renderer."""
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

FieldKey = Literal['company_id', 'declarant_name', 'declarant_id', 'representative_name', 'representative_id', 'email', 'phone', 'same_person']
Modification = Literal['seat_address', 'branch_address', 'other']


class Evidence(BaseModel):
    origin: Literal['user', 'document']
    reference_id: str
    quote: str
    page: int | None = None


class Value(BaseModel):
    value: str
    evidence: list[Evidence] = Field(default_factory=list)
    confirmed: bool = False


class Message(BaseModel):
    id: str
    role: Literal['user', 'assistant']
    text: str
    at: str
    source_ids: list[str] = Field(default_factory=list)


class RneState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    revision: int = 0
    values: dict[str, Value] = Field(default_factory=dict)
    modification: Modification | None = None
    modification_confirmed: bool = False
    candidates: list[Modification] = Field(default_factory=list)
    reason: str = ''
    messages: list[Message] = Field(default_factory=list)
    cin_document_id: str | None = None
    cin_status: Literal['missing', 'uploaded', 'extracted', 'needs_review'] = 'missing'
    pending_question: str = ''
    stage: str = 'intent'
    pdf_revision: int | None = None
    processed_requests: list[str] = Field(default_factory=list)


class Update(BaseModel):
    key: FieldKey
    value: str = Field(min_length=1, max_length=180)
    quote: str = Field(min_length=1, max_length=3000)


class Proposal(BaseModel):
    reply: str = Field(min_length=1, max_length=4000)
    updates: list[Update] = Field(default_factory=list, max_length=8)
    modification: Modification | None = None
    intent_quote: str = ''
    candidates: list[Modification] = Field(default_factory=list, max_length=3)
    reason: str = Field(default='', max_length=1000)
    source_ids: list[str] = Field(default_factory=list)


class RneRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=80, pattern=r'^[a-zA-Z0-9-]+$')
    action: Literal['message', 'edit', 'select_modification', 'confirm', 'prepare', 'extract_cin', 'use_evidence'] = 'message'
    message: str = Field(default='', max_length=3000)
    key: FieldKey | None = None
    value: str = Field(default='', max_length=180)
    modification: Modification | None = None
    document_id: str = Field(default='', max_length=80)


class IdentityField(BaseModel):
    key: Literal['first_name', 'last_name', 'cin_number']
    value: str = Field(min_length=1, max_length=120)
    page: int = Field(ge=1)
    evidence: str = Field(min_length=1, max_length=2000)


class IdentityExtraction(BaseModel):
    is_cin: bool
    fields: list[IdentityField] = Field(max_length=3)
