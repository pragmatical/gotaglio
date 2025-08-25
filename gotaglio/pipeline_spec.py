from pydantic import BaseModel, Field
from rich.console import Console
from typing import Any, Callable


class TurnLocator(BaseModel):
    index: int = Field(..., description="Turn index")
    isolated: bool = Field(False, description="Is the turn isolated")


class FormatterSpec(BaseModel):
    before_case: Callable[[Console, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents before each case"
    )
    after_case: Callable[[Console, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents after each case"
    )
    format_turn: Callable[[Console, int, dict[str, Any]], None] = Field(
        default=None, description="Function to generate contents for each turn"
    )


class ColumnSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Column name")
    params: dict[str, Any] = Field(
        {}, description="Rich formatting parameters for the column"
    )
    contents: Callable[[dict[str, Any]], Any] = Field(
        ..., description="Function to create the cell contents"
    )


def column_spec(
    name: str, contents: Callable[[dict[str, Any]], Any], **kwargs
) -> ColumnSpec:
    """
    Convenience factory creates ColumnSpec for use in SummarizerSpec.
    """
    return ColumnSpec(name=name, contents=contents, params=kwargs)


class SummarizerSpec(BaseModel):
    columns: list[ColumnSpec] = Field([], description="List of columns to summarize")


class PipelineSpec(BaseModel):
    name: str = Field(..., min_length=1, description="Pipeline name")
    description: str = Field(..., min_length=1, description="Pipeline description")
    configuration: dict[str, Any] = Field(..., description="Pipeline configuration")
    create_dag: Callable[[str, dict[str, Any], Any], Any] = Field(
        ..., description="Function to create the DAG"
    )
    expected: Callable[[dict[str, Any]], Any] = Field(
        default=None, description="Function that returns the expected result of a turn."
    )
    formatter: FormatterSpec | Callable = Field(
        default=None, description="Optional formatter spec or function"
    )
    passed_predicate: Callable[[dict[str, Any]], bool] = Field(
        default=lambda result: False,
        description="Function to determine if the summarization passed",
    )
    summarizer: SummarizerSpec | Callable = Field(
        default=None, description="Optional summarizer spec or function"
    )


class PipelineSpecs:
    """
    Registry for PipelineSpec objects.
    """

    def __init__(self, pipelines: list[PipelineSpec]):
        self.pipelines = pipelines

    def get(self, name: str) -> PipelineSpec | None:
        """
        Retrieve a PipelineSpec by name.
        """
        spec = next((p for p in self.pipelines if p.name == name), None)
        if spec is None:
            raise ValueError(f"Cannot find pipeline '{name}'.")
        return spec

    def __iter__(self):
        return iter(self.pipelines)

    def __len__(self):
        return len(self.pipelines)


# Used by stage functions to get inputs
def get_stages(context, turn_index=None):
    """
    Returns the portion of the context that corresponds to the pipeline
    `stages` results for either the most recently processed turn or a
    specified turn.
    """
    return get_result(context, turn_index)["stages"]


# Used by summarize() to get `succeeded`
def get_result(context, turn_index=None):
    """
    Returns the portion of the context that corresponds to the
    results of a test run, for either the most recently processed
    turn or a specified turn. Returns the entire context if the
    test case does not use turns.
    """
    if "turns" in context["case"]:
        if turn_index is None:
            turn_index = len(context["turns"]) - 1
        return context["turns"][turn_index]
    return context


# Used by stage functions and model mocks to get inputs.
def get_turn(context, turn_index=None):
    """
    Returns the portion of the context's test case that defines a
    turn. If the case uses turns, it will return the last turn if
    no `turn_index` is specified. The last turn corresponds to the
    current turn in `run_dag()`. Returns the case itself if the
    case does not use turns.
    """
    if "turns" in context["case"]:
        if turn_index is None:
            turn_index = len(context["turns"]) - 1
        return context["case"]["turns"][turn_index]
    return context["case"]


def get_turn_index(context):
    """
    Returns the index of the current turn in the context, or None
    if the case does not use turns.
    """
    if "turns" in context["case"]:
        return len(context["turns"]) - 1
    return None


def uses_turns(result):
    """
    Check if the test case `result` is based on uses turns.
    """
    return "turns" in result["case"]
