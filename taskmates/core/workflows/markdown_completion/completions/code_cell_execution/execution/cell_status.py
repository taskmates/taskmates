from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List


class CellExecutionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    FINISHED = "finished"
    ERROR = "error"
    INTERRUPTED = "interrupted"


@dataclass
class CellStatus:
    cell_id: str
    source: str
    status: CellExecutionStatus = CellExecutionStatus.PENDING
    sent_messages: List[Dict[str, Any]] = field(default_factory=list)
    received_messages: List[Dict[str, Any]] = field(default_factory=list)
    error_info: Dict[str, Any] = field(default_factory=dict)
    execution_count: int | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "source": self.source,
            "status": self.status.value,
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "error_info": self.error_info,
            "execution_count": self.execution_count,
        }


@dataclass
class KernelCellTracker:
    cells: Dict[str, CellStatus] = field(default_factory=dict)
    current_cell_id: str | None = None

    def add_cell(self, cell_id: str, source: str) -> None:
        self.cells[cell_id] = CellStatus(cell_id=cell_id, source=source)
        self.current_cell_id = cell_id

    def get_cell(self, cell_id: str) -> CellStatus | None:
        return self.cells.get(cell_id)

    def get_current_cell(self) -> CellStatus | None:
        if self.current_cell_id:
            return self.get_cell(self.current_cell_id)
        return None

    def record_sent_message(self, cell_id: str, message: Dict[str, Any]) -> None:
        if cell := self.get_cell(cell_id):
            cell.sent_messages.append(message)
            cell.status = CellExecutionStatus.EXECUTING

    def record_received_message(self, cell_id: str, message: Dict[str, Any]) -> None:
        if cell := self.get_cell(cell_id):
            cell.received_messages.append(message)
            msg_type = message.get("msg_type")

            if msg_type == "error":
                cell.status = CellExecutionStatus.ERROR
                cell.error_info = message.get("content", {})
            elif msg_type == "execute_reply":
                if cell.status != CellExecutionStatus.ERROR:
                    cell.status = CellExecutionStatus.FINISHED
                cell.execution_count = message.get("content", {}).get("execution_count")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cells": {cell_id: cell.to_dict() for cell_id, cell in self.cells.items()},
            "current_cell_id": self.current_cell_id
        }


def test_cell_status():
    cell = CellStatus(cell_id="123", source="print('hello')")
    assert cell.status == CellExecutionStatus.PENDING
    assert cell.sent_messages == []
    assert cell.received_messages == []

    cell_dict = cell.to_dict()
    assert cell_dict["cell_id"] == "123"
    assert cell_dict["source"] == "print('hello')"
    assert cell_dict["status"] == "pending"


def test_kernel_cell_tracker():
    tracker = KernelCellTracker()

    # Test adding a cell
    tracker.add_cell("123", "print('hello')")
    assert tracker.current_cell_id == "123"
    assert "123" in tracker.cells

    # Test recording sent message
    sent_msg = {"msg_id": "abc", "content": {"code": "print('hello')"}}
    tracker.record_sent_message("123", sent_msg)
    cell = tracker.get_cell("123")
    assert cell.status == CellExecutionStatus.EXECUTING
    assert cell.sent_messages == [sent_msg]

    # Test recording received message (success)
    success_msg = {"msg_type": "execute_reply", "content": {"execution_count": 1, "status": "ok"}}
    tracker.record_received_message("123", success_msg)
    assert cell.status == CellExecutionStatus.FINISHED
    assert cell.execution_count == 1

    # Test recording received message (error)
    tracker.add_cell("456", "1/0")
    error_msg = {"msg_type": "error", "content": {"ename": "ZeroDivisionError"}}
    tracker.record_received_message("456", error_msg)
    cell = tracker.get_cell("456")
    assert cell.status == CellExecutionStatus.ERROR
    assert cell.error_info["ename"] == "ZeroDivisionError"
