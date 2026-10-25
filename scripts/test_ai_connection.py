"""
Zero AI Reusable Connection Diagnostic Command.
Tests live authentication, inspects model catalog, tests completions,
selects a working model, and safely updates .env configuration.

Usage:
  python scripts/test_ai_connection.py
  python scripts/test_ai_connection.py --no-update
  python scripts/test_ai_connection.py --base-url https://agent-router.net/aggregate/openai/v1
"""

import sys
import argparse
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import get_settings
from app.ai.connection_tester import AIConnectionTester


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero AI Provider Connection Diagnostic")
    parser.add_argument(
        "--base-url",
        default="https://agent-router.net/aggregate/openai/v1",
        help="Target OpenAI-compatible API base URL",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Run diagnostics without updating .env configuration",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=5,
        help="Maximum candidate models to test completions on",
    )
    args = parser.parse_args()

    # Load active settings
    settings = get_settings(reload=True)
    api_key = settings.ai_api_key

    print(f"\n[INITIATING] Zero AI Provider Connection Test...")
    print(f"Target Base URL: {args.base_url}")

    tester = AIConnectionTester(
        api_base=args.base_url,
        api_key=api_key,
        timeout=settings.ai_timeout,
        env_path=PROJECT_ROOT / ".env",
    )

    report = tester.run_full_diagnostic(
        preferred_model=settings.ai_model,
        target_verified_count=2,
        max_models_to_test=args.max_candidates,
        update_env_on_success=not args.no_update,
    )

    # Print clean terminal report
    print("\n" + report.format_terminal_report() + "\n")

    # Save sanitized diagnostic report
    reports_dir = PROJECT_ROOT / "logs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "ai_connection_report.json"
    try:
        report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"[REPORT SAVED] Diagnostic report saved to: {report_file}")
    except Exception as e:
        print(f"[REPORT WARNING] Failed to save report JSON: {e}")

    # Return 0 if verified, 1 if auth or completion failed
    if report.auth_result.success and report.verified_models:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
