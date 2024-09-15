from typing import Optional

from taskmates.core.execution_environment import EXECUTION_ENVIRONMENT


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = EXECUTION_ENVIRONMENT.get().signals
    await signals.response.result.send_async({"result": result, "summary": summary})
    return result
