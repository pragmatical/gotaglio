import re

from gotaglio.shared import minimal_unique_prefix


# class IdHelper:
#     def __init__(self, results, field):
#         self._field = field

#         #
#         # Ensure every case has a uuid field that contains a valid uuid.
#         #
#         guid_pattern = re.compile(
#             r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
#         )

#         using_uuids = all(
#             field in result["case"] and guid_pattern.match(result["case"][field])
#             for result in results
#         )

#         if not using_uuids:
#             raise ValueError("Each case must have a valid uuid.")

#         #
#         # Ensure every case has a unique uuid.
#         #
#         uuids = {result["case"][field] for result in results}
#         if len(uuids) != len(results):
#             raise ValueError("Each case must have a unique uuid.")

#         self._prefix_len = max(minimal_unique_prefix([uuid for uuid in uuids]), 3)

#     def id(self, result):
#         return result["case"][self._field][: self._prefix_len]

def IdShortener(results, field):
        #
        # Ensure every case has a uuid field that contains a valid uuid.
        #
        guid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )

        using_uuids = all(
            field in result["case"] and guid_pattern.match(result["case"][field])
            for result in results
        )

        if not using_uuids:
            raise ValueError("Each case must have a valid uuid.")

        #
        # Ensure every case has a unique uuid.
        #
        uuids = {result["case"][field] for result in results}
        if len(uuids) != len(results):
            raise ValueError("Each case must have a unique uuid.")

        prefix_len = max(minimal_unique_prefix([uuid for uuid in uuids]), 3)

        return lambda result: result["case"][field][:prefix_len]

# Per-row values
# Aggregates of per-row values
# Text() blocks
# Helpers - e.g. IdHelper
# def go(results):
#     table = TableBuilder(
#         {"passed": passed},
#         {"id": Id, "run": Status, "score": Custom(), "keywords": Custom()},
#     )
