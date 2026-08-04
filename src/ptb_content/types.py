"""Core types for the PersianToolbox Content Factory."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class Category(str, Enum):
    TOOL_DEMO = "tool-demo"
    PDF_TUTORIAL = "pdf-tutorial"
    PERSIAN_TEXT = "persian-text"
    PROFESSIONAL = "professional"
    PRIVACY = "privacy"
    FINANCIAL = "financial"
    SEASONAL = "seasonal"
    COMPARISON = "comparison"


class RiskTag(str, Enum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    TAX = "tax"
    SECURITY = "security"
    PRIVACY = "privacy"
    TESTIMONIAL = "testimonial"
    COMPARATIVE = "comparative"
    STATISTICAL = "statistical"
    MEDICAL = "medical"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ESCALATE = "ESCALATE"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


class QADecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ESCALATE = "ESCALATE"


class HookType(str, Enum):
    DIRECT = "direct"
    EDUCATIONAL = "educational"
    CURIOSITY = "curiosity"
    PROBLEM_SOLUTION = "problem-solution"
    BEFORE_AFTER = "before-after"


class TemplateType(str, Enum):
    TOOL_DEMO = "tool-demo"
    STEP_BY_STEP = "step-by-step"
    COMMON_MISTAKE = "common-mistake"
    PRIVACY_TRUST = "privacy-trust"
    PROFESSIONAL_SEASONAL = "professional-seasonal"


class ClaimVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNVERIFIABLE = "UNVERIFIABLE"
    DISPUTED = "DISPUTED"


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}-{uid}" if prefix else uid


def generate_hash(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def utcnow() -> str:
    """Current UTC time in ISO format."""
    return datetime.now(UTC).isoformat()


@dataclass
class Claim:
    text: str
    source_id: str
    verifiable: bool
    confidence: float = 0.5
    verdict: ClaimVerdict = ClaimVerdict.UNVERIFIED
    evidence_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HTTPMetadata:
    status_code: int = 0
    content_type: str = ""
    content_length: int = 0
    last_modified: str | None = None
    etag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CatalogRecord:
    canonical_url: str
    title: str
    summary: str
    category: Category
    source_id: str
    source_hash: str
    crawled_at: str
    claims: list[Claim] = field(default_factory=list)
    risk_tags: list[RiskTag] = field(default_factory=list)
    http_metadata: HTTPMetadata = field(default_factory=HTTPMetadata)
    verified_at: str | None = None
    expires_at: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    visible_text_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["risk_tags"] = [t.value for t in self.risk_tags]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogRecord:
        data = data.copy()
        data["category"] = Category(data["category"])
        data["risk_tags"] = [RiskTag(t) for t in data.get("risk_tags", [])]
        data["claims"] = [Claim(**c) for c in data.get("claims", [])]
        if "http_metadata" in data:
            data["http_metadata"] = HTTPMetadata(**data["http_metadata"])
        return cls(**data)


@dataclass
class Audience:
    segment: str
    pain_point: str
    desire: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentStrategy:
    angle: str
    hook_type: HookType
    template_type: TemplateType

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["hook_type"] = self.hook_type.value
        d["template_type"] = self.template_type.value
        return d


@dataclass
class PsychologyHypothesis:
    principle: str
    expected_effect: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Caption:
    primary: str
    variants: dict[str, str] = field(default_factory=dict)
    alt_text: str = ""
    cta: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ColorPalette:
    primary: str = "#2563EB"
    secondary: str = "#1E40AF"
    accent: str = "#F59E0B"
    background: str = "#FFFFFF"
    text: str = "#1E293B"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Typography:
    heading_font: str = "Vazirmatn"
    body_font: str = "Vazirmatn"
    heading_size_px: int = 28
    body_size_px: int = 16

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArtDirection:
    template: TemplateType
    color_palette: ColorPalette
    typography: Typography
    layout_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["template"] = self.template.value
        return d


@dataclass
class Brief:
    brief_id: str
    catalog_record: CatalogRecord
    audience: Audience
    content_strategy: ContentStrategy
    psychology_hypothesis: PsychologyHypothesis
    caption: Caption
    art_direction: ArtDirection
    risk_level: RiskLevel
    risk_decision: RiskDecision
    utm: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        d = {
            "brief_id": self.brief_id,
            "catalog_record": self.catalog_record.to_dict(),
            "audience": self.audience.to_dict(),
            "content_strategy": self.content_strategy.to_dict(),
            "psychology_hypothesis": self.psychology_hypothesis.to_dict(),
            "caption": self.caption.to_dict(),
            "art_direction": self.art_direction.to_dict(),
            "risk_level": self.risk_level.value,
            "risk_decision": self.risk_decision.value,
            "utm": self.utm,
            "created_at": self.created_at,
            "version": self.version,
        }
        return d


@dataclass
class CheckResult:
    status: CheckStatus
    score: float
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class QAResult:
    brief_id: str
    checks: dict[str, CheckResult]
    decision: QADecision
    failure_reasons: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "brief_id": self.brief_id,
            "checks": {k: v.to_dict() for k, v in self.checks.items()},
            "decision": self.decision.value,
            "failure_reasons": self.failure_reasons,
            "generated_at": self.generated_at,
        }
        return d


@dataclass
class Approval:
    brief_id: str
    approved: bool
    reviewer: str | None = None
    notes: str = ""
    conditions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PublishRecord:
    brief_id: str
    ready_to_publish: bool
    blocks: list[str] = field(default_factory=list)
    target_account: str | None = None
    utm: dict[str, str] = field(default_factory=dict)
    media_ids: list[str] = field(default_factory=list)
    idempotency_key: str = field(default_factory=lambda: generate_id("pub"))
    created_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
