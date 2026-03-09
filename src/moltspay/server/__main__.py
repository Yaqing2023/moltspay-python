#!/usr/bin/env python3
"""
MoltsPay Server CLI

Usage:
    python -m moltspay.server ./my_skill --port 8402
    
    # Or with multiple skills
    python -m moltspay.server ./video_gen ./transcription
    
    # Or via console script (after install)
    moltspay-server ./my_skill
"""

import argparse
import sys
from pathlib import Path

from .server import MoltsPayServer


def main():
    parser = argparse.ArgumentParser(
        description="MoltsPay Server - Accept x402 payments for AI services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start server with one skill
    moltspay-server ./my_skill --port 8402
    
    # Start server with multiple skills
    moltspay-server ./video_gen ./transcription ./image_gen
    
    # Use mainnet
    moltspay-server ./my_skill --mainnet
    
Skill Structure:
    my_skill/
    ├── moltspay.services.json    # Service definitions
    └── __init__.py               # Python functions (async or sync)

Environment Variables (in ~/.moltspay/.env):
    USE_MAINNET=true              # Use Base mainnet
    CDP_API_KEY_ID=xxx            # CDP API Key ID
    CDP_API_KEY_SECRET=xxx        # CDP API Key Secret
        """,
    )
    
    parser.add_argument(
        "skills",
        nargs="+",
        help="Paths to skill directories containing moltspay.services.json",
    )
    
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8402,
        help="Server port (default: 8402)",
    )
    
    parser.add_argument(
        "-H", "--host",
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)",
    )
    
    parser.add_argument(
        "--mainnet",
        action="store_true",
        help="Use Base mainnet (requires CDP credentials)",
    )
    
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use Base Sepolia testnet (default)",
    )
    
    args = parser.parse_args()
    
    # Validate skill paths
    for skill_path in args.skills:
        path = Path(skill_path)
        if not path.exists():
            print(f"Error: Skill path does not exist: {skill_path}", file=sys.stderr)
            sys.exit(1)
        if not path.is_dir():
            print(f"Error: Skill path is not a directory: {skill_path}", file=sys.stderr)
            sys.exit(1)
        if not (path / "moltspay.services.json").exists():
            print(f"Error: No moltspay.services.json found in {skill_path}", file=sys.stderr)
            sys.exit(1)
        if not (path / "__init__.py").exists():
            print(f"Error: No __init__.py found in {skill_path}", file=sys.stderr)
            sys.exit(1)
    
    # Determine mainnet vs testnet
    use_mainnet = None
    if args.mainnet:
        use_mainnet = True
    elif args.testnet:
        use_mainnet = False
    
    # Create and start server
    try:
        server = MoltsPayServer(
            *args.skills,
            port=args.port,
            host=args.host,
            use_mainnet=use_mainnet,
        )
        server.listen()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
