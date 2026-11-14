"""Telegram presentation using the same profile/candidate formatting as the CLI."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from IO_Manager.console_io import ConsoleIO


class TelegramIO:
    @staticmethod
    def keyboard(rows):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=data) for label, data in row]
            for row in rows
        ])

    async def send(self, update, text, rows=None):
        # 1800 Unicode characters also fit Telegram's UTF-16 limit with emoji.
        text = str(text) or " "
        chunks = [text[i:i + 1800] for i in range(0, len(text), 1800)]
        for index, chunk in enumerate(chunks):
            markup = self.keyboard(rows) if rows and index == len(chunks) - 1 else None
            await update.effective_message.reply_text(chunk, reply_markup=markup)

    @staticmethod
    def profile(answers):
        lines = []
        ConsoleIO(write=lines.append).show_profile(answers)
        return "\n".join(lines)

    @staticmethod
    def candidate(candidate):
        lines = []
        ConsoleIO(write=lines.append).show_candidate(candidate)
        return "\n".join(lines)

    @staticmethod
    def connection(result):
        return ConsoleIO().format_recommendations(result)
