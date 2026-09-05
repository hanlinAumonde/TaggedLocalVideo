from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressFrame:
    """
    One report of how far a background task has got.

    Deliberately unit-agnostic: ``current``/``total`` are counted in whatever the task
    measures — bytes for a file copy, frames for a transcode, documents for a rescan — and
    ``unit`` names it for anyone rendering the frame. Transports are free to republish the
    numbers under their own field names.

    Frozen because a single frame is broadcast to every observer of a task; no consumer
    may edit what the others are about to read.
    """

    task_id: str
    status: str
    current: int
    total: int
    unit: str = "bytes"
    message: str | None = None

    @property
    def percentage(self) -> float:
        """
        Completion as a percentage, rounded to one decimal.

        A task whose total is unknown or not measurable reports 0 rather than raising.

        :return: Percentage complete, between 0 and 100.
        :rtype: float
        """
        if self.total <= 0:
            return 0.0
        return round(self.current / self.total * 100, 1)
