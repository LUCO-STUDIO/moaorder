#!/usr/bin/env python3
"""
Phase runner for moaorder tasks.
Reads index.json, runs each phase sequentially via Claude Code CLI,
updates status, and exits with appropriate code.

Exit codes:
  0 - All phases completed successfully
  1 - Error during phase execution
  2 - Phase blocked (needs user intervention)
"""

import json
import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path


def load_index(task_dir: Path) -> dict:
    index_path = task_dir / "index.json"
    with open(index_path) as f:
        return json.load(f)


def save_index(task_dir: Path, index: dict):
    index["updated_at"] = datetime.now(timezone.utc).isoformat()
    index_path = task_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def run_phase(task_dir: Path, phase_num: int, project_dir: Path) -> int:
    """Run a single phase. Returns exit code (0=success, 1=error, 2=blocked)."""
    phase_file = task_dir / f"phase-{phase_num:02d}.md"
    if not phase_file.exists():
        print(f"Phase file not found: {phase_file}")
        return 1

    prompt = phase_file.read_text()

    print(f"\n{'='*60}")
    print(f"  Running Phase {phase_num}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--dangerously-skip-permissions",
                "-p", prompt,
            ],
            cwd=str(project_dir),
            timeout=1800,  # 30 minutes per phase
        )
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"Phase {phase_num} timed out after 30 minutes")
        return 1
    except FileNotFoundError:
        print("Claude CLI not found. Make sure 'claude' is in PATH.")
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python run-phases.py <task-dir>")
        print("Example: python run-phases.py tasks/moaorder-mvp")
        sys.exit(1)

    project_dir = Path(__file__).parent.parent.resolve()
    task_dir = project_dir / sys.argv[1]

    if not task_dir.exists():
        print(f"Task directory not found: {task_dir}")
        sys.exit(1)

    index = load_index(task_dir)
    total = index["total_phases"]
    start_phase = index.get("current_phase", 0) + 1

    if index["status"] == "completed":
        print(f"Task '{index['name']}' is already completed.")
        sys.exit(0)

    index["status"] = "in_progress"
    save_index(task_dir, index)

    for phase_num in range(start_phase, total + 1):
        index["current_phase"] = phase_num
        save_index(task_dir, index)

        exit_code = run_phase(task_dir, phase_num, project_dir)

        if exit_code == 2:
            # Blocked
            index["status"] = "blocked"
            if not index.get("blocked_reason"):
                index["blocked_reason"] = f"Phase {phase_num} needs user intervention"
            save_index(task_dir, index)
            print(f"\nPhase {phase_num} blocked. User intervention needed.")
            sys.exit(2)
        elif exit_code != 0:
            # Error
            index["status"] = "failed"
            index["error_message"] = f"Phase {phase_num} failed with exit code {exit_code}"
            save_index(task_dir, index)
            print(f"\nPhase {phase_num} failed.")
            sys.exit(1)

        print(f"\nPhase {phase_num} completed successfully.")

    # All phases done
    index["status"] = "completed"
    save_index(task_dir, index)
    print(f"\nAll {total} phases completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
