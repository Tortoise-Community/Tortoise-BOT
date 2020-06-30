import os
import logging
from sys import stdout

from dotenv import load_dotenv

from bot.bot import Bot
from bot.non_blocking_file_handler import NonBlockingFileHandler


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")

file_handler = NonBlockingFileHandler("log.txt", encoding="utf-8")
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

console_logger = logging.getLogger("console")
console = logging.StreamHandler(stdout)
console.setFormatter(formatter)
console_logger.addHandler(console)

load_dotenv()
Bot().run(os.getenv("BOT_TOKEN"))
