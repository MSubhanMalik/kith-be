from app.agent.registry import tool
from app.services.metrics import MetricsService


@tool(description="Get computed weekly metrics — tasks done, hours by goal, patterns")
async def get_week_metrics(week_of: str, ctx=None):
    service = MetricsService(ctx)
    return await service.get_week_metrics(week_of)


@tool(description="Compute and store weekly metrics from schedule and completion data")
async def compute_week_metrics(week_of: str, ctx=None):
    service = MetricsService(ctx)
    return await service.compute_week_metrics(week_of)
