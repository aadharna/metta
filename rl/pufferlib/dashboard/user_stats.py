
import numpy as np
from rich.table import Table

from .dashboard import DashboardComponent
from .dashboard import c1, b1, c2, b2, c3, ROUND_OPEN

class UserStats(DashboardComponent):
    def __init__(self, stats: dict, max_stats=5):
        super().__init__()
        self.max_stats = max_stats
        self.stats = stats

    def render(self):
        table = Table(box=ROUND_OPEN, expand=True, pad_edge=False)
        table.add_column(f"{c1}User Stats", justify="left", width=20)
        table.add_column(f"{c1}Value", justify="right", width=10)
        i = 0
        for metric, value in self.stats.items():
            if i >= self.max_stats:
                break
            try: # Discard non-numeric values
                int(value)
            except Exception as _:
                continue

            table.add_row(f'{c2}{metric}', f'{b2}{value:.3f}')
            i += 1
        return table
