#!/usr/bin/env python3
"""
Compare a current extraction output against a baseline extraction output.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "food_ai"))

from batch_review import load_and_compare_extraction_batches


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare current extraction output against a baseline")
    parser.add_argument("--current", required=True, help="Path to current extraction JSON output")
    parser.add_argument("--baseline", required=True, help="Path to baseline extraction JSON output")
    parser.add_argument("--output", help="Optional path to save the delta review JSON")
    args = parser.parse_args()

    report = load_and_compare_extraction_batches(args.current, args.baseline)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
