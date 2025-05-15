from copy import deepcopy
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import TypedDict


class EditType:
    DELETE = "DELETE"
    INSERT = "INSERT"
    REPAIR = "REPAIR"


class Edit(TypedDict):
    op: EditType
    cost: float
    steps: list[str]


class DiffResult(TypedDict):
    cost: float
    edits: list[Edit]


class Repair:
    """
    xyz
    """

    def __init__(
        self, idAttr, childrenAttr, ignoreAttrs, atomicAttrs, nameAttr
    ) -> None:
        """
        Construct an instance of the `Repair` class.

        Parameters
        ----------
        idAttr : str
            The name of the attribute storing the node's unique integer id.
        childrenAttr : str
            The name of the attribute storing the list of child nodes.
        ignoreAttrs: list of str
            A list of attribute names that should be ignored when comparing trees.
        atomicAttrs: list of str
            A list of attribute names where a mismatch between the observed
            and expected values would require the repair to delete the observed
            tree and then insert the expected tree. Mismatches in other attributes
            only require a single change operation at the attribute level.
        nameAttr: str
            The name of the attribute to represent the node's name in diagnostic
            text.

        Returns
        -------
        Repair
            The newly constructed class instance.
        """
        self._idAttr = idAttr
        self._childrenAttr = childrenAttr
        self._ignoreAttrs = ignoreAttrs
        self._atomicAttrs = atomicAttrs
        self._excludedAttrs = [idAttr, childrenAttr] + ignoreAttrs + atomicAttrs
        self._nameAttr = nameAttr

        # _rootCounter is used to keep track of next available top-level id.
        # Note that addIDs() can be invoked multiple times (e.g. once for observed
        # tree and once for expected tree) and _rootCounter ensures that subsequent
        # call pick up with the next id.
        self._rootCounter = 0

    def addIds(self, root: dict | list[dict]) -> dict:
        """
        Add unique integer ids to a tree.

        Returns a deep copy of `root` with each node annotated with a unique integer
        identifier. Identifiers are unique across all calls to `Repair.addIds()` for
        an instance of `Repair`.

        Tree structure, including the `id` attribute and the `children` attribute is
        defined in the constructor of the `Repair` class.

        Parameters
        ----------
        root: dict | list[dict]
            The object to be labeled with unique ids.

        Returns
        -------
        dict | list[dict]
            The copy with ids added.

        """
        r = deepcopy(root)
        nodes = r if type(r) == list else [r]
        for n in nodes:
            prefix = self._rootCounter
            self._rootCounter += 1
            self._addIdsImpl(n, str(prefix))
        return r

    def resetIds(self):
        self._rootCounter = 0

    def diff(self, observed: dict | list[dict], expected: dict | list[dict]) -> Edit:
        """
        Compute the minimum repair cost and corresponding repair steps
        to modify `observed` to be identical to `expected`.
        """
        o = observed if type(observed) == list else [observed]
        e = expected if type(expected) == list else [expected]

        result = self._bipartiteMatchingDiff(o, e)

        return {
            "op": EditType.REPAIR,
            "cost": result["cost"],
            "steps": [step for edit in result["edits"] for step in edit["steps"]],
        }

    def _addIdsImpl(self, node, prefix):
        if self._idAttr in node:
            raise RuntimeError(f"Attempting to override value in {self._idAttr} attribute.")
        node[self._idAttr] = prefix
        if self._childrenAttr in node:
            for i, child in enumerate(node[self._childrenAttr]):
                childPrefix = prefix + "." + str(i)
                self._addIdsImpl(child, childPrefix)

    def _formatStep(self, item, message):
        uuid = item[self._idAttr] if self._idAttr in item else "???"
        name = item[self._nameAttr] if self._nameAttr in item else "???"
        return f"{uuid}: {name}: {message}"

    def _delete(self, item: dict) -> Edit:
        """
        Compute the cost and steps to delete `item`.
        """
        return {
            "op": EditType.DELETE,
            "cost": 1,
            "steps": [self._formatStep(item, f"delete item")],
        }

    def _insert(self, item: dict) -> Edit:
        """
        Compute the cost and steps to insert `item`.
        """
        cost = 0
        steps = []

        # Insert the generic item's default form
        cost += 1
        steps.append(self._formatStep(item, "insert default version"))

        # Non-standard attributes
        for attr in [
            k for k in item if k not in self._excludedAttrs and k != self._nameAttr
        ]:
            cost += 1
            steps.append(
                self._formatStep(item, f"change attribute({attr}) to '{item[attr]}'")
            )

        # Cost of adding children
        if self._childrenAttr in item:
            for child in item[self._childrenAttr]:
                edit = self._insert(child)
                cost += edit["cost"]
                steps += edit["steps"]

        return {"op": EditType.INSERT, "cost": cost, "steps": steps}

    def _repair(self, observed: dict, expected: dict) -> Edit:
        """
        Compute the cost and steps to edit `observed` to be identical to `expected`.
        """
        cost = 0
        steps = []

        expectedAtomic = any(
            [
                (x not in expected or observed[x] != expected[x])
                for x in observed
                if x in self._atomicAttrs
            ]
        )
        observedAtomic = any(
            [
                (x not in observed or observed[x] != expected[x])
                for x in expected
                if x in self._atomicAttrs
            ]
        )

        if expectedAtomic or observedAtomic:
            # This case used to just set cost to Infinity.
            # Changed code to do a delete, followed by an insert
            # with the score slightly diminished so that the system
            # prefers delete-before insert. This is important for
            # working with options that cannot coexist.
            deleteResults = self._delete(observed)
            steps += deleteResults["steps"]
            cost = deleteResults["cost"]
            insertResults = self._insert(expected)
            steps += insertResults["steps"]
            cost += insertResults["cost"]
            cost -= 0.001
        else:
            # Repair attributes
            for attr in [x for x in expected if x not in self._excludedAttrs]:
                if attr not in observed:
                    cost += 1
                    steps.append(
                        self._formatStep(observed, f"set {attr} to `{expected[attr]}`")
                    )
                elif observed[attr] != expected[attr]:
                    cost += 1
                    steps.append(
                        self._formatStep(
                            observed, f"change {attr} to `{expected[attr]}`"
                        )
                    )
            for attr in [
                x
                for x in observed
                if x not in expected and x not in self._excludedAttrs
            ]:
                cost += 1
                steps.append(self._formatStep(observed, f"remove {attr}"))

            # Repair children
            oc = observed[self._childrenAttr] if self._childrenAttr in observed else []
            ec = expected[self._childrenAttr] if self._childrenAttr in expected else []

            result = self._bipartiteMatchingDiff(oc, ec)
            cost += result["cost"]
            steps += [step for edit in result["edits"] for step in edit["steps"]]

        return {"op": EditType.REPAIR, "cost": cost, "steps": steps}

    def _bipartiteMatchingDiff(self, a, b):
        ops = []
        al = len(a)
        bl = len(b)
        n = max(al, bl)

        if n == 0:
            return {"cost": 0, "edits": []}

        for ai in range(n):
            row = []
            for bi in range(n):
                if ai < al:
                    if bi < bl:
                        row.append(self._repair(a[ai], b[bi]))
                    else:
                        row.append(self._delete(a[ai]))
                else:
                    row.append(self._insert(b[bi]))
            ops.append(row)

        # Project to 2D array of costs
        costs = np.array([[edit["cost"] for edit in row] for row in ops])

        # Perform Munkres assignment
        ri, ci = linear_sum_assignment(costs)
        assignments = zip(ri, ci)

        #  Map assignments back to list of operations.
        edits = [
            edit for edit in [ops[x[0]][x[1]] for x in assignments] if edit["cost"] != 0
        ]

        # Total up the costs.
        cost = sum([e["cost"] for e in edits])

        # Return cost and edits.
        return {"cost": cost, "edits": edits}
