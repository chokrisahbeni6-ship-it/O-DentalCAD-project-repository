"""Safe formatting for DICOM Decimal String test values."""
import math

def format_ds(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("DICOM DS cannot contain NaN or infinity")

    result = format(value, ".10g")
    if len(result) > 16:
        result = format(value, ".8e")

    if len(result) > 16:
        raise ValueError("Cannot represent value within DICOM DS limit")

    return result
