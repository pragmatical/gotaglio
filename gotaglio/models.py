from abc import ABC, abstractmethod
import os

from .constants import app_configuration
from .exceptions import ExceptionContext
from .shared import read_json_file
from . import lazy_imports


class Model(ABC):
    # `context` parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context. Real models ignore the `context`
    # parameter.
    @abstractmethod
    def infer(self, message, context=None):
        pass

    @abstractmethod
    def metadata(self):
        pass


class AzureAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            self._client = lazy_imports.azure_ai_inference.ChatCompletionsClient(
                endpoint=endpoint, credential=lazy_imports.azure_core_credentials.AzureKeyCredential(key)
            )

        response = self._client.complete(messages=messages)

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


class AzureOpenAI(Model):
    def __init__(self, registry, configuration):
        self._config = configuration
        self._client = None
        registry.register_model(configuration["name"], self)

    async def infer(self, messages, context=None):
        if not self._client:
            endpoint = self._config["endpoint"]
            key = self._config["key"]
            api = self._config["api"]
            self._client = lazy_imports.openai.AzureOpenAI(
                api_key=key,
                api_version=api,
                azure_endpoint=endpoint,
            )

        response = self._client.chat.completions.create(
            model=self._config["deployment"],
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False,
        )

        return response.choices[0].message.content

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}


def register_models(
    registry,
    config_file=None,
    credentials_file=None,
):
    config_file = config_file or app_configuration["model_config_file"]
    credentials_file = credentials_file or app_configuration["model_credentials_file"]

    if not os.path.exists(config_file):
        pass
    else:
        config = read_json_file(config_file, False)

        # Merge in keys from credentials file
        credentials = read_json_file(credentials_file, True)
        for model in config:
            if model["name"] in credentials:
                model["key"] = credentials[model["name"]]

        for model in config:
            with ExceptionContext(f"While registering model '{model['name']}':"):
                if model["type"] == "AZURE_AI":
                    AzureAI(registry, model)
                elif model["type"] == "AZURE_OPEN_AI":
                    AzureOpenAI(registry, model)
                else:
                    raise ValueError(
                        f"Model {model['name']} has unsupported model type: {model['type']}"
                    )
