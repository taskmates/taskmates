from typing import Optional

from taskmates.workflow_engine.run import RUN


async def report_evaluation(summary: Optional[str], result: bool):
    """
    Report the result of an evaluation.

    :param summary: short summary of the evaluation
    :param result: the result of the evaluation
    :return: success
    """
    signals = RUN.get()
    await signals.signals["output_streams"].result.send_async({"result": result, "summary": summary})
    return result
