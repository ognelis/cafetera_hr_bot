from cafetera_core.config import CoreSettings


class VKSettings(CoreSettings):
    """Settings for the VK bot package.

    Inherits all shared RAG/storage settings from CoreSettings.
    Extra environment variables (e.g. admin settings) are silently ignored
    so the VK bot can coexist with the same ``.env`` file used by the admin.
    """

    model_config = {"extra": "ignore"}

    vk_access_token: str = ""
    vk_group_id: int = 0
