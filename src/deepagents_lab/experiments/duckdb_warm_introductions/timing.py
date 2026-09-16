"""Measure cleanup that QuickJS performs inside the agent invocation."""

from time import perf_counter

from langchain_quickjs import CodeInterpreterMiddleware


class MeasuredCodeInterpreterMiddleware(CodeInterpreterMiddleware):
    """Track cleanup separately so the experiment can exclude it from latency.

    Each trial constructs a fresh instance. The trial captures this counter when
    ainvoke finishes, before its additional best-effort cleanup outside the timer.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cleanup_seconds = 0.0

    async def aafter_agent(self, state, runtime):
        started = perf_counter()
        try:
            return await super().aafter_agent(state, runtime)
        finally:
            self.cleanup_seconds += perf_counter() - started
