#!/usr/bin/env python3
"""Read and validate teamdev-state.json from the current working directory.

Usage: read-state.py [path/to/teamdev-state.json]

If no path is given, reads ./teamdev-state.json.

Exit codes:
  0 - Success, prints JSON to stdout
  1 - File not found (prints empty initial state to stdout)
  2 - Invalid JSON (prints error to stderr)
"""
import json
import sys
import os


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "teamdev-state.json"

    if not os.path.exists(path):
        # Return empty initial state
        print(json.dumps({"projects": []}, indent=2))
        sys.exit(1)

    try:
        with open(path, "r") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(2)

    if "projects" not in state:
        print(f"Missing 'projects' key in {path}", file=sys.stderr)
        sys.exit(2)

    print(json.dumps(state, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
