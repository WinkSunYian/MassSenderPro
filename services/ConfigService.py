import os


class ConfigService:
    def __init__(self, base_dir: str = None, class_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "class")
        if class_dir is None:
            class_dir = os.path.join(os.path.dirname(__file__), "..", "rosters")
        self.base_dir = os.path.abspath(base_dir)
        self.class_dir = os.path.abspath(class_dir)

    def load_config(self):
        raise NotImplementedError

    def save_config(self, config):
        raise NotImplementedError

    def get_current_class(self) -> str:
        class_file = os.path.join(self.class_dir, "class.txt")
        if os.path.exists(class_file):
            try:
                with open(class_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                return ""
        return ""

    def save_current_class(self, class_name: str):
        if not os.path.exists(self.class_dir):
            os.makedirs(self.class_dir, exist_ok=True)
        class_file = os.path.join(self.class_dir, "class.txt")
        with open(class_file, "w", encoding="utf-8") as f:
            f.write(class_name.strip())

    def get_class_roots(self, class_name: str) -> dict:
        if not class_name:
            class_name = self.get_current_class()
        if not class_name:
            raise ValueError("未指定班级名称")
        class_root = os.path.join(self.base_dir, class_name)
        rosters_dir = os.path.join(class_root, "rosters")
        logs_dir = os.path.join(class_root, "logs")
        os.makedirs(rosters_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        self._create_default_files(rosters_dir)
        return {
            "class_root": class_root,
            "rosters_dir": rosters_dir,
            "logs_dir": logs_dir,
        }

    def _create_default_files(self, rosters_dir: str):
        try:
            roster_txt_path = os.path.join(rosters_dir, "rosters.txt")
            if not os.path.exists(roster_txt_path):
                with open(roster_txt_path, "w", encoding="utf-8") as f:
                    f.write("")
        except Exception:
            pass

        try:
            roster_csv_path = os.path.join(rosters_dir, "rosters.csv")
            if not os.path.exists(roster_csv_path):
                with open(roster_csv_path, "w", encoding="utf-8") as f:
                    f.write("name,id\n")
        except Exception:
            pass

    def list_classes(self):
        if not os.path.exists(self.base_dir):
            return []
        return sorted([
            name for name in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, name))
        ])

    def class_exists(self, class_name: str) -> bool:
        if not class_name:
            return False
        class_root = os.path.join(self.base_dir, class_name)
        return os.path.isdir(class_root)
