from typing import Optional

from taskmates.core.workflow_engine.run import RUN


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = RUN.get()
    await signals.signals["execution_environment"].result.send_async({"result": result, "summary": summary})
    return result
