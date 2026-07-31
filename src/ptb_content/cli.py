"""CLI entry point for ptb-content."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click

from .utils.helpers import ensure_dir, project_root, read_jsonl, write_json


@click.group()
@click.version_option(version="0.2.0")
def main() -> None:
    """PersianToolbox Content Factory — deterministic social media content pipeline."""
    pass


def _reconstruct_brief(data: dict) -> Any:
    """Reconstruct a Brief from serialized dict."""
    from .types import (
        ArtDirection,
        Audience,
        Brief,
        Caption,
        CatalogRecord,
        Category,
        ColorPalette,
        ContentStrategy,
        HookType,
        PsychologyHypothesis,
        RiskDecision,
        RiskLevel,
        TemplateType,
        Typography,
    )

    cr_data = data["catalog_record"]
    cr = CatalogRecord(
        canonical_url=cr_data["canonical_url"],
        title=cr_data["title"],
        summary=cr_data["summary"],
        category=Category(cr_data["category"]),
        source_id=cr_data["source_id"],
        source_hash=cr_data["source_hash"],
        crawled_at=cr_data["crawled_at"],
    )
    cs_data = data["content_strategy"]
    art_data = data["art_direction"]
    return Brief(
        brief_id=data["brief_id"],
        catalog_record=cr,
        audience=Audience(**data["audience"]),
        content_strategy=ContentStrategy(
            angle=cs_data["angle"],
            hook_type=HookType(cs_data["hook_type"]),
            template_type=TemplateType(cs_data["template_type"]),
        ),
        psychology_hypothesis=PsychologyHypothesis(**data["psychology_hypothesis"]),
        caption=Caption(**data["caption"]),
        art_direction=ArtDirection(
            template=TemplateType(art_data["template"]),
            color_palette=ColorPalette(**art_data["color_palette"]),
            typography=Typography(**art_data["typography"]),
            layout_notes=art_data.get("layout_notes", ""),
        ),
        risk_level=RiskLevel(data["risk_level"]),
        risk_decision=RiskDecision(data["risk_decision"]),
    )


@main.command()
@click.option("--pilot", is_flag=True, help="Crawl pilot items (20-30 low-risk tools)")
@click.option("--count", default=30, help="Number of items to crawl")
def crawl(pilot: bool, count: int) -> None:
    """Crawl persiantoolbox.ir for catalog records."""
    from .crawler import Crawler

    crawler = Crawler()
    report = asyncio.run(crawler.crawl_pilot())

    click.echo(f"Crawled {report['items_crawled']} items in {report['duration_seconds']}s")
    if report["errors"]:
        click.echo(f"Errors: {len(report['errors'])}")


@main.command()
@click.option("--count", default=4, help="Number of briefs to generate")
def generate(count: int) -> None:
    """Generate content briefs from catalog records."""
    from .generator import DeterministicGenerator
    from .types import CatalogRecord

    catalog_path = project_root() / "data" / "catalog" / "tools.jsonl"
    if not catalog_path.exists():
        click.echo("No catalog found. Run 'ptb-content crawl' first.")
        sys.exit(1)

    records_data = read_jsonl(catalog_path)
    records = [CatalogRecord.from_dict(r) for r in records_data[:count]]

    gen = DeterministicGenerator()
    briefs = gen.generate_briefs(records)

    output_dir = ensure_dir(project_root() / "outputs" / "briefs")
    for brief in briefs:
        write_json(brief.to_dict(), output_dir / f"{brief.brief_id}.json")

    click.echo(f"Generated {len(briefs)} briefs")


@main.command()
def render() -> None:
    """Render briefs to PNG images."""
    from .renderer import Renderer

    briefs_dir = project_root() / "outputs" / "briefs"
    if not briefs_dir.exists():
        click.echo("No briefs found. Run 'ptb-content generate' first.")
        sys.exit(1)

    renderer = Renderer()
    brief_files = list(briefs_dir.glob("*.json"))

    async def _render_all() -> None:
        for bf in brief_files:
            data = json.loads(bf.read_text(encoding="utf-8"))
            brief = _reconstruct_brief(data)
            results = await renderer.render_all_sizes(brief)
            click.echo(f"Rendered {brief.brief_id}: {list(results.keys())}")

    asyncio.run(_render_all())


@main.command()
def qa() -> None:
    """Run QA checks on generated briefs."""
    from .qa import QAEngine

    briefs_dir = project_root() / "outputs" / "briefs"
    if not briefs_dir.exists():
        click.echo("No briefs found.")
        sys.exit(1)

    qa_engine = QAEngine()
    brief_files = list(briefs_dir.glob("*.json"))
    results = []

    for bf in brief_files:
        data = json.loads(bf.read_text(encoding="utf-8"))
        brief = _reconstruct_brief(data)
        result = qa_engine.run_all(brief)
        results.append(result.to_dict())

    qa_dir = ensure_dir(project_root() / "outputs" / "qa")
    write_json(results, qa_dir / "qa-results.json")

    passed = sum(1 for r in results if r["decision"] == "PASS")
    failed = sum(1 for r in results if r["decision"] == "FAIL")
    escalated = sum(1 for r in results if r["decision"] == "ESCALATE")
    click.echo(f"QA: {passed} PASS, {failed} FAIL, {escalated} ESCALATE")


@main.command()
def benchmark() -> None:
    """Run provider benchmark."""
    from .providers import ProviderBenchmark

    bench = ProviderBenchmark()
    results = asyncio.run(bench.run_benchmark())
    bench.save_report()

    for r in results:
        status = "✓" if r["reachable"] else "✗"
        click.echo(
            f"  {status} {r['provider']}: reachable={r['reachable']}, latency={r['latency_p50_ms']}ms"
        )


@main.command()
@click.option("--install", "install_cron", is_flag=True, help="Install cron jobs")
@click.option("--uninstall", "uninstall_cron", is_flag=True, help="Remove cron jobs")
@click.option("--dry-run", "dry_run", is_flag=True, help="Validate without installing")
def schedule(install_cron: bool, uninstall_cron: bool, dry_run: bool) -> None:
    """Manage scheduler (cron jobs)."""
    from .scheduler import LocalScheduler

    scheduler = LocalScheduler()

    if dry_run:
        report = scheduler.dry_run()
        click.echo("Scheduler dry-run:")
        click.echo(f"  Project: {report['project_dir']}")
        click.echo(f"  Python: {report['python_path']}")
        click.echo(f"  Log dir: {report['log_dir']}")
        click.echo(f"  All valid: {report['all_valid']}")
        for name, job in report["jobs"].items():
            status = "✓" if job["valid"] else "✗"
            click.echo(f"  {status} {name}: {job['schedule']} — {job['description']}")
        return

    if uninstall_cron:
        success = scheduler.uninstall_cron()
        click.echo(f"Uninstall: {'SUCCESS' if success else 'FAILED'}")
        return

    if install_cron:
        success = scheduler.install_cron()
        click.echo(f"Install: {'SUCCESS' if success else 'FAILED'}")
        return

    # Default: show info
    info = scheduler.get_schedule_info()
    click.echo("Scheduled jobs:")
    for name, job in info["jobs"].items():
        click.echo(f"  {name}: {job['description']} ({job['schedule']})")
    click.echo(f"\nLog directory: {info['log_dir']}")
    click.echo(f"Disable: {info['disable_command']}")


@main.command()
@click.argument("brief_id")
@click.option("--reviewer", default="admin", help="Reviewer name")
def approve(brief_id: str, reviewer: str) -> None:
    """Approve a brief for publishing."""
    from .publisher import ApprovalGate
    from .types import Approval

    gate = ApprovalGate()

    # Load brief
    brief_path = project_root() / "outputs" / "briefs" / f"{brief_id}.json"
    if not brief_path.exists():
        click.echo(f"Brief not found: {brief_id}")
        sys.exit(1)

    data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief = _reconstruct_brief(data)

    # Compute checksum from file to avoid reconstruction drift
    checksum = gate.compute_checksum_from_file(brief_path)

    # Create approval
    approval = Approval(
        brief_id=brief_id,
        approved=True,
        reviewer=reviewer,
        notes=f"Approved via CLI by {reviewer}",
        version=brief.version,
    )
    gate.save_approval(approval, checksum)

    click.echo(f"Approved: {brief_id}")
    click.echo(f"  Reviewer: {reviewer}")
    click.echo(f"  Version: {brief.version}")
    click.echo(f"  Checksum: {checksum[:16]}...")
    click.echo(f"  Risk: {brief.risk_level.value} / {brief.risk_decision.value}")


@main.command()
@click.argument("brief_id")
def revoke(brief_id: str) -> None:
    """Revoke approval for a brief."""
    from .publisher import ApprovalGate

    gate = ApprovalGate()
    revoked = gate.revoke_approval(brief_id)
    if revoked:
        click.echo(f"Revoked: {brief_id}")
    else:
        click.echo(f"No approval found: {brief_id}")


@main.command()
@click.argument("brief_id")
def publish(brief_id: str) -> None:
    """Attempt to publish a brief (mock — never actually publishes)."""
    from .publisher import ApprovalGate, MockPublisher
    from .qa import QAEngine

    gate = ApprovalGate()
    publisher = MockPublisher()

    # Load brief
    brief_path = project_root() / "outputs" / "briefs" / f"{brief_id}.json"
    if not brief_path.exists():
        click.echo(f"Brief not found: {brief_id}")
        sys.exit(1)

    data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief = _reconstruct_brief(data)

    # Run QA
    qa_engine = QAEngine()
    qa_result = qa_engine.run_all(brief)

    # Attempt publish (use file-based checksum for consistency)
    result = publisher.publish(brief, gate, qa_result, brief_path=brief_path)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@main.command()
def report() -> None:
    """Generate final reports."""
    from datetime import UTC, datetime

    briefs_dir = project_root() / "outputs" / "briefs"
    catalog_path = project_root() / "data" / "catalog" / "tools.jsonl"

    report_data: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "catalog_items": 0,
        "briefs_generated": 0,
        "qa_results": {},
    }

    if catalog_path.exists():
        report_data["catalog_items"] = len(read_jsonl(catalog_path))

    if briefs_dir.exists():
        report_data["briefs_generated"] = len(list(briefs_dir.glob("*.json")))

    qa_path = project_root() / "outputs" / "qa" / "qa-results.json"
    if qa_path.exists():
        qa_data = json.loads(qa_path.read_text(encoding="utf-8"))
        report_data["qa_results"] = {
            "total": len(qa_data),
            "passed": sum(1 for r in qa_data if r["decision"] == "PASS"),
            "failed": sum(1 for r in qa_data if r["decision"] == "FAIL"),
            "escalated": sum(1 for r in qa_data if r["decision"] == "ESCALATE"),
        }

    write_json(report_data, project_root() / "reports" / "catalog-report.json")
    click.echo(json.dumps(report_data, indent=2, ensure_ascii=False))


# --- Semi-Automated Instagram Commands ---


@main.command()
@click.argument("brief_id")
def export_instagram(brief_id: str) -> None:
    """Export a brief as a publish-ready Instagram bundle."""
    from .publisher.instagram_export import InstagramExporter
    from .publisher.manual_queue import ManualQueue

    # Load brief
    brief_path = project_root() / "outputs" / "briefs" / f"{brief_id}.json"
    if not brief_path.exists():
        click.echo(f"Brief not found: {brief_id}")
        sys.exit(1)

    data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief = _reconstruct_brief(data)

    # Export bundle
    exporter = InstagramExporter()
    try:
        bundle_dir = exporter.export(brief, brief_path=brief_path)
    except Exception as e:
        click.echo(f"Export failed: {e}")
        sys.exit(1)

    # Add to manual queue
    from .publisher import ApprovalGate

    gate = ApprovalGate()
    loaded = gate.load_approval(brief_id)
    approval_id = loaded[0].brief_id if loaded else ""
    checksum = gate.compute_checksum_from_file(brief_path)

    queue = ManualQueue()
    try:
        queue.add(
            brief_id=brief_id,
            approval_id=approval_id,
            image_checksum=checksum,
            bundle_path=str(bundle_dir),
        )
    except Exception as e:
        click.echo(f"Queue add failed: {e}")
        sys.exit(1)

    click.echo(f"Exported: {bundle_dir}")
    click.echo(f"  Brief: {brief_id}")
    click.echo(f"  Files: {len(list(bundle_dir.iterdir()))}")
    click.echo("  Queue: READY_FOR_REVIEW")


@main.command("manual-queue")
@click.option("--state", default=None, help="Filter by state")
def manual_queue_list(state: str | None) -> None:
    """List items in the manual publish queue."""
    from .publisher.manual_queue import ManualQueue

    queue = ManualQueue()
    if state:
        items = queue.list_by_state(state)
    else:
        items = queue.list_all()

    if not items:
        click.echo("Queue is empty.")
        return

    click.echo(f"{'Brief ID':<25} {'State':<35} {'Created'}")
    click.echo("-" * 85)
    for item in items:
        click.echo(f"{item['brief_id']:<25} {item['state']:<35} {item['created_at'][:19]}")
    click.echo(f"\nTotal: {len(items)}")


@main.command("manual-scheduled")
@click.argument("brief_id")
@click.option("--at", required=True, help="ISO8601 schedule time")
def manual_scheduled(brief_id: str, at: str) -> None:
    """Mark a brief as manually scheduled in Instagram."""
    from .publisher.manual_queue import ManualQueue

    queue = ManualQueue()
    try:
        queue.transition(
            brief_id,
            "MANUALLY_SCHEDULED",
            scheduled_at=at,
        )
        click.echo(f"Scheduled: {brief_id} at {at}")
    except Exception as e:
        click.echo(f"Failed: {e}")
        sys.exit(1)


@main.command("manual-published")
@click.argument("brief_id")
@click.option("--permalink", required=True, help="Instagram post URL")
def manual_published(brief_id: str, permalink: str) -> None:
    """Confirm a brief was published on Instagram."""
    from .publisher.manual_queue import ManualQueue
    from .types import utcnow

    queue = ManualQueue()
    try:
        queue.transition(
            brief_id,
            "PUBLISHED_CONFIRMED",
            permalink=permalink,
            published_at=utcnow(),
        )
        click.echo(f"Published: {brief_id}")
        click.echo(f"  Permalink: {permalink}")
    except Exception as e:
        click.echo(f"Failed: {e}")
        sys.exit(1)


@main.command("manual-cancel")
@click.argument("brief_id")
def manual_cancel(brief_id: str) -> None:
    """Cancel a brief in the manual queue."""
    from .publisher.manual_queue import ManualQueue

    queue = ManualQueue()
    try:
        queue.transition(brief_id, "CANCELLED")
        click.echo(f"Cancelled: {brief_id}")
    except Exception as e:
        click.echo(f"Failed: {e}")
        sys.exit(1)


@main.command()
def status() -> None:
    """Show current project status."""
    briefs_dir = project_root() / "outputs" / "briefs"
    golden_dir = project_root() / "outputs" / "golden"
    approvals_dir = project_root() / "data" / "approvals"
    bundles_dir = project_root() / "outputs" / "bundles"
    baselines_dir = Path("tests/baselines")

    briefs_count = len(list(briefs_dir.glob("*.json"))) if briefs_dir.exists() else 0
    golden_count = len(list(golden_dir.glob("*.json"))) if golden_dir.exists() else 0
    approvals_count = len(list(approvals_dir.glob("*.json"))) if approvals_dir.exists() else 0
    bundles_count = len(list(bundles_dir.glob("*/manifest.json"))) if bundles_dir.exists() else 0
    pngs = (
        sum(1 for _ in (project_root() / "outputs").rglob("*.png"))
        if (project_root() / "outputs").exists()
        else 0
    )
    baselines = (
        len(list((baselines_dir / "snapshot-test").glob("*.png"))) if baselines_dir.exists() else 0
    )

    # Manual queue stats
    from .publisher.manual_queue import ManualQueue

    queue = ManualQueue()
    queue_total = queue.count()
    queue_scheduled = queue.count("MANUALLY_SCHEDULED")
    queue_published = queue.count("PUBLISHED_CONFIRMED")

    click.echo("=== PersianToolbox Content Factory ===")
    click.echo(f"  Briefs:      {briefs_count}")
    click.echo(f"  Golden:      {golden_count}")
    click.echo(f"  Approvals:   {approvals_count}")
    click.echo(f"  Bundles:     {bundles_count}")
    click.echo(f"  PNGs:        {pngs}")
    click.echo(f"  Snapshots:   {baselines}")
    click.echo(
        f"  Queue:       {queue_total} total, {queue_scheduled} scheduled, {queue_published} published"
    )
    click.echo("  API:         BLOCKED_BY_META_DEVELOPER_VERIFICATION")
    click.echo("  Mode:        SEMI_AUTOMATED")


if __name__ == "__main__":
    main()
