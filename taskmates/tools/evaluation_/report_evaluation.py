from typing import Optional

from taskmates.signals.signals import SIGNALS


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = SIGNALS.get()
    await signals.output.return_value.send_async({"result": result, "summary": summary})
    return result
