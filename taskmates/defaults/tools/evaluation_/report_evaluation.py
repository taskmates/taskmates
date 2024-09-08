from typing import Optional

from taskmates.core.signals import SIGNALS


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = SIGNALS.get()
    await signals.output.result.send_async({"result": result, "summary": summary})
    return result