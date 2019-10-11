import logging
import json

logger = logging.getLogger(__name__)


class ConfigHandler:
    CONFIG_PATH = "config.json"

    def __init__(self):
        self._config = ConfigHandler._load_config()

    @staticmethod
    def _load_config():
        try:
            with open(ConfigHandler.CONFIG_PATH) as cfg:
                data = json.load(cfg)
                return data
        except Exception as e:
            logger.critical(f"Can't load json config: {e}")

    def get_token(self):
        return self._config["token"]
