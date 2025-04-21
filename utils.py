from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import timedelta
from time import perf_counter


@dataclass
class stopwatch(AbstractContextManager):
    name: str = "Timer"
    start: int = field(default_factory=perf_counter, init=False)
    log: bool = True

    def get_time_ms(self):
        return (perf_counter() - self.start) * 1000

    def get_print_string(self):
        duration = timedelta(milliseconds=self.get_time_ms())

        return f"⏱ {duration} ⮜ {self.name}"

    def done(self):
        if self.log:
            print(self.get_print_string())

    def __enter__(self):
        if self.log:
            print(f"⏱ {self.name}...", end="\r")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.done()
        return False
