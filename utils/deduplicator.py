from hashlib import sha256
from typing import Set


class Deduplicator:
    """
    Simple in-memory deduplicator for a single request.
    """

    def __init__(self) -> None:
        self._seen: Set[str] = set()

    @staticmethod
    def compute_id(apply_url: str) -> str:
        return sha256(apply_url.encode("utf-8")).hexdigest()

    def is_new(self, apply_url: str) -> str | None:
        """
        Returns the computed id if this apply_url has not been seen before,
        otherwise returns None.
        """
        job_id = self.compute_id(apply_url)
        if job_id in self._seen:
            return None
        self._seen.add(job_id)
        return job_id

