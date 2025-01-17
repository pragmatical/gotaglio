from .templating import load_template

from abc import ABC, abstractmethod
import json


class Pipeline(ABC):
    @abstractmethod
    def stages(self):
        pass

    @abstractmethod
    def metadata(self):
        pass
