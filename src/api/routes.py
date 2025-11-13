from fastapi import APIRouter
import random
import decimal

router = APIRouter()

def _format_to_5dec(value):
    d = decimal.Decimal(str(value))
    return float(d.quantize(decimal.Decimal("0.00001")))

@router.get("/api/gauges")
async def get_gauges():
    """
    Returns 8 random gauge readings (0.00000 - 90.00000), accurate to 5 decimals.
    """
    values = [random.uniform(0, 90) for _ in range(8)]
    values = [_format_to_5dec(v) for v in values]

    return {
        "gauges": [
            {"id": i + 1, "value": values[i], "min": 0.0, "max": 90.0, "precision": 5}
            for i in range(8)
        ]
    }