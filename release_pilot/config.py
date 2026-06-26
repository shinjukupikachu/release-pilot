import os
from pathlib import Path

SLACK_CHANNEL: str = os.environ.get("SLACK_CHANNEL", "C0BDFHM8EA2")
DB_PATH: str = os.environ.get("DB_PATH", "./releases.db")
TEST_DATA: bool = os.environ.get("TEST_DATA", "0") == "1"
TEST_DATA_DIR: Path = Path(os.environ.get("TEST_DATA_DIR", "./test_data"))
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
SLACK_BOT_TOKEN: str | None = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN: str | None = os.environ.get("SLACK_APP_TOKEN")
