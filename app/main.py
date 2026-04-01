from __future__ import annotations

import argparse

import uvicorn

from app.api.application import create_app
from app.utils.config import Settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fashion inspiration app.")
    parser.add_argument("--host", default=None, help="Override the host from .env")
    parser.add_argument("--port", type=int, default=None, help="Override the port from .env")
    return parser.parse_args()


def main() -> None:
    settings = Settings.from_env()
    args = parse_args()

    # CLI args win over .env so the app can be moved to a free port quickly.
    host = args.host or settings.host
    port = args.port or settings.port

    uvicorn.run(
        "app.api.application:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
