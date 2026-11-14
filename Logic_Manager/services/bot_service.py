from Data_Manager.repositories.bot_repo import BotRepo
from results.success import Success
from results.result import Result
from results.error import Error


class BotService:
    def __init__(self, bot_repo: BotRepo) -> Result:
        self.bot_repo = bot_repo

    def add_bot(self, student_id: str, bot_id: str) -> Result:
        add_bot_success = self.bot_repo.add_bot(bot_id, student_id)
        return Success("Bot added") if add_bot_success else Error("Bot Exists")

    def get_student_id(self, bot_id: str) -> Result:
        get_student_id_result = self.bot_repo.get_student_id(bot_id)
        if get_student_id_result is None:
            return Error("Student ID Not associated with bot")
        return Success(get_student_id_result)

    def logout(self, bot_id: str) -> Result:
        logout_result = self.bot_repo.remove_bot(bot_id=bot_id)
        if not logout_result:
            return Error("Telegram ID not found")
        return Success("Logged out")
