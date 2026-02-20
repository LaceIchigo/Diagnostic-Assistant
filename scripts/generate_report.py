#!/usr/bin/env python3
"""Generate an HTML evaluation report from WER/DER results."""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostic Assistant — Report Generator"
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory containing evaluation_results.json",
    )
    parser.add_argument(
        "--output",
        default="report.html",
        help="Output HTML report file path",
    )
    return parser.parse_args()


def load_results(results_dir: str) -> List[dict]:
    """Load evaluation results from JSON file."""
    path = os.path.join(results_dir, "evaluation_results.json")
    if not os.path.exists(path):
        print(f"Results file not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_html(results: List[dict], output_path: str) -> None:
    """Generate an HTML report from evaluation results.

    Args:
        results: List of scenario result dicts.
        output_path: Path to write the HTML file.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)

    rows = ""
    for r in results:
        wer_str = f"{r['wer']:.2%}" if r.get("wer") is not None else "N/A"
        der_str = f"{r['der']:.2%}" if r.get("der") is not None else "N/A"
        status_cls = "pass" if r.get("passed") else "fail"
        status_str = "✓ PASS" if r.get("passed") else "✗ FAIL"
        t = f"{r.get('processing_time', 0):.2f}s"
        rows += f"""
        <tr class="{status_cls}">
            <td>{r['scenario_id']}</td>
            <td>{r['scenario_name']}</td>
            <td>{wer_str}</td>
            <td>{der_str}</td>
            <td>{t}</td>
            <td><span class="badge {status_cls}">{status_str}</span></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diagnostic Assistant — Raport Evaluare</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f7fa; color: #333; }}
  h1 {{ color: #1a1a2e; }}
  .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.1); min-width: 140px; text-align: center; }}
  .card .value {{ font-size: 2em; font-weight: bold; color: #1a73e8; }}
  .card .label {{ color: #666; font-size: 0.9em; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); margin-top: 20px; }}
  th {{ background: #1a1a2e; color: white; padding: 12px 16px; text-align: left; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid #eee; }}
  tr.pass {{ background: #f0fff4; }}
  tr.fail {{ background: #fff5f5; }}
  .badge {{ padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }}
  .badge.pass {{ background: #34a853; color: white; }}
  .badge.fail {{ background: #e53935; color: white; }}
  footer {{ margin-top: 40px; color: #888; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>🩺 Diagnostic Assistant — Raport de Evaluare</h1>
<p>Generat la: {now}</p>

<div class="summary">
  <div class="card">
    <div class="value">{total}</div>
    <div class="label">Total scenarii</div>
  </div>
  <div class="card">
    <div class="value" style="color: #34a853">{passed}</div>
    <div class="label">Trecut</div>
  </div>
  <div class="card">
    <div class="value" style="color: #e53935">{total - passed}</div>
    <div class="label">Eșuat</div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>ID Scenariu</th>
      <th>Denumire</th>
      <th>WER</th>
      <th>DER</th>
      <th>Timp procesare</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>

<footer>
  <p>⚠️ Decizia medicală finală aparține exclusiv medicului. Sistemul are rol de suport și standardizare a informației.</p>
</footer>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report saved to: {output_path}")


def main() -> None:
    args = parse_args()
    results = load_results(args.results_dir)
    if not results:
        print("No results to report.")
        return
    generate_html(results, args.output)


if __name__ == "__main__":
    main()
