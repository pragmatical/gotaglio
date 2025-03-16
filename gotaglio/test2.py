import os
import sys

# Add the parent directory to the sys.path so that we can import from the
# gotaglio package, as if it had been installed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gotaglio.make_console import MakeConsole

# ✅ Example Usage
make_console = MakeConsole()
console2 = make_console("text/markdown")
console2.print("# This is a Heading", style="bold blue")
console2.print("## This is a Subheading", style="bold green")
console2.print("- Item 1")
console2.print("- Item 2")
console2.print("- **Bold Text** and *Italic Text*")

print("=================")

# Call display to show the entire markdown at once
make_console.render()
