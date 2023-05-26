from bot_module import bot
from os import environ

BOT_TOKEN = environ["BOT_TOKEN"]

competence_bot = bot.Competence_bot(bot_token=BOT_TOKEN)
def main():
    while True:
        try:
            competence_bot.run()
        except Exception as e:
            continue

if __name__=='__main__':
    main()