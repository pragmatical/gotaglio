from io import StringIO
from rich.console import Console
from rich.markdown import Markdown as RichMarkdown
from rich.text import Text


css_fix = """
    <style>
        pre, code {
            line-height: 1.2 !important;  /* Reduce extra spacing */
            margin: 0 !important;
            padding: 5px !important;
            background-color: #f8f8f8 !important;  /* Light gray background */
        }
    </style>
"""


class MyConsole:
    def __init__(self):
        self._items = []

    def print(self, text=""):
        self._items.append(text)

    def export_text(self):
        return "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class MakeConsole:
    """
    A class to create a console for the Gotaglio application.
    """

    def __init__(self):
        """
        Initializes the MakeConsole class.
        """
        self._output_buffer = None
        self._console = None

    def __call__(self, content_type="text/plain"):
        """
        Creates a console for the Gotaglio application.
        """
        if self._output_buffer:
            raise Exception(
                "Console already created. Call display() to show the output."
            )
        self._content_type = content_type
        self._output_buffer = StringIO()
        # self._console = Console(file=self._output_buffer, force_terminal=True, record=True, disable=True)
        # self._console = MyConsole()
        # self._console = Console(record=True, quiet=True)
        # self._console = Console(record=True, force_jupyter=False)
        # self._console = Console(file=self._output_buffer, record=True) # Double output
        # self._console = Console(file=self._output_buffer, record=True, quiet=True) # No output

        # self._console = Console(force_terminal=True)    # Works but has control characters
        self._console = Console(force_terminal=False)
        self._console.begin_capture()
        return self._console

    def render(self):
        if not self._output_buffer:
            raise Exception("No output buffer found. Did you call __call__() first?")
        # text = self._output_buffer.getvalue()
        # text = self._console.export_text()
        text = self._console.end_capture()
        # text = self._console.export_text()
        # text = " HELLO WORLD "

        try:
            from IPython import get_ipython
            from IPython.display import display, HTML, Markdown

            ipython = get_ipython()
            if ipython and "IPKernelApp" in ipython.config:
                if self._content_type == "text/html":
                    display(HTML(text))
                elif self._content_type == "text/markdown":
                    # x = Markdown(text)
                    # display(Markdown("# Hello, **Markdown** in Jupyter! 🎉\n\n- Item 1\n- Item 2\n\n[Click here](https://example.com)"))

                    # text = remove_ansi_escape_sequences(text)
                    text = Text.from_ansi(text).plain
                    # display(text)  # All on one line

                    # display(HTML(css_fix))  # Add CSS fix
                    display(Markdown(text))

                    # display(RichMarkdown(text))
                else:
                    display(HTML("<pre>" + text + "</pre>"))
                return
        except Exception:
            pass
        console = Console()
        console.print(text)


import re


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F][0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)
