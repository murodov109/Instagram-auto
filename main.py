import os
import json
import time
import asyncio
import threading
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from instagrapi import Client as IgClient

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

VIDEO_PATH = os.path.abspath("video.mp4")
SESSION_FILE = "ig_session.json"
CONFIG_FILE = "config.json"

posting_active = False
ig_client = None
loop = None

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "counter": 1,
        "interval": 3600,
        "username": os.getenv("IG_USERNAME", ""),
        "password": os.getenv("IG_PASSWORD", ""),
        "caption": ""
    }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


def send_msg(text):
    if loop:
        asyncio.run_coroutine_threadsafe(
            app.send_message(ADMIN_ID, text), loop
        )


def ig_login(username, password):
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    cl = IgClient()
    cl.login(username, password)
    cl.dump_settings(SESSION_FILE)
    return cl


def posting_loop():
    global posting_active, ig_client
    cfg = load_config()

    send_msg("Instagram-ga kirilmoqda...")
    try:
        ig_client = ig_login(cfg["username"], cfg["password"])
        send_msg(f"Login muvaffaqiyatli: @{cfg['username']}")
    except Exception as e:
        send_msg(f"Login xato: {e}")
        posting_active = False
        return

    while posting_active:
        cfg = load_config()
        n = cfg["counter"]
        caption = f"{cfg['caption']}\n\n#{n}".strip()
        try:
            if os.path.exists(VIDEO_PATH):
                send_msg(f"Post #{n} yuklanmoqda...")
                ig_client.video_upload(VIDEO_PATH, caption=caption)
                cfg["counter"] = n + 1
                save_config(cfg)
                send_msg(f"Post #{n} muvaffaqiyatli qoyildi!")
            else:
                send_msg(f"Video topilmadi: {VIDEO_PATH}")
        except Exception as e:
            send_msg(f"Post xato: {e}")
            try:
                ig_client = ig_login(cfg["username"], cfg["password"])
            except Exception as e2:
                send_msg(f"Qayta login xato: {e2}")

        interval = cfg.get("interval", 3600)
        for _ in range(interval):
            if not posting_active:
                break
            time.sleep(1)

    send_msg("Postlash toxtatildi.")


def admin_filter(_, __, msg: Message):
    return msg.from_user and msg.from_user.id == ADMIN_ID


admin = filters.create(admin_filter)


@app.on_message(filters.command("start") & admin)
async def cmd_start(client, msg: Message):
    await msg.reply(
        "Admin panel:\n\n"
        "/status — holat\n"
        "/start_post — postlashni boshlash\n"
        "/stop_post — toxtatish\n"
        "/set_interval 3600 — interval (soniya)\n"
        "/set_account login parol — akkaunt\n"
        "/set_caption matn — post matni\n"
        "/reset_counter — hisobni 1 ga qaytarish\n\n"
        "Video yuboring — video almashadi"
    )


@app.on_message(filters.command("start") & ~admin)
async def cmd_start_unknown(client, msg: Message):
    await msg.reply("Bu bot shaxsiy. Murojaat: @murodov_ads")


@app.on_message(filters.command("status") & admin)
async def cmd_status(client, msg: Message):
    cfg = load_config()
    state = "Aktiv" if posting_active else "Toxtatilgan"
    mins = cfg.get("interval", 3600) // 60
    video = "bor" if os.path.exists(VIDEO_PATH) else "yoq"
    await msg.reply(
        f"Holat: {state}\n"
        f"Akkaunt: @{cfg.get('username', '-')}\n"
        f"Interval: {mins} daqiqa\n"
        f"Keyingi post: #{cfg.get('counter', 1)}\n"
        f"Video: {video}"
    )


@app.on_message(filters.command("start_post") & admin)
async def cmd_start_post(client, msg: Message):
    global posting_active, loop
    if posting_active:
        await msg.reply("Allaqachon ishlayapti.")
        return
    if not os.path.exists(VIDEO_PATH):
        await msg.reply(f"Avval video yuboring.")
        return
    loop = asyncio.get_event_loop()
    posting_active = True
    threading.Thread(target=posting_loop, daemon=True).start()
    await msg.reply("Postlash boshlandi.")


@app.on_message(filters.command("stop_post") & admin)
async def cmd_stop_post(client, msg: Message):
    global posting_active
    posting_active = False
    await msg.reply("Toxtatilmoqda...")


@app.on_message(filters.command("set_interval") & admin)
async def cmd_set_interval(client, msg: Message):
    try:
        seconds = int(msg.command[1])
        cfg = load_config()
        cfg["interval"] = seconds
        save_config(cfg)
        await msg.reply(f"Interval {seconds // 60} daqiqa qilindi.")
    except:
        await msg.reply("Ishlatish: /set_interval 3600")


@app.on_message(filters.command("set_account") & admin)
async def cmd_set_account(client, msg: Message):
    try:
        username = msg.command[1]
        password = msg.command[2]
        cfg = load_config()
        cfg["username"] = username
        cfg["password"] = password
        save_config(cfg)
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        await msg.reply(f"Akkaunt ozgartirildi: @{username}")
    except:
        await msg.reply("Ishlatish: /set_account login parol")


@app.on_message(filters.command("set_caption") & admin)
async def cmd_set_caption(client, msg: Message):
    caption = " ".join(msg.command[1:])
    cfg = load_config()
    cfg["caption"] = caption
    save_config(cfg)
    await msg.reply("Matn saqlandi.")


@app.on_message(filters.command("reset_counter") & admin)
async def cmd_reset_counter(client, msg: Message):
    cfg = load_config()
    cfg["counter"] = 1
    save_config(cfg)
    await msg.reply("Hisoblagich 1 ga qaytarildi.")


@app.on_message(filters.video & admin)
async def receive_video(client, msg: Message):
    await msg.reply("Video yuklanmoqda...")
    downloaded = await msg.download()
    if downloaded:
        os.replace(downloaded, VIDEO_PATH)
        await msg.reply(f"Video saqlandi.")
    else:
        await msg.reply("Xato: video saqlanmadi.")


@app.on_message(~admin)
async def unknown_user(client, msg: Message):
    await msg.reply("Bu bot shaxsiy. Murojaat: @murodov_ads")


if __name__ == "__main__":
    print("Bot ishga tushdi")
    app.run()
