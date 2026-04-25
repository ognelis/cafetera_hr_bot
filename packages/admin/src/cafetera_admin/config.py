"""Admin-specific settings extending the core configuration."""

from cafetera_core.config import CoreSettings


class AdminSettings(CoreSettings):
    """Settings for the admin web UI package.

    Inherits all shared RAG/storage settings from CoreSettings.
    Adds only the admin-specific fields.

    Extra environment variables (e.g. VK settings) are silently ignored
    so the admin package can coexist with the same ``.env`` file used
    by the VK bot package.
    """

    model_config = {"extra": "ignore"}

    admin_api_key: str = ""
