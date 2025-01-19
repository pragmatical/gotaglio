class PersistentContext:
    # Class-level static context stack
    context_stack = []

    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        """Add the context when entering the block."""
        PersistentContext.context_stack.append(self.msg)

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Remove the context only if no exception occurred.
        If an exception occurs, leave the context on the stack.
        """
        if exc_type is None:
            # No exception occurred, clean up context
            PersistentContext.context_stack.pop()
        # If an exception occurred, do not clean up
        return False  # Do not suppress exceptions

    @classmethod
    def get_context(cls):
        """Retrieve the current context stack."""
        return " > ".join(cls.context_stack)

    @classmethod
    def clear_context(cls):
        """Clear the entire context stack."""
        cls.context_stack.clear()

    @classmethod
    def format_message(cls, exception):
        """
        Format an exception message with the current context stack.

        Args:
            exception (Exception): The exception to format.

        Returns:
            str: A formatted string including the exception and context.
        """
        context = cls.get_context()
        return f"Context: {context if context else 'No context available'}\nError: {exception}\n"
