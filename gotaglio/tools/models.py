from .constants import model_config_file, model_credentials_file
from .exceptions import ExceptionContext
from .shared import read_json_file

from abc import ABC, abstractmethod
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import json
import openai


class Model(ABC):
    # context parameter provides entire test case context to
    # assist in implementing mocks that can pull the expected
    # value ouf of the context.
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
            self._client = ChatCompletionsClient(
                endpoint=endpoint, credential=AzureKeyCredential(key)
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
            self._client = openai.AzureOpenAI(
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
    registry, config_file=model_config_file, credentials_file=model_credentials_file
):
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
