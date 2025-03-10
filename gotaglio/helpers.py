import re

from gotaglio.shared import minimal_unique_prefix


def IdShortener(uuids):
        #
        # Ensure every case has a uuid field that contains a valid uuid.
        #
        guid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )

        using_uuids = all(
            guid_pattern.match(uuid)
            for uuid in uuids
        )

        if not using_uuids:
            raise ValueError("Each case must have a valid uuid.")

        #
        # Ensure every case has a unique uuid.
        #
        unique = set(uuids)
        if len(uuids) != len(unique):
            raise ValueError("Each case must have a unique uuid.")

        prefix_len = max(minimal_unique_prefix(uuids), 3)

        return lambda uuid: uuid[:prefix_len]
