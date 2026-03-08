from sqlalchemy.ext.asyncio import AsyncSession


async def record_metric(
    db: AsyncSession,
    metric_name: str,
    metric_value: float,
    tags: dict | None = None,
) -> None:
    """Record a metric data point to the metrics table.

    Args:
        db: Database session.
        metric_name: Dot-separated metric name (e.g. "api.request.count").
        metric_value: Numeric value to record.
        tags: Optional key-value tags for filtering/grouping.
    """
    # TODO: implement in monitoring step
    raise NotImplementedError
