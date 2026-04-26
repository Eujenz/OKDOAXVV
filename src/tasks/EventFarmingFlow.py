from src.tasks.FlowRunnerTask import FlowRunnerTask


class EventFarmingFlow(FlowRunnerTask):
    """自動刷活動 — 由 flows/event_farming.json 驅動。"""
    flow_file = "flows/event_farming.json"
