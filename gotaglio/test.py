from rich.console import Console
from io import StringIO
# from IPython.display import Markdown, display

class RichMarkdownCapture:
    def __init__(self):
        """Initialize the console and start capturing output."""
        self._capture_buffer = StringIO()
        # self.console = Console()
        self.console = Console(file=self._capture_buffer, force_terminal=True)
        # self.console.file = self._capture_buffer  # Redirect output to StringIO

    def print(self, *args, **kwargs):
        """Capture output using console.print()."""
        self.console.print(*args, **kwargs)

    def display(self):
        """Stop capturing and render the accumulated markdown."""
        rich_output = self._capture_buffer.getvalue()
        print("=================")
        print(rich_output)
        # display(Markdown(rich_output))  # Display as a single markdown block

# ✅ Example Usage
rich_md = RichMarkdownCapture()
rich_md.print("# This is a Heading", style="bold blue")
rich_md.print("## This is a Subheading", style="bold green")
rich_md.print("- Item 1")
rich_md.print("- Item 2")
rich_md.print("- **Bold Text** and *Italic Text*")

# Call display to show the entire markdown at once
rich_md.display()
