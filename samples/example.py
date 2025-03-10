import os
import sys
# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.main import main

from menu import MenuPipeline
from simple import SamplePipeline

def go():
  main([MenuPipeline, SamplePipeline])


if __name__ == "__main__":
    go()
