from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID

USERS = frozenset({"TEST_USER_A", "TEST_USER_B"})
PURPOSE = "assistant.context"

class LabError(Exception):
    pass

class Denied(LabError):
    pass

class Conflict(LabError):
    pass

class Unavailable(LabError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)

@dataclass(frozen=True)
class TestPrincipal:
    """Injected fixture identity. NOT production authentication or consent."""
    actor: str
    fixture_boundary: str = "NIGHT01_TEST_IDENTITY_V1"

    def check(self):
        if self.actor not in USERS or self.fixture_boundary != "NIGHT01_TEST_IDENTITY_V1":
            raise Denied("INVALID_TEST_PRINCIPAL")

@dataclass(frozen=True)
class Budget:
    max_attempts: int = 2
    timeout_seconds: float = 0.5
    max_context_records: int = 8
    max_context_bytes: int = 16384
    max_output_bytes: int = 32768
    external_provider_usd: int = 0
    tool_calls: int = 0

    def check(self):
        for key, low, high in [("max_attempts",1,2),("max_context_records",1,8),
                               ("max_context_bytes",256,16384),("max_output_bytes",256,32768)]:
            val = getattr(self, key)
            if type(val) is not int or not low <= val <= high:
                raise Denied("INVALID_BUDGET")
        if type(self.timeout_seconds) not in (int,float) or not 0.01 <= self.timeout_seconds <= 2:
            raise Denied("INVALID_TIMEOUT")
        if type(self.external_provider_usd) is not int or self.external_provider_usd != 0:
            raise Denied("EXTERNAL_PROVIDER_BUDGET_MUST_BE_ZERO")
        if type(self.tool_calls) is not int or self.tool_calls != 0:
            raise Denied("TOOLS_DISABLED")

def check_request(principal, data):
    principal.check()
    fields = {"schema_version","request_id","actor_id","topic","question","kind"}
    if type(data) is not dict or set(data) != fields:
        raise Denied("REQUEST_FIELDS")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise Denied("REQUEST_VERSION")
    if data["actor_id"] != principal.actor:
        raise Denied("FORGED_ACTOR")
    try:
        if str(UUID(data["request_id"])) != data["request_id"]:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise Denied("REQUEST_ID") from None
    if data["kind"] not in ("PROJECT_RECALL", "DRAFT_NOTE"):
        raise Denied("UNSUPPORTED_ACTION")
    for key, limit in (("topic",64),("question",2000)):
        if type(data[key]) is not str or not 1 <= len(data[key]) <= limit:
            raise Denied("REQUEST_TEXT")
    return dict(data)
