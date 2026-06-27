"""Currency conversion.

Every value/fee/cashflow must be FX-converted before it can be summed. Rates are
``to_usd`` (1 unit of currency = this many USD) as of the report date. To convert
between two non-USD currencies we go via USD, exactly as the dataset guide says.
"""

from __future__ import annotations


class FXConverter:
    """Convert amounts between currencies via USD using ``to_usd`` rates."""

    def __init__(self, to_usd: dict[str, float]) -> None:
        self._to_usd = dict(to_usd)

    def rate(self, currency: str) -> float:
        try:
            return self._to_usd[currency]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"No FX rate for currency {currency!r}") from exc

    def to_usd(self, amount: float, currency: str) -> float:
        return amount * self.rate(currency)

    def convert(self, amount: float, from_ccy: str, to_ccy: str) -> float:
        """Convert ``amount`` from ``from_ccy`` to ``to_ccy`` (via USD)."""
        if from_ccy == to_ccy:
            return amount
        return amount * self.rate(from_ccy) / self.rate(to_ccy)
