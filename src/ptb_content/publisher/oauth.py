"""OAuth CLI commands for Meta Instagram authorization."""

from __future__ import annotations

import json
import secrets
import webbrowser

import click


@click.group()
def oauth() -> None:
    """Manage Meta Instagram OAuth tokens."""
    pass


@oauth.command("auth-url")
def auth_url() -> None:
    """Generate the Facebook OAuth authorization URL."""
    from .settings import MetaInstagramSettings

    settings = MetaInstagramSettings()
    if not settings.app_id:
        click.echo("Error: META_INSTAGRAM_APP_ID not set")
        raise SystemExit(1)

    state = secrets.token_urlsafe(32)
    scopes = "instagram_basic,instagram_content_publish,pages_read_engagement"

    url = (
        f"https://www.facebook.com/v21.0/dialog/oauth"
        f"?client_id={settings.app_id}"
        f"&redirect_uri={settings.oauth_redirect_uri}"
        f"&scope={scopes}"
        f"&response_type=code"
        f"&state={state}"
    )

    click.echo("Open this URL in your browser:\n")
    click.echo(url)
    click.echo(f"\nState (save this): {state}")

    try:
        webbrowser.open(url)
        click.echo("\nOpened in default browser.")
    except Exception:
        pass


@oauth.command("exchange-code")
@click.argument("code")
def exchange_code(code: str) -> None:
    """Exchange an authorization code for a short-lived access token."""
    import httpx

    from .settings import MetaInstagramSettings

    settings = MetaInstagramSettings()
    if not settings.app_id or not settings.app_secret:
        click.echo("Error: META_INSTAGRAM_APP_ID and META_INSTAGRAM_APP_SECRET required")
        raise SystemExit(1)

    resp = httpx.post(
        f"{settings.host_url}/v21.0/oauth/access_token",
        data={
            "client_id": settings.app_id,
            "client_secret": settings.app_secret,
            "redirect_uri": settings.oauth_redirect_uri,
            "code": code,
        },
        timeout=30.0,
    )

    if resp.status_code != 200:
        click.echo(f"Error: {resp.status_code} — {resp.text[:200]}")
        raise SystemExit(1)

    data = resp.json()
    click.echo(json.dumps(data, indent=2))

    if "access_token" in data:
        click.echo(f"\nShort-lived token: {data['access_token'][:20]}...")
        click.echo("Use 'ptb-content oauth exchange-long-lived' to get a long-lived token.")


@oauth.command("exchange-long-lived")
@click.argument("short_lived_token")
def exchange_long_lived(short_lived_token: str) -> None:
    """Exchange a short-lived token for a long-lived token (60 days)."""
    import httpx

    from .settings import MetaInstagramSettings

    settings = MetaInstagramSettings()
    if not settings.app_id or not settings.app_secret:
        click.echo("Error: META_INSTAGRAM_APP_ID and META_INSTAGRAM_APP_SECRET required")
        raise SystemExit(1)

    resp = httpx.get(
        f"{settings.host_url}/v21.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.app_id,
            "client_secret": settings.app_secret,
            "fb_exchange_token": short_lived_token,
        },
        timeout=30.0,
    )

    if resp.status_code != 200:
        click.echo(f"Error: {resp.status_code} — {resp.text[:200]}")
        raise SystemExit(1)

    data = resp.json()
    click.echo(json.dumps(data, indent=2))

    if "access_token" in data:
        click.echo(f"\nLong-lived token: {data['access_token'][:20]}...")
        click.echo("Set this as META_INSTAGRAM_ACCESS_TOKEN in your .env file.")


@oauth.command("verify")
def verify() -> None:
    """Verify the current access token and show account info."""
    import httpx

    from .settings import MetaInstagramSettings

    settings = MetaInstagramSettings()
    if not settings.access_token:
        click.echo("Error: META_INSTAGRAM_ACCESS_TOKEN not set")
        raise SystemExit(1)

    resp = httpx.get(
        f"{settings.host_url}/{settings.api_version}/me",
        params={"access_token": settings.access_token, "fields": "id,name"},
        timeout=30.0,
    )

    if resp.status_code != 200:
        click.echo(f"Error: {resp.status_code} — {resp.text[:200]}")
        raise SystemExit(1)

    data = resp.json()
    click.echo(json.dumps(data, indent=2))


@oauth.command("token-status")
def token_status() -> None:
    """Check token expiry and permissions."""
    import httpx

    from .settings import MetaInstagramSettings

    settings = MetaInstagramSettings()
    if not settings.access_token:
        click.echo("Error: META_INSTAGRAM_ACCESS_TOKEN not set")
        raise SystemExit(1)

    resp = httpx.get(
        f"{settings.host_url}/{settings.api_version}/me",
        params={
            "access_token": settings.access_token,
            "fields": "id,name",
        },
        timeout=30.0,
    )

    if resp.status_code != 200:
        click.echo(f"Token is invalid or expired: {resp.text[:200]}")
        raise SystemExit(1)

    data = resp.json()
    click.echo("Token is valid.")
    click.echo(f"  Account ID: {data.get('id')}")
    click.echo(f"  Name: {data.get('name')}")

    # Check publishing limit
    if settings.instagram_account_id:
        resp2 = httpx.get(
            f"{settings.host_url}/{settings.api_version}/{settings.instagram_account_id}/content_publishing_limit",
            params={"access_token": settings.access_token},
            timeout=30.0,
        )
        if resp2.status_code == 200:
            limit_data = resp2.json().get("data", [{}])
            if limit_data:
                click.echo("\nPublishing limit (24h):")
                click.echo(f"  Config: {limit_data[0].get('config', {}).get('quota_total', 'N/A')}")
                click.echo(f"  Usage: {limit_data[0].get('quota_usage', 'N/A')}")


@oauth.command("disconnect")
def disconnect() -> None:
    """Revoke the current access token (disconnect app)."""
    click.echo("To revoke the token:")
    click.echo("1. Go to https://www.facebook.com/settings/apps")
    click.echo("2. Find your app and click 'Remove'")
    click.echo("Or call: DELETE /me/permissions?access_token=<TOKEN>")
