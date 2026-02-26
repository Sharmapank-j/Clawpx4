"""automation/scheduler.py — APScheduler-based task scheduler for Clawpx4.

Provides a thin wrapper around APScheduler's BackgroundScheduler so that the
rest of the codebase can schedule recurring or one-shot tasks without coupling
to APScheduler internals.

Environment variables:
    SCHEDULER_TIMEZONE – timezone for cron/interval jobs (default: UTC)

Usage::

    from automation.scheduler import get_scheduler

    sched = get_scheduler()

    # Add a recurring job (every 5 minutes)
    @sched.interval_job(minutes=5)
    def my_task():
        print("Running every 5 minutes")

    # Add a cron job (every day at 08:00)
    @sched.cron_job(hour=8, minute=0)
    def morning_summary():
        print("Good morning!")

    sched.start()   # called automatically on first use
    sched.stop()    # call on shutdown
"""

from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Lightweight APScheduler wrapper with decorator helpers."""

    def __init__(self, timezone: Optional[str] = None) -> None:
        self._timezone = timezone or os.getenv("SCHEDULER_TIMEZONE", "UTC")
        self._scheduler = None  # lazy init

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _get_scheduler(self):
        """Lazily create and return the BackgroundScheduler."""
        if self._scheduler is None:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
            except ImportError as exc:
                raise ImportError(
                    "APScheduler is not installed. Run: pip install apscheduler"
                ) from exc
            self._scheduler = BackgroundScheduler(timezone=self._timezone)
            logger.info("Scheduler initialised (timezone=%s)", self._timezone)
        return self._scheduler

    def start(self) -> None:
        """Start the background scheduler (idempotent)."""
        sched = self._get_scheduler()
        if not sched.running:
            sched.start()
            logger.info("Scheduler started.")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    @property
    def running(self) -> bool:
        return bool(self._scheduler and self._scheduler.running)

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_interval_job(
        self, func: Callable, job_id: Optional[str] = None, **interval_kwargs: Any
    ) -> None:
        """Schedule *func* to run at a fixed interval.

        Args:
            func:             Callable to schedule.
            job_id:           Optional unique identifier.
            **interval_kwargs: Passed to APScheduler's ``IntervalTrigger``
                               (e.g. ``minutes=5``, ``hours=1``).
        """
        sched = self._get_scheduler()
        sched.add_job(
            func,
            trigger="interval",
            id=job_id or func.__name__,
            replace_existing=True,
            **interval_kwargs,
        )
        logger.debug("Added interval job: %s %s", job_id or func.__name__, interval_kwargs)

    def add_cron_job(
        self, func: Callable, job_id: Optional[str] = None, **cron_kwargs: Any
    ) -> None:
        """Schedule *func* using a cron expression.

        Args:
            func:           Callable to schedule.
            job_id:         Optional unique identifier.
            **cron_kwargs:  Passed to APScheduler's ``CronTrigger``
                            (e.g. ``hour=8``, ``minute=0``).
        """
        sched = self._get_scheduler()
        sched.add_job(
            func,
            trigger="cron",
            id=job_id or func.__name__,
            replace_existing=True,
            **cron_kwargs,
        )
        logger.debug("Added cron job: %s %s", job_id or func.__name__, cron_kwargs)

    def remove_job(self, job_id: str) -> None:
        """Remove the job with *job_id* (no-op if not found)."""
        sched = self._get_scheduler()
        try:
            sched.remove_job(job_id)
        except Exception:
            pass

    def list_jobs(self) -> list:
        """Return a list of scheduled job metadata dicts."""
        sched = self._get_scheduler()
        return [
            {"id": job.id, "next_run": str(job.next_run_time)}
            for job in sched.get_jobs()
        ]

    # ------------------------------------------------------------------
    # Decorator helpers
    # ------------------------------------------------------------------

    def interval_job(self, **interval_kwargs: Any) -> Callable:
        """Decorator — schedule the wrapped function at a fixed interval."""
        def decorator(func: Callable) -> Callable:
            self.add_interval_job(func, **interval_kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def cron_job(self, **cron_kwargs: Any) -> Callable:
        """Decorator — schedule the wrapped function via cron."""
        def decorator(func: Callable) -> Callable:
            self.add_cron_job(func, **cron_kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator


# Module-level singleton
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """Return the module-level :class:`Scheduler` singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
