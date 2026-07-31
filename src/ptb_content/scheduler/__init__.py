"""Local scheduler for content factory jobs.

Features:
- Dry-run mode (validate without installing)
- Lockfile to prevent overlapping runs
- Absolute paths for Python, working dir, log dir
- Disable/uninstall support
- Exit code non-zero on failure
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..utils.helpers import ensure_dir, project_root, write_json

LOCKFILE_DIR = Path("/tmp/ptb-content-factory")  # noqa: S108


class LocalScheduler:
    """Schedule recurring jobs using system cron or systemd timer."""

    JOBS = {
        "catalog-refresh": {
            "description": "Refresh tool catalog from persiantoolbox.ir",
            "schedule": "0 3 * * 0",  # Sunday 3 AM
            "command": "ptb-content crawl --pilot",
        },
        "weekly-generation": {
            "description": "Generate weekly content briefs",
            "schedule": "0 3 * * 1",  # Monday 3 AM
            "command": "ptb-content generate --count 4",
        },
        "weekly-render": {
            "description": "Render weekly content PNGs",
            "schedule": "0 4 * * 1",  # Monday 4 AM (after generation)
            "command": "ptb-content render",
        },
        "weekly-qa-report": {
            "description": "Generate weekly QA report",
            "schedule": "0 5 * * 2",  # Tuesday 5 AM
            "command": "ptb-content qa --report",
        },
    }

    def __init__(self) -> None:
        self.project_dir = project_root()
        self.log_dir = ensure_dir(self.project_dir / "logs")
        self.python_path = sys.executable

    def _lockfile_path(self, job_name: str) -> Path:
        """Get lockfile path for a job."""
        return LOCKFILE_DIR / f"{job_name}.lock"

    def acquire_lock(self, job_name: str) -> bool:
        """Acquire lockfile. Returns False if already locked."""
        LOCKFILE_DIR.mkdir(parents=True, exist_ok=True)
        lockfile = self._lockfile_path(job_name)
        if lockfile.exists():
            return False
        lockfile.write_text(str(os.getpid()), encoding="utf-8")
        return True

    def release_lock(self, job_name: str) -> None:
        """Release lockfile."""
        lockfile = self._lockfile_path(job_name)
        if lockfile.exists():
            lockfile.unlink()

    def generate_cron_entries(self) -> list[str]:
        """Generate cron entries for all jobs with absolute paths."""
        entries = []
        for name, job in self.JOBS.items():
            lock_cmd = f"test ! -f /tmp/ptb-content-factory/{name}.lock || exit 0"
            lock_touch = f"touch /tmp/ptb-content-factory/{name}.lock"
            lock_rm = f"rm -f /tmp/ptb-content-factory/{name}.lock"
            workdir = f"cd {self.project_dir}"
            run = f"{self.python_path} -m ptb_content.cli {job['command'].replace('ptb-content ', '')}"
            log = f">> {self.log_dir}/{name}.log 2>&1"
            # Chain: check lock → acquire → run → release
            full_cmd = f"{lock_cmd} && {lock_touch} && {workdir} && {run} {log}; {lock_rm}"
            entries.append(f"{job['schedule']} {full_cmd}")
        return entries

    def dry_run(self) -> dict[str, Any]:
        """Validate cron entries without installing. Returns report."""
        entries = self.generate_cron_entries()
        report: dict[str, Any] = {
            "dry_run": True,
            "project_dir": str(self.project_dir),
            "python_path": self.python_path,
            "log_dir": str(self.log_dir),
            "jobs": {},
            "all_valid": True,
        }

        for i, (name, job) in enumerate(self.JOBS.items()):
            entry = entries[i] if i < len(entries) else "MISSING"
            # Validate entry structure
            valid = (
                entry.startswith(("0 ", "1 ", "2 ", "3 ", "4 ", "5 "))
                and self.project_dir.as_posix() in entry
                and self.python_path in entry
                and str(self.log_dir) in entry
            )
            report["jobs"][name] = {
                "schedule": job["schedule"],
                "description": job["description"],
                "command": job["command"],
                "cron_entry": entry,
                "valid": valid,
            }
            if not valid:
                report["all_valid"] = False

        return report

    def install_cron(self) -> bool:
        """Install cron jobs (Linux/macOS)."""
        try:
            existing = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True
            )
            existing_entries = existing.stdout if existing.returncode == 0 else ""

            marker = "# ptb-content-factory"
            new_entries = self.generate_cron_entries()
            cron_lines = [f"{entry} {marker}" for entry in new_entries]

            lines = existing_entries.split("\n")
            filtered = [line for line in lines if marker not in line and line.strip()]

            full_cron = "\n".join(filtered + cron_lines) + "\n"

            proc = subprocess.run(
                ["crontab", "-"], input=full_cron, text=True, capture_output=True
            )
            return proc.returncode == 0
        except Exception:
            return False

    def uninstall_cron(self) -> bool:
        """Remove all ptb-content-factory cron entries."""
        try:
            existing = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True
            )
            existing_entries = existing.stdout if existing.returncode == 0 else ""

            marker = "# ptb-content-factory"
            lines = existing_entries.split("\n")
            filtered = [line for line in lines if marker not in line and line.strip()]

            full_cron = "\n".join(filtered) + "\n" if filtered else ""

            proc = subprocess.run(
                ["crontab", "-"], input=full_cron, text=True, capture_output=True
            )
            return proc.returncode == 0
        except Exception:
            return False

    def disable_job(self, job_name: str) -> bool:
        """Disable a specific job by commenting it out."""
        if job_name not in self.JOBS:
            return False
        try:
            existing = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True
            )
            existing_entries = existing.stdout if existing.returncode == 0 else ""
            marker = "# ptb-content-factory"

            lines = existing_entries.split("\n")
            new_lines = []
            for line in lines:
                if marker in line and self.JOBS[job_name]["command"] in line:
                    new_lines.append(f"# {line}")  # Comment out
                else:
                    new_lines.append(line)

            full_cron = "\n".join(new_lines) + "\n"
            proc = subprocess.run(
                ["crontab", "-"], input=full_cron, text=True, capture_output=True
            )
            return proc.returncode == 0
        except Exception:
            return False

    def get_schedule_info(self) -> dict[str, Any]:
        """Get information about scheduled jobs."""
        return {
            "jobs": self.JOBS,
            "cron_entries": self.generate_cron_entries(),
            "log_dir": str(self.log_dir),
            "python_path": self.python_path,
            "project_dir": str(self.project_dir),
            "note": "Jobs require system cron. If computer is off, jobs will not run.",
            "disable_command": "crontab -l | grep -v 'ptb-content-factory' | crontab -",
            "uninstall_command": "ptb-content schedule --uninstall",
        }

    def save_schedule(self) -> None:
        """Save schedule configuration."""
        schedule_path = self.project_dir / "reports" / "schedule.json"
        write_json(self.get_schedule_info(), schedule_path)
