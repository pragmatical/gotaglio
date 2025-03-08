import os
import sys
# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.main import main

from api import ApiPipeline
from menu import MenuPipeline

def go():
  main([ApiPipeline, MenuPipeline])


if __name__ == "__main__":
    go()
