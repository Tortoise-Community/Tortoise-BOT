import os
import json
import logging


logger = logging.getLogger(__name__)


class ConfigHandler:
    CONFIG_PATH = "configs"

    def __init__(self, config_name: str):
        """
        :param config_name: name of the config file (including the extension suffix).
        """
        self.path = os.path.join(ConfigHandler.CONFIG_PATH, config_name)
        self.loaded = self._load_config()

    def _load_config(self) -> dict:
        """
        Loads config and checks fo validity of json file.
        :return: dict loaded json data
        """
        try:
            with open(self.path) as cfg:
                data = json.load(cfg)
                return data
        except FileNotFoundError as e:
            logger.critical(f"Config json file was not found: {self.path} : {e}")
        except ValueError as e:
            logger.critical(f"Invalid config json: {e}")
        except KeyError as e:
            logger.critical(f"Invalid json config configuration: {e}")
        except Exception as e:
            logger.critical(f"Can't load json config: {e}")

    def reload_config(self):
        """
        Reloads config.
        If you change the config manually while the bot is running you need to call this method
        so the values are updated in memory.
        """
        self.loaded = self._load_config()

    def get_key(self, key):
        try:
            return self.loaded[key]
        except KeyError as e:
            error_message = f"Key '{key}' not found in json config! {e}"
            logger.critical(error_message)
            raise KeyError(error_message)

    def update_key(self, key, value):
        try:
            self.loaded[key] = value
            with open(self.path, "w") as cfg:
                json.dump(self.loaded, cfg, indent=4, sort_keys=True)
        except TypeError as e:
            logger.critical(f"Unable to serialize the object {e}")
        except Exception as e:
            logger.critical(f"Unable to update json key {key} to value {value}: {e}")
