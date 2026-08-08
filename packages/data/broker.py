from dataclasses import dataclass

from packages.core.models import OrderIntent


@dataclass(frozen=True)
class Execution:
    order_id: str
    status: str
    intent: OrderIntent


class PaperBroker:
    """In-memory broker. No real-money orders can leave this process."""

    def submit(self, intent: OrderIntent) -> Execution:
        order_id = f"paper-{intent.created_at.timestamp_ns()}"
        return Execution(order_id, "filled", intent)
