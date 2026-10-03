"""Programmatic calculation tools ensuring arithmetic accuracy without LLM hallucination."""

import time
from typing import Any, Dict, List, Optional
from app.tools.base_tool import BaseTool, ToolResult, tool_registry


class CalculateMetricTool(BaseTool):
    """Calculates growth rates, margins, percentage differences, and statistical metrics programmatically."""

    name = "calculate_metric"
    description = "Executes deterministic mathematical and financial calculations without LLM arithmetic errors."
    parameters = {
        "operation": "Type of calculation: 'growth_rate', 'profit_margin', 'ratio', 'percentage_change', 'sum', 'difference'",
        "current": "Current period or target value (float)",
        "previous": "Previous period or base value (float)",
        "denominator": "Denominator for ratio or margin (float)",
        "numerator": "Numerator for ratio or margin (float)",
        "values": "Optional list of float values for aggregation"
    }

    def execute(
        self,
        operation: str,
        current: Optional[float] = None,
        previous: Optional[float] = None,
        numerator: Optional[float] = None,
        denominator: Optional[float] = None,
        values: Optional[List[float]] = None,
        **kwargs
    ) -> ToolResult:
        start_t = time.perf_counter()
        op = operation.lower()

        try:
            if op in ("growth_rate", "percentage_change", "yoy_growth"):
                if current is None or previous is None:
                    return ToolResult(success=False, data=None, error="Both 'current' and 'previous' values are required for growth calculations.")
                if previous == 0:
                    return ToolResult(success=False, data=None, error="Previous value cannot be zero for percentage change.")
                
                abs_change = current - previous
                pct_change = (abs_change / abs(previous)) * 100.0
                result = {
                    "operation": op,
                    "previous": previous,
                    "current": current,
                    "absolute_change": round(abs_change, 2),
                    "percentage_change": round(pct_change, 2),
                    "direction": "increase" if abs_change > 0 else ("decrease" if abs_change < 0 else "neutral"),
                    "formatted_string": f"{'+' if pct_change > 0 else ''}{pct_change:.2f}% (from {previous} to {current})"
                }
                return ToolResult(success=True, data=result, execution_time_ms=(time.perf_counter() - start_t) * 1000)

            elif op in ("profit_margin", "margin", "ratio"):
                num = numerator if numerator is not None else current
                den = denominator if denominator is not None else previous
                if num is None or den is None:
                    return ToolResult(success=False, data=None, error="Both numerator and denominator are required for margin/ratio.")
                if den == 0:
                    return ToolResult(success=False, data=None, error="Denominator cannot be zero.")

                ratio = num / den
                margin_pct = ratio * 100.0
                result = {
                    "operation": op,
                    "numerator": num,
                    "denominator": den,
                    "ratio": round(ratio, 4),
                    "margin_percentage": round(margin_pct, 2),
                    "formatted_string": f"{margin_pct:.2f}%"
                }
                return ToolResult(success=True, data=result, execution_time_ms=(time.perf_counter() - start_t) * 1000)

            elif op == "difference":
                val1 = current if current is not None else 0.0
                val2 = previous if previous is not None else 0.0
                diff = val1 - val2
                result = {
                    "operation": op,
                    "value1": val1,
                    "value2": val2,
                    "difference": round(diff, 2)
                }
                return ToolResult(success=True, data=result, execution_time_ms=(time.perf_counter() - start_t) * 1000)

            elif op in ("sum", "average", "stats"):
                if not values:
                    return ToolResult(success=False, data=None, error="List of 'values' is required for statistical aggregation.")
                s = sum(values)
                avg = s / len(values)
                result = {
                    "operation": op,
                    "count": len(values),
                    "sum": round(s, 2),
                    "mean": round(avg, 2),
                    "min": min(values),
                    "max": max(values)
                }
                return ToolResult(success=True, data=result, execution_time_ms=(time.perf_counter() - start_t) * 1000)

            else:
                return ToolResult(success=False, data=None, error=f"Unknown calculation operation: {operation}")

        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e), execution_time_ms=(time.perf_counter() - start_t) * 1000)


calc_tool = CalculateMetricTool()
tool_registry.register(calc_tool)
