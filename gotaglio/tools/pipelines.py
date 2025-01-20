from abc import ABC, abstractmethod
import json


class Pipeline(ABC):
    @abstractmethod
    def stages(self):
        pass

    @abstractmethod
    def summarize(self, results):
        pass
    
    @abstractmethod
    def metadata(self):
        pass
