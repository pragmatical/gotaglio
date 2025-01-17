from .constants import model_config_file, model_credentials_file

from abc import ABC, abstractmethod
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import openai
import os
import json


class Model(ABC):
    @abstractmethod
    def infer(self, messages):
        pass

    @abstractmethod
    def metadata(self):
        pass


class AzureAI(Model):
    def __init__(self, runner, configuration):
        self._config = configuration
        self._client = None
        runner.register_model(configuration["name"], self)

    async def infer(self, messages):
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
    def __init__(self, runner, configuration):
        self._config = configuration
        self._client = None
        runner.register_model(configuration["name"], self)

    async def infer(self, messages):
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


class Echo(Model):
    def __init__(self, runner, configuration):
        runner.register_model(configuration["name"], self)

    async def infer(self, messages):
        return json.dumps(messages)

    def metadata(self):
        return {k: v for k, v in self._config.items() if k != "key"}

def read_json_file(filename, optional):
    try:
        if optional and not os.path.isfile(filename):
            return {}  
        with open(filename, "r") as file:
            result = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"File {filename} not found.")
    except json.JSONDecodeError:
        raise ValueError(f"Error decoding JSON from file {filename}.")
    return result

def register_models(
    runner, config_file=model_config_file, credentials_file=model_credentials_file
):
    config = read_json_file(config_file, False)

    # MErge in keys from credentials file
    credentials = read_json_file(credentials_file, True)
    for model in config:
        if model["name"] in credentials:
            model["key"] = credentials[model["name"]]

    try:
        for model in config:
            if model["type"] == "AZURE_AI":
                AzureAI(runner, model)
            elif model["type"] == "AZURE_OPEN_AI":
                AzureOpenAI(runner, model)
            elif model["type"] == "ECHO":
                Echo(runner, model)
            else:
                raise ValueError(
                    f"Model {model['name']} has unsupported model type: {model['type']}"
                )
    except Exception as e:
        print(f"An error occurred while registering models: {e}")
