import os
import traceback
from pathlib import Path
from dotenv import load_dotenv
from bot import Bot


load_dotenv()
if os.environ.get("DEBUG", "false").lower() == "true":
    banned_extensions = ("security", "tortoise_server", "verification",)
    default_prefix = "."
    print(f"Debug bot banned extension: {banned_extensions}")
else:
    banned_extensions = ("socket_comm",)
    default_prefix = "t."
    print(f"Main bot banned extension: {banned_extensions}")


if __name__ == "__main__":
    bot = Bot(prefix=default_prefix)
    for extension_path in Path("./cogs").glob("*.py"):
        extension_name = extension_path.stem
        if extension_name in banned_extensions:
            continue

        dotted_path = f"cogs.{extension_name}"
        try:
            bot.load_extension(dotted_path)
            print(f"\t loaded {dotted_path}")
        except Exception as e:
            traceback_msg = traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            print(f"Failed to load cog {dotted_path} - traceback:{traceback_msg}")

    bot.run(os.getenv("BOT_TOKEN"))

