import html
import logging

import tomlkit
from telegram import Update

from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler

from .rss import get_unseen_entries

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"start: {update=}, {context=}")
    await update.message.reply_text(
        "Hei! Tämä botti ei vielä osaa kovin monta temppua. "
        "Tällä hetkellä se vain seuraa matematiikkavalmennuksen sivuston uutisia ja lähettää ne chattiin."
    )


async def fetch_feed_callback(context: CallbackContext) -> None:
    """Scheduled task to fetch the RSS feed and send to group if there's a new entry."""
    logger.info(f"fetch callback: {context=}")
    url = context.bot_data["feed_url"]
    max: int = context.bot_data.get("feed_max", 1)
    chat_id = context.bot_data["chat_id"]
    entries = get_unseen_entries(url)[-max:]
    for entry in entries:
        text = f'☞ <a href="{entry.link}"><b>{html.escape(entry.title)}</b></a>'
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


def main():
    with open("config.toml", "rt") as f:
        config = tomlkit.load(f)
        telegram = config.get("telegram")
        feed = config.get("feed")
    if not telegram or not feed:
        raise Exception("No configuration found in config.toml")
    token = telegram.get("token")
    app = ApplicationBuilder().token(token).build()
    app.bot_data["chat_id"] = telegram["chat_id"]
    app.bot_data["feed_url"] = feed["url"]
    app.bot_data["feed_max"] = feed["max"]

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))

    # Schedule the task to fetch the RSS feed every 10 minutes
    job_queue = app.job_queue
    job_queue.run_repeating(fetch_feed_callback, interval=600)
    job_queue.run_once(
        lambda ctx: ctx.bot.set_my_commands(
            [("start", "Start the bot"), ("help", "Help with the bot")]
        ),
        0,
    )

    app.run_polling()


if __name__ == "__main__":
    main()
