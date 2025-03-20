default_concurrancy = 2
model_config_file = "models.json"
model_credentials_file = ".credentials.json"
program_name = "gotag"

if 'log_folder' not in globals():
  log_folder = "logs"

values = {
    "base_folder": "",
    "log_folder": "logs",
    "model_config_file": "models.json",
    "model_credentials_file": ".credentials.json",
    "default_concurrancy": 2,
    "program_name": "gotag"
}
