"""Tests for publisher module — protocol, state machine, queue, gateway, meta publisher."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from ptb_content.publisher.errors import (
    AuthenticationError,
    IdempotencyViolationError,
    MediaGatewayError,
    PublishError,
    RateLimitError,
    TokenExpiredError,
)
from ptb_content.publisher.media_gateway import MediaGateway
from ptb_content.publisher.protocol import (
    _VALID_TRANSITIONS,
    InvalidStateTransitionError,
    PublishJob,
    PublishState,
    can_transition,
)
from ptb_content.publisher.queue import PublishQueue
from ptb_content.publisher.settings import MetaInstagramSettings
from ptb_content.types import (
    ArtDirection,
    Audience,
    Brief,
    Caption,
    CatalogRecord,
    Category,
    CheckResult,
    CheckStatus,
    ColorPalette,
    ContentStrategy,
    HookType,
    PsychologyHypothesis,
    QADecision,
    QAResult,
    RiskDecision,
    RiskLevel,
    TemplateType,
    Typography,
)

# --- Fixtures ---


def _make_brief(brief_id: str = "test-brief-001") -> Brief:
    return Brief(
        brief_id=brief_id,
        catalog_record=CatalogRecord(
            canonical_url="https://example.com/test",
            title="Test Tool",
            summary="A test tool",
            category=Category.TOOL_DEMO,
            source_id="test-001",
            source_hash="abc123",
            crawled_at="2026-01-01T00:00:00+00:00",
        ),
        audience=Audience(segment="developers", pain_point="slow", desire="fast"),
        content_strategy=ContentStrategy(
            angle="test angle",
            hook_type=HookType.DIRECT,
            template_type=TemplateType.TOOL_DEMO,
        ),
        psychology_hypothesis=PsychologyHypothesis(
            principle="social proof",
            expected_effect="trust",
        ),
        caption=Caption(primary="Test caption for testing #test"),
        art_direction=ArtDirection(
            template=TemplateType.TOOL_DEMO,
            color_palette=ColorPalette(),
            typography=Typography(),
        ),
        risk_level=RiskLevel.LOW,
        risk_decision=RiskDecision.AUTO_APPROVE,
    )


def _make_qa_result(
    brief_id: str = "test-brief-001", decision: QADecision = QADecision.PASS
) -> QAResult:
    return QAResult(
        brief_id=brief_id,
        checks={"length": CheckResult(status=CheckStatus.PASS, score=1.0, details="ok")},
        decision=decision,
    )


def _make_settings(**overrides) -> MetaInstagramSettings:
    defaults = {
        "app_id": "test-app-id",
        "app_secret": "test-app-secret",
        "access_token": "test-access-token",
        "instagram_account_id": "12345678",
        "auto_publish": True,
        "live_canary_approved": True,
        "real_publish_enabled": True,
        "media_gateway_secret": "test-hmac-secret-32-chars-long!!",
        "media_gateway_host": "https://media.example.com",
    }
    defaults.update(overrides)
    return MetaInstagramSettings(**defaults)


@pytest.fixture
def tmp_queue(tmp_path):
    db_path = tmp_path / "test-queue.db"
    q = PublishQueue(db_path)
    yield q
    q.close()


# --- State Machine Tests ---


class TestPublishState:
    def test_initial_state(self):
        assert PublishState.DRAFT.value == "DRAFT"

    def test_valid_transition(self):
        assert can_transition(PublishState.DRAFT, PublishState.QA_PASSED)
        assert can_transition(PublishState.QA_PASSED, PublishState.APPROVED)
        assert can_transition(PublishState.APPROVED, PublishState.SCHEDULED)

    def test_invalid_transition(self):
        assert not can_transition(PublishState.DRAFT, PublishState.PUBLISHED)
        assert not can_transition(PublishState.PUBLISHED, PublishState.DRAFT)

    def test_terminal_states_have_no_transitions(self):
        assert len(_VALID_TRANSITIONS[PublishState.PUBLISHED]) == 0
        assert len(_VALID_TRANSITIONS[PublishState.REVOKED]) == 0
        assert len(_VALID_TRANSITIONS[PublishState.CANCELLED]) == 0


class TestPublishJob:
    def test_create_job(self):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        assert job.state == PublishState.DRAFT
        assert job.idempotency_key == "publish:brief-001:abc123:123456"

    def test_transition_success(self):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        job.transition(PublishState.QA_PASSED)
        assert job.state == PublishState.QA_PASSED

    def test_transition_invalid_raises(self):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        with pytest.raises(InvalidStateTransitionError):
            job.transition(PublishState.PUBLISHED)

    def test_transition_sets_published_at(self):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        # DRAFT → QA_PASSED → APPROVED → SCHEDULED → VALIDATING → MEDIA_EXPOSED → CONTAINER_CREATED → PROCESSING → PUBLISHED
        for state in [
            PublishState.QA_PASSED,
            PublishState.APPROVED,
            PublishState.SCHEDULED,
            PublishState.VALIDATING,
            PublishState.MEDIA_EXPOSED,
            PublishState.CONTAINER_CREATED,
            PublishState.PROCESSING,
            PublishState.PUBLISHED,
        ]:
            job.transition(state)
        assert job.published_at is not None

    def test_to_dict_roundtrip(self):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        d = job.to_dict()
        job2 = PublishJob.from_dict(d)
        assert job2.job_id == job.job_id
        assert job2.state == job.state
        assert job2.idempotency_key == job.idempotency_key


# --- Queue Tests ---


class TestPublishQueue:
    def test_enqueue_and_get(self, tmp_queue):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        tmp_queue.enqueue(job)
        loaded = tmp_queue.get("job-001")
        assert loaded is not None
        assert loaded.brief_id == "brief-001"

    def test_idempotency_violation(self, tmp_queue):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        tmp_queue.enqueue(job)
        job2 = PublishJob(
            job_id="job-002",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        with pytest.raises(IdempotencyViolationError):
            tmp_queue.enqueue(job2)

    def test_get_nonexistent(self, tmp_queue):
        assert tmp_queue.get("nonexistent") is None

    def test_update_state(self, tmp_queue):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        tmp_queue.enqueue(job)
        updated = tmp_queue.update_state("job-001", PublishState.QA_PASSED)
        assert updated.state == PublishState.QA_PASSED

    def test_list_by_state(self, tmp_queue):
        for i in range(3):
            job = PublishJob(
                job_id=f"job-{i:03d}",
                brief_id=f"brief-{i:03d}",
                content_checksum=f"checksum-{i}",
                instagram_account_id="123456",
            )
            tmp_queue.enqueue(job)
            if i < 2:
                tmp_queue.update_state(f"job-{i:03d}", PublishState.QA_PASSED)

        drafts = tmp_queue.list_by_state(PublishState.DRAFT)
        assert len(drafts) == 1
        passed = tmp_queue.list_by_state(PublishState.QA_PASSED)
        assert len(passed) == 2

    def test_count_recent_posts(self, tmp_queue):
        assert tmp_queue.count_recent_posts() == 0

    def test_get_by_idempotency_key(self, tmp_queue):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )
        tmp_queue.enqueue(job)
        found = tmp_queue.get_by_idempotency_key(job.idempotency_key)
        assert found is not None
        assert found.job_id == "job-001"


# --- Media Gateway Tests ---


class TestMediaGateway:
    def test_enabled_when_configured(self):
        settings = _make_settings()
        gw = MediaGateway(settings)
        assert gw.enabled

    def test_disabled_when_no_secret(self):
        settings = _make_settings(media_gateway_secret="")
        gw = MediaGateway(settings)
        assert not gw.enabled

    def test_disabled_when_no_host(self):
        settings = _make_settings(media_gateway_host="")
        gw = MediaGateway(settings)
        assert not gw.enabled

    def test_sign_url(self, tmp_path):
        settings = _make_settings()
        gw = MediaGateway(settings)
        fake_file = tmp_path / "test.png"
        fake_file.write_bytes(b"fake png data")

        url = gw.sign_url(fake_file)
        assert "token=" in url
        assert "expires=" in url
        assert "path=" in url

    def test_validate_token_valid(self, tmp_path):
        settings = _make_settings()
        gw = MediaGateway(settings)
        fake_file = tmp_path / "test.png"
        fake_file.write_bytes(b"fake png data")

        url = gw.sign_url(fake_file)
        valid, error = gw.validate_token(url)
        assert valid
        assert error is None

    def test_validate_token_expired(self, tmp_path):
        settings = _make_settings()
        gw = MediaGateway(settings)
        fake_file = tmp_path / "test.png"
        fake_file.write_bytes(b"fake png data")

        url = gw.sign_url(fake_file, expires_at=time.time() - 10)
        valid, error = gw.validate_token(url)
        assert not valid
        assert "expired" in error.lower()

    def test_validate_token_bad_hmac(self, tmp_path):
        settings = _make_settings()
        gw = MediaGateway(settings)
        fake_file = tmp_path / "test.png"
        fake_file.write_bytes(b"fake png data")

        url = gw.sign_url(fake_file)
        # Tamper with the token
        url = url.replace("token=", "token=badtoken&orig=")
        valid, error = gw.validate_token(url)
        assert not valid

    def test_validate_token_missing_params(self):
        settings = _make_settings()
        gw = MediaGateway(settings)
        valid, error = gw.validate_token("https://media.example.com/media?foo=bar")
        assert not valid
        assert "missing" in error.lower()

    def test_get_local_path(self, tmp_path):
        settings = _make_settings()
        gw = MediaGateway(settings)
        fake_file = tmp_path / "test.png"
        fake_file.write_bytes(b"fake png data")

        url = gw.sign_url(fake_file)
        path = gw.get_local_path(url)
        assert path == fake_file

    def test_sign_url_raises_when_disabled(self, tmp_path):
        settings = _make_settings(media_gateway_secret="")
        gw = MediaGateway(settings)
        with pytest.raises(MediaGatewayError):
            gw.sign_url(tmp_path / "test.png")


# --- Settings Tests ---


class TestSettings:
    def test_defaults_are_fail_closed(self):
        settings = MetaInstagramSettings()
        assert not settings.auto_publish
        assert not settings.live_canary_approved
        assert not settings.real_publish_enabled
        assert settings.publisher_backend == "mock"

    def test_can_publish_requires_all_flags(self):
        settings = _make_settings()
        assert settings.can_publish

    def test_can_publish_blocked_by_auto_publish(self):
        settings = _make_settings(auto_publish=False)
        assert not settings.can_publish

    def test_can_publish_blocked_by_canary(self):
        settings = _make_settings(live_canary_approved=False)
        assert not settings.can_publish

    def test_can_publish_blocked_by_real_publish(self):
        settings = _make_settings(real_publish_enabled=False)
        assert not settings.can_publish

    def test_has_credentials(self):
        settings = _make_settings()
        assert settings.has_credentials

    def test_missing_credentials(self):
        settings = _make_settings(app_id="")
        assert not settings.has_credentials


# --- Meta Instagram Publisher Tests ---


class TestMetaInstagramPublisher:
    def test_validate_checks_can_publish(self):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings(auto_publish=False)
        publisher = MetaInstagramPublisher(settings=settings)
        brief = _make_brief()
        qa = _make_qa_result()

        with pytest.raises(AuthenticationError):
            publisher.validate(brief, qa)

    def test_validate_caption_too_long(self):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings()
        publisher = MetaInstagramPublisher(settings=settings)
        brief = _make_brief()
        brief.caption.primary = "x" * 2201
        qa = _make_qa_result()

        with pytest.raises(PublishError, match="Caption too long"):
            publisher.validate(brief, qa)

    def test_publish_returns_job(self, tmp_path):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings()
        mock_queue = MagicMock()
        mock_queue.count_recent_posts.return_value = 0
        publisher = MetaInstagramPublisher(settings=settings, queue=mock_queue)
        brief = _make_brief()
        qa = _make_qa_result()

        # No image file exists, so it should fail gracefully
        with patch.object(publisher, "_check_can_publish"):
            result = publisher.publish(brief, qa)
            assert isinstance(result, PublishJob)
            assert result.state in (
                PublishState.FAILED_PERMANENT,
                PublishState.PUBLISHED,
            )

    def test_publish_with_mocked_api(self, tmp_path):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings()
        mock_queue = MagicMock()
        mock_queue.count_recent_posts.return_value = 0
        publisher = MetaInstagramPublisher(settings=settings, queue=mock_queue)
        brief = _make_brief()
        qa = _make_qa_result()

        # Create a fake image
        image_dir = tmp_path / brief.brief_id
        image_dir.mkdir(parents=True)
        (image_dir / "feed-1080x1080.png").write_bytes(b"fake png")

        # Mock the gateway
        mock_gateway = MagicMock()
        mock_gateway.sign_url.return_value = "https://media.example.com/signed.png"
        publisher.gateway = mock_gateway

        # Mock the API calls and image path
        with (
            patch.object(publisher, "_check_can_publish"),
            patch.object(
                publisher, "_get_image_path", return_value=image_dir / "feed-1080x1080.png"
            ),
            patch.object(publisher, "_create_image_container", return_value="container-123"),
            patch.object(publisher, "_poll_container", return_value="FINISHED"),
            patch.object(publisher, "_publish_container", return_value="media-456"),
        ):
            result = publisher.publish(brief, qa)

        assert result.state == PublishState.PUBLISHED
        assert result.instagram_media_id == "media-456"
        assert result.container_id == "container-123"

    def test_publish_handles_rate_limit(self, tmp_path):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings()
        mock_queue = MagicMock()
        mock_queue.count_recent_posts.return_value = 0
        publisher = MetaInstagramPublisher(settings=settings, queue=mock_queue)
        brief = _make_brief()
        qa = _make_qa_result()

        mock_gateway = MagicMock()
        mock_gateway.sign_url.return_value = "https://media.example.com/signed.png"
        publisher.gateway = mock_gateway

        with (
            patch.object(publisher, "_check_can_publish"),
            patch.object(publisher, "_get_image_path", return_value=tmp_path / "fake.png"),
            patch.object(
                publisher, "_create_image_container", side_effect=RateLimitError("Rate limited")
            ),
        ):
            result = publisher.publish(brief, qa)
            assert result.state == PublishState.FAILED_RETRYABLE
            assert "Rate limited" in (result.error_message or "")

    def test_publish_handles_token_expired(self, tmp_path):
        from ptb_content.publisher.meta_instagram import MetaInstagramPublisher

        settings = _make_settings()
        mock_queue = MagicMock()
        mock_queue.count_recent_posts.return_value = 0
        publisher = MetaInstagramPublisher(settings=settings, queue=mock_queue)
        brief = _make_brief()
        qa = _make_qa_result()

        mock_gateway = MagicMock()
        mock_gateway.sign_url.return_value = "https://media.example.com/signed.png"
        publisher.gateway = mock_gateway

        with (
            patch.object(publisher, "_check_can_publish"),
            patch.object(publisher, "_get_image_path", return_value=tmp_path / "fake.png"),
            patch.object(
                publisher, "_create_image_container", side_effect=TokenExpiredError("Token expired")
            ),
        ):
            result = publisher.publish(brief, qa)
            assert result.state == PublishState.FAILED_RETRYABLE
            assert "Token expired" in (result.error_message or "")


# --- Integration Test: Full Publish Flow ---


class TestFullPublishFlow:
    def test_full_flow_with_queue(self, tmp_queue):
        job = PublishJob(
            job_id="job-001",
            brief_id="brief-001",
            content_checksum="abc123",
            instagram_account_id="123456",
        )

        # Enqueue
        tmp_queue.enqueue(job)
        assert tmp_queue.get("job-001") is not None

        # State transitions
        tmp_queue.update_state("job-001", PublishState.QA_PASSED)
        tmp_queue.update_state("job-001", PublishState.APPROVED)
        tmp_queue.update_state("job-001", PublishState.SCHEDULED)
        tmp_queue.update_state("job-001", PublishState.VALIDATING)
        tmp_queue.update_state("job-001", PublishState.MEDIA_EXPOSED)
        tmp_queue.update_container("job-001", "container-123")
        tmp_queue.update_state("job-001", PublishState.CONTAINER_CREATED)
        tmp_queue.update_state("job-001", PublishState.PROCESSING)
        tmp_queue.update_state("job-001", PublishState.PUBLISHED)
        tmp_queue.update_media_id("job-001", "media-456")

        final = tmp_queue.get("job-001")
        assert final.state == PublishState.PUBLISHED
        assert final.instagram_media_id == "media-456"
        assert final.container_id == "container-123"
        assert final.published_at is not None
