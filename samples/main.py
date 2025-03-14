import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from gotaglio.main import main
from gotaglio.pipeline import Pipeline

from dag.dag import DAGPipeline
from menu.menu import MenuPipeline
from simple.simple import SimplePipeline


def go():
    main([DAGPipeline, MenuPipeline, SimplePipeline])


if __name__ == "__main__":
    go()
