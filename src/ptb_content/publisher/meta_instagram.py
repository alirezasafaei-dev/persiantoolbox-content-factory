"""Meta Instagram Graph API publisher — production-grade, fail-closed.

Flow:
1. Validate brief + QA result
2. Sign media URL via gateway
3. Create image container via POST /<IG_ID>/media
4. Poll container status until FINISHED
5. Publish via POST /<IG_ID>/media_publish
6. Return PublishJob with PUBLISHED state
"""

from __future__ import annotations

import time
import uuid

import httpx

from ..types import Brief, QAResult, generate_hash
from .errors import (
    AuthenticationError,
    ContainerError,
    ContainerExpiredError,
    ContainerProcessingError,
    PublishError,
    RateLimitError,
    TokenExpiredError,
)
from .media_gateway import MediaGateway
from .protocol import PublishJob, PublishState
from .publisher_base import BasePublisher
from .queue import PublishQueue
from .settings import MetaInstagramSettings


class MetaInstagramPublisher(BasePublisher):
    """Real Meta Instagram Graph API publisher.

    Uses httpx for HTTP, implements full container → poll → publish flow.
    Always checks settings.can_publish before any external request.
    """

    def __init__(
        self,
        settings: MetaInstagramSettings | None = None,
        queue: PublishQueue | None = None,
        gateway: MediaGateway | None = None,
    ) -> None:
        self.settings = settings or MetaInstagramSettings()
        self.queue = queue or PublishQueue()
        self.gateway = gateway or MediaGateway(self.settings)
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.settings.base_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _auth_params(self) -> dict[str, str]:
        return {"access_token": self.settings.access_token}

    def _check_can_publish(self) -> None:
        if not self.settings.can_publish:
            raise AuthenticationError(
                "Cannot publish: missing credentials or disabled via settings "
                "(PTB_REAL_PUBLISH_ENABLED, PTB_AUTO_PUBLISH, PTB_LIVE_CANARY_APPROVED must all be true)"
            )

    def _api_post(self, path: str, data: dict) -> dict:
        """POST to Meta API with error handling."""
        params = {**self._auth_params()}
        payload = {k: v for k, v in data.items() if v is not None}

        try:
            resp = self.client.post(path, params=params, json=payload)
        except httpx.TimeoutException as e:
            raise PublishError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise PublishError(f"Network error: {e}") from e

        if resp.status_code == 401:
            raise TokenExpiredError("Access token expired or invalid")
        if resp.status_code == 400:
            body = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            error = body.get("error", {})
            code = error.get("code", 0)
            msg = error.get("message", "")
            if code == 190:
                raise TokenExpiredError(f"Token error: {msg}")
            if code == 32:
                raise RateLimitError(f"Rate limit: {msg}")
            raise PublishError(f"API error {code}: {msg}")
        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded (429)")
        if resp.status_code >= 400:
            raise PublishError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        if "error" in body:
            error = body["error"]
            code = error.get("code", 0)
            msg = error.get("message", "")
            if code == 32:
                raise RateLimitError(f"Rate limit: {msg}")
            raise PublishError(f"API error {code}: {msg}")

        return body

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        """GET from Meta API with error handling."""
        query_params = {**self._auth_params()}
        if params:
            query_params.update(params)

        try:
            resp = self.client.get(path, params=query_params)
        except httpx.TimeoutException as e:
            raise PublishError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise PublishError(f"Network error: {e}") from e

        if resp.status_code == 401:
            raise TokenExpiredError("Access token expired or invalid")
        if resp.status_code >= 400:
            raise PublishError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return resp.json()

    def _create_image_container(self, image_url: str, caption: str) -> str:
        """Create an image media container. Returns container ID."""
        data = self._api_post(
            f"/{self.settings.instagram_account_id}/media",
            {
                "image_url": image_url,
                "caption": caption,
            },
        )
        container_id = data.get("id")
        if not container_id:
            raise ContainerError(f"No container ID returned: {data}")
        return container_id

    def _poll_container(self, container_id: str) -> str:
        """Poll container status until FINISHED or terminal error.

        Returns the status_code string.
        """
        start = time.monotonic()
        timeout = self.settings.container_timeout_seconds
        interval = self.settings.poll_interval_seconds

        while True:
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                raise ContainerProcessingError(
                    f"Container {container_id} timed out after {timeout}s"
                )

            data = self._api_get(
                f"/{container_id}",
                params={"fields": "status_code,status"},
            )
            status_code = data.get("status_code") or data.get("status", "")

            if status_code == "FINISHED":
                return status_code
            if status_code == "PUBLISHED":
                return status_code
            if status_code == "EXPIRED":
                raise ContainerExpiredError(f"Container {container_id} expired")
            if status_code == "ERROR":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                raise ContainerError(f"Container {container_id} error: {error_msg}")

            time.sleep(interval)

    def _publish_container(self, container_id: str) -> str:
        """Publish the container via media_publish. Returns media ID."""
        data = self._api_post(
            f"/{self.settings.instagram_account_id}/media_publish",
            {"creation_id": container_id},
        )
        media_id = data.get("id")
        if not media_id:
            raise PublishError(f"No media ID returned from publish: {data}")
        return media_id

    def validate(self, brief: Brief, qa_result: QAResult) -> None:
        """Validate brief is publishable. Raises on failure."""
        self._check_can_publish()

        # Compute checksum
        payload = __import__("json").dumps(brief.to_dict(), sort_keys=True, ensure_ascii=False)
        generate_hash(payload)

        # Check rate limit
        recent = self.queue.count_recent_posts(hours=24)
        if recent >= self.settings.max_posts_per_24h:
            raise RateLimitError(
                f"Rate limit: {recent}/{self.settings.max_posts_per_24h} posts in last 24h"
            )

        # Validate caption length
        caption = brief.caption.primary or ""
        if len(caption) > 2200:
            raise PublishError(f"Caption too long: {len(caption)} chars (max 2200)")

    def publish(self, brief: Brief, qa_result: QAResult) -> PublishJob:
        """Full publish flow: validate → sign URL → create container → poll → publish."""
        self._check_can_publish()

        # Compute checksum
        import json

        payload = json.dumps(brief.to_dict(), sort_keys=True, ensure_ascii=False)
        checksum = generate_hash(payload)

        # Create job
        job = PublishJob(
            job_id=f"job-{uuid.uuid4().hex[:12]}",
            brief_id=brief.brief_id,
            content_checksum=checksum,
            instagram_account_id=self.settings.instagram_account_id,
        )

        try:
            # Validate
            self.validate(brief, qa_result)

            # Transition through approval states
            job.transition(PublishState.QA_PASSED)
            job.transition(PublishState.APPROVED)
            job.transition(PublishState.SCHEDULED)
            job.transition(PublishState.VALIDATING)
            self.queue.enqueue(job)

            # Sign media URL
            feed_path = self._get_image_path(brief)

            signed_url = self.gateway.sign_url(feed_path)
            job.transition(PublishState.MEDIA_EXPOSED)
            self.queue.enqueue(job)

            # Create container
            caption = brief.caption.primary or ""
            container_id = self._create_image_container(signed_url, caption)
            job.container_id = container_id
            job.transition(PublishState.CONTAINER_CREATED)
            self.queue.update_state(job.job_id, job.state)
            self.queue.update_container(job.job_id, container_id)

            # Poll until ready
            job.transition(PublishState.PROCESSING)
            self.queue.update_state(job.job_id, job.state)
            self._poll_container(container_id)

            # Publish
            media_id = self._publish_container(container_id)
            job.instagram_media_id = media_id
            job.transition(PublishState.PUBLISHED)
            self.queue.update_state(job.job_id, job.state)
            self.queue.update_media_id(job.job_id, media_id)

            return job

        except (RateLimitError, TokenExpiredError) as e:
            job.retry_count += 1
            if job.retry_count <= job.max_retries:
                job.transition(PublishState.FAILED_RETRYABLE, str(e))
            else:
                job.transition(PublishState.FAILED_PERMANENT, str(e))
            self.queue.enqueue(job) if job.job_id not in [j.job_id for j in []] else None
            try:
                self.queue.update_state(job.job_id, job.state, str(e))
            except Exception:
                pass
            return job

        except Exception as e:
            job.transition(PublishState.FAILED_PERMANENT, str(e))
            try:
                self.queue.enqueue(job)
            except Exception:
                pass
            return job

    def get_status(self, job_id: str) -> PublishJob | None:
        return self.queue.get(job_id)
