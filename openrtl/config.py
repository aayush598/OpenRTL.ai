import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from openrtl.exceptions import ConfigError

load_dotenv()


class Config:
    """Application configuration loaded from environment variables.

    All values can be overridden via environment variables:
      NVIDIA_API_KEY, OPENRTL_MODEL_ID, OPENRTL_LOG_LEVEL,
      OPENRTL_PROJECTS_DIR, OPENRTL_DB_PATH, OPENRTL_LOG_FILE
    """

    def __init__(self) -> None:
        self.nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
        self.nvidia_model_id: str = os.getenv(
            "OPENRTL_MODEL_ID", "meta/llama-3.1-8b-instruct"
        )
        self.nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
        self.log_level: str = os.getenv("OPENRTL_LOG_LEVEL", "INFO")
        self.log_file: str | None = os.getenv("OPENRTL_LOG_FILE") or None

        self.agent_retries: int = 3
        self.agent_retry_delay: int = 2
        self.tool_call_limit: int = 5
        self.synthesis_timeout: int = 120

        self.base_dir: Path = Path(__file__).resolve().parent.parent
        self.projects_dir: Path = Path(
            os.getenv("OPENRTL_PROJECTS_DIR", str(Path.cwd() / "projects"))
        )
        self.db_path: Path = Path(
            os.getenv("OPENRTL_DB_PATH", str(Path.cwd() / "database" / "openrtl.db"))
        )
        self.knowledge_dir: Path = Path(
            os.getenv("OPENRTL_KNOWLEDGE_DIR", str(Path.cwd() / "knowledge_base"))
        )

        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        if not self.nvidia_api_key:
            raise ConfigError(
                "NVIDIA_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )


config: Final[Config] = Config()
