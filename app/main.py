import base64
import bencodepy
import hashlib
import logging as log
import os
import signal
import sys
import telebot
import time

from telebot import types
from telegram_deluge_client import TelegramDelugeClient

AUTHORIZED_USERS = [
    int(x) for x in os.getenv("AUTHORIZED_USERS", "294967926,191151492").split(",")
]

bot = telebot.TeleBot(
    os.getenv("TELEGRAM_BOT_TOKEN"),
    threaded=False,
    parse_mode="Markdown",
)


def signal_handler(signal_number):
    print("Received signal " + str(signal_number) + ". Trying to end tasks and exit...")
    bot.stop_polling()
    sys.exit(0)


def log_and_send_message_decorator(fn):
    def wrapper(message):
        bot.send_message(message.chat.id, f"Executing your command, please wait...")
        log.info("[FROM {}] [{}]".format(message.chat.id, message.text))
        if message.chat.id in AUTHORIZED_USERS:
            reply = fn(message)
        else:
            reply = "Sorry, this is a private bot"
        log.info("[TO {}] [{}]".format(message.chat.id, reply))
        try:
            bot.send_message(message.chat.id, reply)
        except Exception as e:
            log.warning(f"Something went wrong:\n{e}")
            bot.send_message(
                message.chat.id, "Sorry, I can't send you reply. Report it to @Lestarby"
            )

    return wrapper


def generate_markup():
    markup = types.ReplyKeyboardMarkup()
    button_1 = types.KeyboardButton("❌ Delete")
    button_2 = types.KeyboardButton("⏸️ Pause")
    button_3 = types.KeyboardButton("▶️ Resume")

    markup.add(button_1, button_2, button_3)

    return markup


@bot.message_handler(commands=["start", "help"])
@log_and_send_message_decorator
def print_help_message(message):
    welcome_msg = (
        "\nWelcome to Deluge management bot!\n"
        "Send me magnet link or torrent file to add it to the download queue."
        "Send torrent name to get list of available operations with your torrents."
        "/list - List active torrents.\n"
        "/help - Print this message again."
    )
    if message.chat.first_name is not None:
        if message.chat.last_name is not None:
            reply = "Hello, {} {} {}".format(
                message.chat.first_name, message.chat.last_name, welcome_msg
            )
        else:
            reply = "Hello, {} {}".format(message.chat.first_name, welcome_msg)
    else:
        reply = "Hello, {} {}".format(message.chat.title, welcome_msg)
    return reply


@bot.message_handler(commands=["list"])
@log_and_send_message_decorator
def list_all_torrents(message):
    deluge = TelegramDelugeClient(message.chat.id)
    torrents = deluge.parse_torrents()
    reply = ""
    if torrents:
        for t in torrents:
            if t.state == "Paused":
                prefix = f"⏸️ *{t.progress}/100%*"
            else:
                prefix = (
                    "✅ *100/100%*"
                    if t.progress == 100
                    else f"🚀 *{t.progress}/100% ⌛ {t.eta_hr}*"
                )
            reply += f"{prefix} `{t.name}`\n"
    else:
        reply = "You don't have active torrents"
    return reply


@bot.message_handler(
    func=lambda m: m.text is not None and m.text.startswith(("magnet:?"))
)
@log_and_send_message_decorator
def add_new_torrent_by_magnet_link(message):
    deluge = TelegramDelugeClient(message.chat.id)
    magnet_link = message.text

    torrent_id = deluge.add_torrent(magnet_link)
    if not torrent_id:
        return f"Failed to add the torrent, try again"
    return f"Torrent was added ({torrent_id})"


@bot.message_handler(content_types=["document"])
@log_and_send_message_decorator
def add_new_torrent_by_file(message):
    deluge = TelegramDelugeClient(message.chat.id)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    torrent_file_name = "{}.torrent".format(time.strftime("%d%m%Y%H%M%S"))
    with open(torrent_file_name, "wb") as new_file:
        new_file.write(downloaded_file)
        metadata = bencodepy.decode_from_file(torrent_file_name)
        subj = metadata[b"info"]
        hashcontents = bencodepy.encode(subj)
        digest = hashlib.sha1(hashcontents).digest()
        b32hash = base64.b32encode(digest).decode()
        torrent_id = deluge.add_torrent("magnet:?xt=urn:btih:" + b32hash)
        os.remove(torrent_file_name)
        if not torrent_id:
            return f"Failed to add the torrent, try again"
        return f"Torrent was added ({torrent_id})"


@bot.message_handler(func=lambda m: True)
def modify_torrent(message):
    deluge = TelegramDelugeClient(message.chat.id)
    torrent_exists = None
    torrent_name = message.text

    torrents = deluge.parse_torrents()
    if torrents:
        for t in torrents:
            if t.name == torrent_name:
                torrent_exists = True
                markup = generate_markup()
                msg = bot.reply_to(
                    message,
                    f"Choose what to do with *{torrent_name}*",
                    reply_markup=markup,
                )
                bot.register_next_step_handler(
                    msg, lambda m: process_action(m, deluge, torrent_name)
                )
    if not torrent_exists:
        bot.send_message(
            message.chat.id, "Sorry, I don't know what to do with your message. Check /help"
        )


def process_action(message, torrent_client, torrent_name):
    markup = types.ReplyKeyboardRemove(selective=False)
    if message:
        action = message.text
        if action == "❌ Delete":
            torrent_client.delete_torrent_by_name(torrent_name)
            bot.reply_to(message, "Torrent removed", reply_markup=markup)
        if action == "⏸️ Pause":
            torrent_client.pause_torrent_by_name(torrent_name)
            bot.reply_to(message, "Torrent paused", reply_markup=markup)
        if action == "▶️ Resume":
            torrent_client.resume_torrent_by_name(torrent_name)
            bot.reply_to(message, "Torrent resumed", reply_markup=markup)
        return
    bot.reply_to(message, "Something is wrong, try again", reply_markup=markup)


def main():
    log.basicConfig(level=log.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("Bot was started.")
    signal.signal(signal.SIGINT, signal_handler)
    log.info("Starting bot polling...")
    bot.polling()


if __name__ == "__main__":
    main()
