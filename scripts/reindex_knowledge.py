"""
Zero AI Knowledge Reindexing CLI Command.
Performs incremental or full forced reindexing of all supported documents in Knowledge/.

Usage:
  python scripts/reindex_knowledge.py
  python scripts/reindex_knowledge.py --force
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.paths import get_knowledge_dir
from app.knowledge.service import get_knowledge_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Zero AI Knowledge Reindexer")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-extraction and reindexing of all documents, ignoring modification times and hashes",
    )
    args = parser.parse_args()

    print("=" * 70)
    print(" ZERO AI // KNOWLEDGE REINDEXING ENGINE")
    print("=" * 70)

    service = get_knowledge_service()
    kb_dir = get_knowledge_dir()
    print(f"Target Directory: {kb_dir}")
    print(f"Mode: {'FULL REINDEX (FORCED)' if args.force else 'INCREMENTAL (CHANGED & NEW ONLY)'}\n")

    try:
        report = service.sync_and_index(force_all=args.force)

        print("-" * 70)
        print(" REINDEXING SUMMARY:")
        print(f"  • Files Scanned    : {report.scanned_files}")
        print(f"  • Newly Indexed    : {report.indexed_files}")
        print(f"  • Updated Files    : {report.updated_files}")
        print(f"  • Unchanged (Skipped): {report.skipped_files}")
        print(f"  • Removed / Pruned : {report.deleted_files}")
        print(f"  • Rejected (Media) : {report.rejected_files}")
        print(f"  • Errors           : {report.error_files}")
        print(f"  • Total FTS Chunks : {report.total_chunks}")
        print("-" * 70)

        if report.details:
            print("\nFILE ACTION LOG:")
            for d in report.details[:20]:
                fid = d.get("file_id", "Unknown")
                action = d.get("action", "PROCESSED")
                status = d.get("status", "OK")
                chunks = d.get("chunks", 0)
                err = d.get("error")
                err_str = f" [Error: {err}]" if err else ""
                print(f"  [{action:<7}] {fid:<40} {status} ({chunks} chunks){err_str}")
            if len(report.details) > 20:
                print(f"  ... and {len(report.details) - 20} more files.")

        print("\n" + "=" * 70)
        print(" [SUCCESS] Reindex complete. Knowledge base is ready for RAG queries.")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n[FATAL ERROR] Reindexing failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
