from typing import List

from models.roster_item import RosterItem


class RosterService:
    def load_from_excel(self, path: str, payload: list = None) -> List[RosterItem]:
        raise NotImplementedError

    def load_from_txt(self, path: str, payload: list = None) -> List[RosterItem]:
        raise NotImplementedError

    def load_from_csv(self, path: str, payload: list = None) -> List[RosterItem]:
        raise NotImplementedError

    def save_failed_roster(self, failed: List[str]):
        raise NotImplementedError