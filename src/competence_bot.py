from bot_module import bot
from os import environ

BOT_TOKEN = environ["BOT_TOKEN"]

competence_bot = bot.Competence_bot(bot_token=BOT_TOKEN)
competence_bot.run()
