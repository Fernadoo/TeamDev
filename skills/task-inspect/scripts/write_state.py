#!/usr/bin/env python3
"""Write JSON state from stdin to a file, then verify it.

Usage:
    echo '{"projects":[]}' | write_state.py <output_file>

Reads JSON from stdin, writes it formatted (2-space indent) to the output
file, then reads it back to verify. Outputs "OK" on success.

Exit codes:
  0  Success
  1  Invalid JSON on stdin
  2  Write or verification failed
"""

import json
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: write_state.py <output_file>", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]

    try:
        state = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(output_file, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"Error: Failed to write file: {e}", file=sys.stderr)
        sys.exit(2)

    # Verify
    try:
        with open(output_file, "r") as f:
            verified = json.load(f)
        if verified != state:
            print("Error: Verification failed - written data does not match", file=sys.stderr)
            sys.exit(2)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error: Verification failed: {e}", file=sys.stderr)
        sys.exit(2)

    print("OK")


if __name__ == "__main__":
    main()
