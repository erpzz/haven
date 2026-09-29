"""IP-01 wire contract. Full vectors are preconditions, never bearer authority."""
from __future__ import annotations
import hashlib
import json
import math
import time
import uuid
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime

CANONICALIZATION = 'ip01.json.sorted-utf8.v1'
PROFILE = 'ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT'
LIMITS = {'people': 2, 'sources': 32, 'grants': 16, 'edges': 128, 'depth': 16,
          'metadata_bytes': 65536, 'output_bytes': 262144}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def raw_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def uid(prefix='r') -> str:
    return prefix + '_' + uuid.uuid4().hex


class Denied(Exception):
    def __init__(self, code: str, status=409, message=None, operation_id=None):
        self.code, self.status = code, status
        self.message = message or code.replace('_', ' ').capitalize()
        self.operation_id = operation_id
        super().__init__(code)


class UnknownCommit(Denied):
    def __init__(self, operation_id=None):
        super().__init__('COMMIT_UNKNOWN', 503, 'Commit outcome is uncertain. Reconcile using the same operation key; do not replay.', operation_id)


class Wire(BaseModel):
    model_config = ConfigDict(extra='forbid')


class GrantDependency(Wire):
    id: str
    revision: int = Field(ge=1)
    revocation_epoch: int = Field(ge=1)


class SourceDependency(Wire):
    id: str
    revision: int = Field(ge=1)
    sha256: str
    lineage_epoch: int = Field(ge=1)
    authenticity_epoch: int = Field(ge=1)


class CancelScope(Wire):
    scope_id: str
    epoch: int = Field(ge=1)


class AuthorityVector(Wire):
    vector_version: Literal['ip01.authority.v1']
    authority_instance_epoch: str
    restore_epoch: int = Field(ge=1)
    policy_ref: str
    purpose_definition_ref: str
    rights_policy_refs: list[str]
    principal_ref: str
    session_revision: str
    device_binding_revision: str
    device_epoch: int = Field(ge=1)
    service_capability_revision: str
    tool_catalog_digest: str
    grant_dependencies: list[GrantDependency] = Field(max_length=16)
    source_dependencies: list[SourceDependency] = Field(max_length=32)
    subject_scope_revision: str
    participant_area_scope_revision: str
    job_ref: str
    lease_fence: int = Field(ge=1)
    cancel_scope_epochs: list[CancelScope]
    destination_ref: str
    destination_epoch: int = Field(ge=1)
    audience_revision: str
    route_profile_revision: str
    provider_data_policy_revision: Literal['NOT_APPLICABLE_LOCAL_ONLY']
    dependency_closure_digest: str
    canonicalization_version: Literal['ip01.json.sorted-utf8.v1']


class SessionRequest(Wire):
    person: Literal['A', 'B']


class NoteRequest(Wire):
    title: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=16000)
    parents: list[str] = Field(default_factory=list, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)


class NoteEdit(Wire):
    expected_revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=16000)
    parents: list[str] | None = Field(default=None, max_length=32)


class RevisionRequest(Wire):
    expected_revision: int = Field(ge=1)


class GrantRequest(Wire):
    recipient: Literal['A', 'B']
    purpose: Literal['answer'] = 'answer'
    expires_at: AwareDatetime
    max_uses: int | None = Field(default=None, ge=1, le=100)
    idempotency_key: str = Field(min_length=1, max_length=128)
    profile: Literal['ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT'] = PROFILE


class DraftRequest(Wire):
    kind: Literal['draft', 'task']
    text: str = Field(min_length=1, max_length=16000)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DraftEdit(Wire):
    expected_revision: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=16000)
    done: bool = False


class AnswerRequest(Wire):
    question: str = Field(min_length=1, max_length=2000)
    route: Literal['deterministic', 'model'] = 'deterministic'
    image_source_id: str | None = None
    source_ids: list[str] | None = Field(default=None, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=128)
    destination_ref: str


class ConsumeRequest(Wire):
    release_id: str
    output_digest: str
    destination_ref: str
    nonce: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ObservationRequest(Wire):
    release_id: str
    consumption_id: str
    output_digest: str
    destination_ref: str
    nonce: str
    idempotency_key: str = Field(min_length=1, max_length=128)
    kind: Literal['DISPLAY_REPORTED', 'DELIVERY_UNKNOWN', 'STOP_REPORTED', 'SENT_UNACKNOWLEDGED']

