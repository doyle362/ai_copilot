#!/usr/bin/env python3
"""CLI script for database connectivity diagnostics."""

import os
import sys
import json
from pathlib import Path

# Add the services/analyst directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "analyst"))

def main():
    """Run database diagnostics from CLI."""
    # Load environment from .env
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

    # Import after setting up environment
    from analyst.routes.diag import diag_db

    result = diag_db()
    print(json.dumps(result, indent=2))

    # Exit with non-zero if database connection failed
    if not result.get("psycopg_connect", {}).get("ok", False):
        sys.exit(1)

if __name__ == "__main__":
    main()