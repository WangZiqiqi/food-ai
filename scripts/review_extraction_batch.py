#!/usr/bin/env python3
"""
Generate a deterministic batch quality report for an extraction output.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "food_ai"))

from build_quality import load_and_summarize_extraction_quality


def main() -> int:
    parser = argparse.ArgumentParser(description="Review an extraction batch without invoking agents")
    parser.add_argument("--input", required=True, help="Path to extraction JSON output")
    parser.add_argument("--output", help="Optional path to save the quality report JSON")
    args = parser.parse_args()

    report = load_and_summarize_extraction_quality(args.input)
    output_path = Path(args.output) if args.output else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
