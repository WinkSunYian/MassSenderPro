class WeWorkAutoService:
    def search_and_open_user(self, user_id: str) -> bool:
        raise NotImplementedError

    def send_text(self, text: str):
        raise NotImplementedError

    def send_file(self, file_path: str):
        raise NotImplementedError

    def close_chat(self):
        raise NotImplementedError
