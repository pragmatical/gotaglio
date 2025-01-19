import threading
from contextlib import contextmanager

class ExceptionContext:
    _context = threading.local()

    @classmethod
    def get_context(cls):
        return getattr(cls._context, "value", [])

    @classmethod
    def add_context(cls, context):
        if not hasattr(cls._context, "value"):
            cls._context.value = []
        cls._context.value.append(context)

    @classmethod
    def remove_context(cls):
        if hasattr(cls._context, "value") and cls._context.value:
            cls._context.value.pop()

@contextmanager
def context(msg):
    ExceptionContext.add_context(msg)
    try:
        yield
    finally:
        ExceptionContext.remove_context()

# Custom exception formatter
def format_exception(e):
    context = ExceptionContext.get_context()
    return f"Error: {e}\nContext: {' > '.join(context)}"
