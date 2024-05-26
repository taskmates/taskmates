from typing import List, Dict, Any

class LastMessage:
    def __init__(self):
        self.recipient: str = None
        self.recipient_role: str = None
        self.code_cells: List[Dict[str, Any]] = []
