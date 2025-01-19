import argparse
from copy import deepcopy
from glom import assign
import json
import os

def format_list(values):
    if not values:
        return ""
    elif len(values) == 1:
        return values[0]
    elif len(values) == 2:
        return f"{values[0]} and {values[1]}"
    else:
        return f"{', '.join(values[:-1])}, and {values[-1]}"


def parse_key_value_args(args):
    """Parse key=value arguments into a dictionary."""
    config = {}
    for arg in args:
        if "=" not in arg:
            raise argparse.ArgumentTypeError(
                f"Invalid format: '{arg}'. Expected key=value."
            )
        key, value = arg.split("=", 1)
        config[key] = value
    return config


def get_filenames_with_prefix(folder_path, prefix):
    """
    Returns a list of filenames in the specified folder that start with the given prefix.

    :param folder_path: Path to the folder to search.
    :param prefix: The prefix to filter filenames.
    :return: List of filenames that start with the prefix.
    """
    try:
        # List all files in the folder
        filenames = [
            filename
            for filename in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, filename))
            and filename.startswith(prefix)
        ]
        return filenames
    except FileNotFoundError:
        print(f"Error: Folder '{folder_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


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


def write_json_file(filename, data):
    with open (filename, "w") as file:
        json.dump(data, file, indent=2)


def parse_patches(path_bindings):
    """Parse key=value arguments into a dictionary."""
    patch = {}
    for binding in path_bindings:
        if "=" not in binding:
            raise ValueError(f"Invalid patch: '{binding}'. Expected key=value.")
        key, value = binding.split("=", 1)
        key = key.strip()
        value = value.strip()
        patch[key] = value
    return patch


def apply_patch(target_dict, patches):
    """
    Create a new dictionary that results from applying a series of
    dot-separated key-value pairs as a patch to a a deep copy of an
    existing dictionary.

    :param target_dict: The dictionary to be copied and patched.
    :param patches: A dictionary with dot-separated keys and their corresponding values.
    """
    result = deepcopy(target_dict)
    for key, value in patches.items():
        assign(result, key, value, missing=dict)
    return result


# # Existing hierarchical dictionary
# existing_dict = {
#     "a": {
#         "b": {
#             "c": 1
#         }
#     },
#     "d": 4
# }

# # Dot-separated key-value pairs to apply as patches
# # patches = {
# #     "a.b.c": 2,        # Update an existing nested value
# #     "a.b.d": 5,        # Add a new nested key
# #     "e.f.g": 6         # Add a new deeply nested structure
# # }
# patches = parse_patches("a.b.c=2 a.b.d=5 e.f.g=6".split())

# # Apply the patch
# result = apply_patch(existing_dict, patches)

# print(json.dumps(result, indent=2))


# def minimal_unique_prefix(uuids):
#     """
#     Given a list of UUIDs, return a list of minimal length prefixes
#     that uniquely identify each UUID.

#     :param uuids: List of UUID strings
#     :return: List of minimal unique prefixes
#     """
#     prefixes = []
#     for uuid in uuids:
#         for length in range(1, len(uuid) + 1):
#             prefix = uuid[:length]
#             # Check if prefix is unique among all UUIDs
#             if all(not other.startswith(prefix) or other == uuid for other in uuids):
#                 prefixes.append(prefix)
#                 break
#     return prefixes

def minimal_unique_prefix(uuids):
    """
    Given a list of UUIDs, return a list of minimal length prefixes
    that uniquely identify each UUID. All prefixes will have the length
    of the longest required prefix.

    :param uuids: List of UUID strings
    :return: List of minimal unique prefixes with uniform length
    """
    prefixes = []
    max_length = 0

    # First pass: determine the minimal unique prefix for each UUID
    for uuid in uuids:
        for length in range(1, len(uuid) + 1):
            prefix = uuid[:length]
            # Check if prefix is unique among all UUIDs
            if all(not other.startswith(prefix) or other == uuid for other in uuids):
                prefixes.append(prefix)
                max_length = max(max_length, length)
                break

    return max_length
    # # Second pass: adjust all prefixes to the length of the longest required prefix
    # uniform_prefixes = [prefix + uuid[len(prefix):max_length] for prefix, uuid in zip(prefixes, uuids)]

    # return uniform_prefixes

# # Example usage
# uuids = [
#     "0383eea3-93d8-4bee-9dcf-090145f80bbd",
#     "099e4ea1-9b5f-457f-ba3e-880ae7e8dfc9",
#     "13316955-8021-4e45-b474-39125e4d3305",
#     "1dbab635-8ab8-4bb7-bb29-179e8730fed8",
#     "28a13033-f0d3-470c-a123-062f92f6b1e3",
#     "2add3862-582d-45e8-ba8d-d46ad8ce7bc6",
#     "360fe048-0a61-4eb6-a66d-9ca8f24a4448",
#     "37944424-5da3-4d2e-8676-4e96db2cfe2b",
#     "4651f420-bc2e-4638-809b-6702faa182d0",
#     "4fc07081-93a2-475b-b490-e7493962e265",
#     "57518803-553c-43cb-a71a-e7e03b870ebb",
#     "69ccd226-323f-4822-a8cd-9edd68985a0f",
#     "6a7b69b4-112e-465d-a4c6-c5ab3c099398",
#     "75ac929c-a251-4e3f-b21a-3d4e0d86b341",
#     "76e7ad88-b144-4731-b1e1-5a8f4d7d4ecf",
#     "7fece99d-aa4e-4217-8137-3a7c4ad25911",
#     "8226c3e0-4ca6-421a-880e-c5a71a50c242",
#     "8d4560e6-6b04-43ed-88f5-51284b573b4e",
#     "960c1b24-4367-4bad-ac7f-3316017d736c",
#     "977c5574-71c8-49ba-8f55-d9d268d4fb9e",
#     "99b5a329-d9d5-4cc3-9de2-5e5dd0d0d80f",
#     "9cce731c-aad3-41b1-a4af-612b36fb8b48",
#     "a1bb8aa6-1d06-43d5-9bf7-c5c6235f6850",
#     "a283ecd6-f0ae-4418-a5bb-062a8be1fabd",
#     "a2e883f8-c408-43f4-a104-b5215127b405",
#     "aecf608b-4862-4332-bd3e-1d70742b7431",
#     "b702b431-259f-4e3b-bd18-666756ed3ee9",
#     "c367255c-845a-46bf-9dd6-061f0cb31a9d",
#     "c44cb199-bfe3-4331-91af-d1d4f02ae182",
#     "c6cb6340-dcdd-44ad-9a28-118a2e661d3a",
#     "c6e9e5f8-56ec-42de-a1af-b03e3cf78562",
#     "cec4207b-54cd-4026-a040-7de58ca92710",
#     "d4a3ce1d-75db-4677-8c76-4b63a5e6c51a",
#     "dd33937c-c4ca-471b-b44b-a7e9cdbd5917",
#     "e897f696-3d61-4900-9266-6f03426f2bb6",
#     "ecb9c896-3ecd-4940-8943-643b5072e584",
#     "fc0c3d1d-067f-4c62-9c34-b58377bdb59b",
#     "ff831dbb-d2e4-415d-bf43-94d6f5c5b053",
# ]
# print(minimal_unique_prefix(uuids))
