from typing import Optional

from taskmates.core.execution_context import EXECUTION_CONTEXT


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = EXECUTION_CONTEXT.get()
    await signals.outputs.result.send_async({"result": result, "summary": summary})
    return result
