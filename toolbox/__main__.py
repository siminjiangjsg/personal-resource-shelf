# /// script
# requires-python = ">=3.13"
# dependencies = ["fastapi==0.141.1", "pydantic==2.13.4", "uvicorn==0.52.1"]
# ///
# How to run: from the project root, python -m toolbox
"""Start the loopback server; the launcher owns opening the browser."""

import os
from pathlib import Path

import uvicorn

from toolbox.app import create_app


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    directory = Path(os.environ.get("TOOLBOX_DATA_DIR", str(root / "data")))
    port = int(os.environ.get("TOOLBOX_PORT", "8765"))
    uvicorn.run(
        create_app(directory), host="127.0.0.1", port=port, access_log=False, log_level="warning"
    )


if __name__ == "__main__":
    main()
