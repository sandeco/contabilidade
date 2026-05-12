# -*- coding: utf-8 -*-
"""
extract_documents.py
Utility script for the doc-intelligence skill.
Refactored to be project-agnostic and generic.
"""
import sys
import json
import os
import argparse
from typing import List, Dict, Any

# Recommended: Install the project as a package or set PYTHONPATH.
# For backward compatibility, we keep a fallback search for the lib directory.
try:
    # pyrefly: ignore [missing-import]
    from lib.intelligence.extract_financial import extract_financial_data
except ImportError:
    # Fallback to local search if not installed as a package
    from pathlib import Path
    # Assuming the project structure: skills/doc-intelligence/extract_documents.py
    # and lib is in the root.
    BASE_DIR = Path(__file__).resolve().parents[2]
    if str(BASE_DIR) not in sys.path:
        sys.path.append(str(BASE_DIR))
    
    try:
        # pyrefly: ignore [missing-import]
        from lib.intelligence.extract_financial import extract_financial_data
    except ImportError:
        # If still not found, we will report error in main
        extract_financial_data = None

def markdown_from_records(data: Dict[str, Any], columns: List[str] = None, currency_symbol: str = "R$") -> str:
    """
    Generates a Markdown table from a list of records.
    
    Args:
        data: Dictionary containing 'success', 'records', and potentially 'error'.
        columns: List of columns to display. If None, uses all keys from the first record.
        currency_symbol: Symbol to use for currency formatting.
    """
    if not data.get('success'):
        error_msg = data.get('error', 'Unknown error')
        return f"**Error:** {error_msg}"
    
    records = data.get('records', [])
    if not records:
        return "*No records found.*"
    
    # Determine columns automatically if not provided
    if not columns:
        # Filter out internal keys starting with underscore
        columns = [k for k in records[0].keys() if not k.startswith('_')]
    
    # Header
    header = "| " + " | ".join([col.capitalize() for col in columns]) + " |"
    separator = "| " + " | ".join(["---" for _ in columns]) + " |"
    
    lines = [header, separator]
    
    for rec in records:
        row = []
        for col in columns:
            val = rec.get(col, "-")
            # Format currency if the column name looks like 'amount' or 'value'
            if any(key in col.lower() for key in ['amount', 'valor', 'value']) and isinstance(val, (int, float)):
                val = f"{currency_symbol} {val:.2f}"
            row.append(str(val))
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Extract financial data from spreadsheets and output Markdown.")
    parser.add_argument("file_path", help="Path to the spreadsheet file")
    parser.add_argument("--currency", default=os.getenv("FINANCIAL_CURRENCY", "R$"), help="Currency symbol (default: R$)")
    parser.add_argument("--output", choices=["md", "json"], default="md", help="Output format (default: md)")
    parser.add_argument("--cols", help="Comma-separated list of columns to display")
    
    args = parser.parse_args()

    if extract_financial_data is None:
        print(json.dumps({"error": "Dependency 'lib.intelligence.extract_financial' not found. Please check your PYTHONPATH."}, ensure_ascii=False))
        sys.exit(1)

    if not os.path.exists(args.file_path):
        print(json.dumps({"error": f"File not found: {args.file_path}"}, ensure_ascii=False))
        sys.exit(1)

    try:
        result = extract_financial_data(args.file_path)
        
        if args.output == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            cols = args.cols.split(',') if args.cols else None
            md = markdown_from_records(result, columns=cols, currency_symbol=args.currency)
            print(md)
            
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()

