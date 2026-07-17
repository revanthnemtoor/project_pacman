from datetime import datetime


class BuilderLogger:

    @staticmethod
    def info(message):

        now = datetime.now().strftime("%H:%M:%S")

        print(f"[{now}] {message}")
