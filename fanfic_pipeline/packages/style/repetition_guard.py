from typing import List

class RepetitionGuard:
    def __init__(self, max_history: int = 5):
        self.history: List[str] = []
        self.max_history = max_history

    def record_chapter(self, text: str):
        self.history.append(text)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_overused_phrases(self) -> List[str]:
        return []
