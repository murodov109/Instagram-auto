import os
import json
import time
import threading
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from instagrapi import Client

load_dotenv()

TG_TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

VIDEO_PATH = "video.mp4"
SESSION_FILE = "session.json"
CONFIG_FILE = "config.json"

posting_active = False
ig_client = None


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

def ig_login(username, password):
    cl = Client()
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)
    cl.login(username, password)
    cl.dump_settings(SESSION_FILE)
    return cl

def posting_loop():
    global posting_active, ig_client
    cfg = load_config()
    try:
        ig_client = ig_login(cfg["username"], cfg["password"])
    except Exception as e:
        print(f"Login xato: {e}")
        posting_active = False
        return

    while posting_active:
        cfg = load_config()
        n = cfg["counter"]
        caption = f"{cfg['caption']}\n\n#{n}".strip()
        try:
            if os.path.exists(VIDEO_PATH):
                ig_client.video_upload(VIDEO_PATH, caption=caption)
                print(f"Post #{n} qoyildi")
                cfg["counter"] = n + 1
                save_config(cfg)
            else:
                print("Video topilmadi")
        except Exception as e:
            print(f"Post xato: {e}")
            try:
                ig_client = ig_login(cfg["username"], cfg["password"])
            except:
                pass

        interval = cfg.get("interval", 3600)
        for _ in range(interval):
            if not posting_active:
                break
            time.sleep(1)


def admin_only(func):
    async def wrapper(update: Update, ctx, *args, **kwargs):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("Ruxsat yoq. Murojaat: @murodov_ads")
            return
        return await func(update, ctx, *args, **kwargs)
    return wrapper


@admin_only
async def start(update: Update, ctx):
    await update.message.reply_text(
        "Admin panel:\n\n"
        "/status — holat\n"
        "/start_post — boshlash\n"
        "/stop_post — toxtatish\n"
        "/set_interval 3600 — vaqt (soniya)\n"
        "/set_account login parol — akkaunt\n"
        "/set_caption matn — post matni\n"
        "/reset_counter — hisobni 1 ga qaytarish\n\n"
        "Video yuboring — video almashadi"
    )

async def start_unknown(update: Update, ctx):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bu bot shaxsiy. Murojaat: @murodov_ads")

@admin_only
async def status(update: Update, ctx):
    cfg = load_config()
    state = "Aktiv" if posting_active else "Toxtatilgan"
    mins = cfg.get("interval", 3600) // 60
    video = "bor" if os.path.exists(VIDEO_PATH) else "yoq"
    await update.message.reply_text(
        f"Holat: {state}\n"
        f"Akkaunt: @{cfg.get('username', '-')}\n"
        f"Interval: {mins} daqiqa\n"
        f"Keyingi post: #{cfg.get('counter', 1)}\n"
        f"Video: {video}"
    )

@admin_only
async def start_post(update: Update, ctx):
    global posting_active
    if posting_active:
        await update.message.reply_text("Allaqachon ishlayapti.")
        return
    if not os.path.exists(VIDEO_PATH):
        await update.message.reply_text("Avval video yuboring.")
        return
    posting_active = True
    threading.Thread(target=posting_loop, daemon=True).start()
    await update.message.reply_text("Postlash boshlandi.")

@admin_only
async def stop_post(update: Update, ctx):
    global posting_active
    posting_active = False
    await update.message.reply_text("Postlash toxtatildi.")

@admin_only
async def set_interval(update: Update, ctx):
    try:
        seconds = int(ctx.args[0])
        cfg = load_config()
        cfg["interval"] = seconds
        save_config(cfg)
        await update.message.reply_text(f"Interval {seconds // 60} daqiqa qilindi.")
    except:
        await update.message.reply_text("Ishlatish: /set_interval 3600")

@admin_only
async def set_account(update: Update, ctx):
    try:
        username, password = ctx.args[0], ctx.args[1]
        cfg = load_config()
        cfg["username"] = username
        cfg["password"] = password
        save_config(cfg)
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        await update.message.reply_text(f"Akkaunt ozgartirildi: @{username}")
    except:
        await update.message.reply_text("Ishlatish: /set_account login parol")

@admin_only
async def set_caption(update: Update, ctx):
    caption = " ".join(ctx.args)
    cfg = load_config()
    cfg["caption"] = caption
    save_config(cfg)
    await update.message.reply_text(f"Matn saqlandi.")

@admin_only
async def reset_counter(update: Update, ctx):
    cfg = load_config()
    cfg["counter"] = 1
    save_config(cfg)
    await update.message.reply_text("Hisoblagich 1 ga qaytarildi.")

@admin_only
async def receive_video(update: Update, ctx):
    await update.message.reply_text("Video yuklanmoqda...")
    file = await update.message.video.get_file()
    await file.download_to_drive(VIDEO_PATH)
    await update.message.reply_text("Video saqlandi.")


def main():
    app = Application.builder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("start_post", start_post))
    app.add_handler(CommandHandler("stop_post", stop_post))
    app.add_handler(CommandHandler("set_interval", set_interval))
    app.add_handler(CommandHandler("set_account", set_account))
    app.add_handler(CommandHandler("set_caption", set_caption))
    app.add_handler(CommandHandler("reset_counter", reset_counter))
    app.add_handler(MessageHandler(filters.VIDEO, receive_video))
    app.add_handler(MessageHandler(filters.ALL, start_unknown))
    print("Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
