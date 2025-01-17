import json
import os

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
