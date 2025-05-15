import os

app_configuration_values = {
    "base_folder": "",
    "log_folder": "logs",
    "model_config_file": "models.json",
    "model_credentials_file": ".credentials.json",
    "default_concurrancy": 2,
    "program_name": "gotag",
}

class AppConfiguration:
    def __init__(self, config):
        self._config = config
        self.base_relative = ["log_folder", "model_config_file", "model_credentials_file"]

    def __getitem__(self, key):
        if key in self.base_relative:
            return os.path.join(self._config["base_folder"], self._config[key])
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value

    def __contains__(self, key):
        return key in self._config

    def __repr__(self):
        return str(self._config)

app_configuration = AppConfiguration(app_configuration_values)
