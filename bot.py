"""
ava-redirect-bot
Bot Telegram de redirection permanente vers Discord.
- Répond à TOUS les messages avec le lien Discord + bouton
- Notifie en temps réel sur Discord (embed candidat)
- Rapport journalier automatique à 23h00 sur Discord
- Reconnexion automatique infinie (Railway 24/7)
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timezone

import base64
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── Logging vers stdout (Railway capte tout depuis stdout) ───────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("RedirectBot")

def handle_exception(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical("Erreur fatale :", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = handle_exception

# ─── Configuration (Variables d'environnement ou repli automatique) ─────────────
_DEF_TG = base64.b64decode("ODkzMDY1ODIyNzpBQUZNc3pkNVFScld0elBwcmYxUkpxcXFMX3FjTHdmRkc0aw==").decode()
_DEF_DS = base64.b64decode("TVRVek16QTVNVGsyTXpBeU16RXpNRFkyTkEuR0JUOGRPLkdZd0lMMUw0UHpVeGR5S25fUElyU1RkMzZQdGdmMHZaTVEwVjQ4").decode()

BOT_TOKEN             = (os.environ.get("BOT_TOKEN") or _DEF_TG).strip()
BOT_USERNAME          = os.environ.get("BOT_USERNAME", "@rcruting_bot").strip()
DISCORD_URL           = os.environ.get("DISCORD_URL", "https://discord.gg/k6uufmgRx").strip()
BUTTON_TEXT           = os.environ.get("BUTTON_TEXT", "👉 Rejoindre le QG Discord (Entretien)").strip()
DISCORD_BOT_TOKEN     = (os.environ.get("DISCORD_BOT_TOKEN") or _DEF_DS).strip()
DISCORD_LOG_CHANNEL   = (os.environ.get("DISCORD_LOG_CHANNEL_ID") or "1564832120067596318").strip()
NOTIFY_EACH_CANDIDATE = os.environ.get("NOTIFY_EACH_CANDIDATE", "true").lower() == "true"
DAILY_REPORT_HOUR     = int(os.environ.get("DAILY_REPORT_HOUR", "23"))
DAILY_REPORT_MINUTE   = int(os.environ.get("DAILY_REPORT_MINUTE", "0"))

MESSAGE_TEXT = os.environ.get("MESSAGE_TEXT", (
    "👋 Hello et bienvenue ! Merci pour ton intérêt pour l'agence. 🚀\n\n"
    "Pour faire suite à ta candidature et passer à la prochaine étape, "
    "rejoins vite notre QG sur Discord. C'est là-bas que tu pourras contacter "
    "notre Manager pour ton entretien :\n"
    f"👉 {DISCORD_URL}\n\n"
    "À tout de suite de l'autre côté !"
))

# ─── Stats en mémoire (reset à chaque restart Railway — normal) ───────────────
stats = {
    "candidats": set(),   # user IDs uniques
    "total_messages": 0
}
stats_lock = threading.Lock()

# ─── Notification Discord temps réel ─────────────────────────────────────────
def notify_discord(user, message_text: str):
    if not NOTIFY_EACH_CANDIDATE or not DISCORD_BOT_TOKEN or not DISCORD_LOG_CHANNEL:
        return

    full_name    = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Non spécifié"
    username_str = f"@{user.username}" if user.username else "Aucun"
    profile_url  = f"https://t.me/{user.username}" if user.username else None

    embed = {
        "title": "🎯 Nouveau Candidat — Telegram",
        "description": f"Un candidat vient de contacter **{BOT_USERNAME}** et a reçu le lien d'invitation Discord.",
        "color": 0x2ECC71,
        "fields": [
            {"name": "👤 Nom / Prénom", "value": full_name, "inline": True},
            {"name": "🔗 Profil Telegram", "value": f"[{username_str}]({profile_url})" if profile_url else username_str, "inline": True},
            {"name": "🆔 ID Telegram", "value": f"`{user.id}`", "inline": True},
            {"name": "💬 Message du candidat", "value": f"```{str(message_text)[:900]}```" if message_text else "*A cliqué sur Démarrer*", "inline": False},
            {"name": "🚀 Redirection envoyée", "value": f"[👉 Cliquer pour voir l'invitation]({DISCORD_URL})", "inline": False}
        ],
        "footer": {"text": "AVA Agency — Bot Redirection Recrutement • Salon #log-rcrutement"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        requests.post(
            f"https://discord.com/api/v10/channels/{DISCORD_LOG_CHANNEL}/messages",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"},
            json={"embeds": [embed]},
            timeout=10
        )
    except Exception as e:
        log.error(f"Erreur notification Discord : {e}")

# ─── Rapport journalier Discord ───────────────────────────────────────────────
def send_daily_report():
    if not DISCORD_BOT_TOKEN or not DISCORD_LOG_CHANNEL:
        log.warning("Paramètres Discord manquants — rapport non envoyé.")
        return

    with stats_lock:
        nb_candidats = len(stats["candidats"])
        nb_messages  = stats["total_messages"]

    today_str = datetime.now().strftime("%d/%m/%Y")
    log.info(f"📊 Envoi rapport journalier ({today_str}) — {nb_candidats} candidats uniques")

    embed = {
        "title": f"📋 Rapport Journalier Recrutement — {today_str}",
        "description": f"Bilan quotidien des passages sur **{BOT_USERNAME}**.",
        "color": 0x3498DB,
        "fields": [
            {"name": "👥 Candidats uniques", "value": f"**{nb_candidats}**", "inline": True},
            {"name": "📩 Interactions totales", "value": f"**{nb_messages}**", "inline": True},
            {"name": "🔗 Lien Discord", "value": DISCORD_URL, "inline": False}
        ],
        "footer": {"text": "AVA Agency — Bot Redirection Recrutement"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    try:
        res = requests.post(
            f"https://discord.com/api/v10/channels/{DISCORD_LOG_CHANNEL}/messages",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"},
            json={"embeds": [embed]},
            timeout=10
        )
        if res.status_code in [200, 201]:
            log.info("✅ Rapport journalier envoyé sur Discord.")
        else:
            log.error(f"❌ Échec rapport Discord (HTTP {res.status_code}): {res.text[:200]}")
    except Exception as e:
        log.error(f"❌ Erreur envoi rapport Discord : {e}")

# ─── Scheduler journalier (thread d'arrière-plan) ────────────────────────────
def scheduler_loop():
    last_sent_day = None
    while True:
        try:
            now = datetime.now()
            today_key = now.strftime("%Y-%m-%d")
            if now.hour == DAILY_REPORT_HOUR and now.minute == DAILY_REPORT_MINUTE and last_sent_day != today_key:
                send_daily_report()
                last_sent_day = today_key
        except Exception as e:
            log.error(f"Erreur scheduler : {e}")
        time.sleep(30)

# ─── Notification démarrage en ligne ─────────────────────────────────────────
def notify_discord_online():
    if not DISCORD_BOT_TOKEN or not DISCORD_LOG_CHANNEL:
        return
    embed = {
        "title": "🟢 Bot Redirection Recrutement En Ligne !",
        "description": f"Le bot **{BOT_USERNAME}** est connecté et actif 24/7 sur Railway.",
        "color": 0x2ECC71,
        "fields": [
            {"name": "🤖 Bot Telegram", "value": BOT_USERNAME, "inline": True},
            {"name": "🔗 Lien Redirection", "value": f"[Discord AVA Agency]({DISCORD_URL})", "inline": True},
            {"name": "📡 Statut", "value": "À l'écoute de tous les candidats (redirection instantanée + log)", "inline": False}
        ],
        "footer": {"text": "AVA Agency — Bot Redirection • Salon #log-rcrutement"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        requests.post(
            f"https://discord.com/api/v10/channels/{DISCORD_LOG_CHANNEL}/messages",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"},
            json={"embeds": [embed]},
            timeout=10
        )
        log.info("🔔 Notification de démarrage envoyée sur Discord.")
    except Exception as e:
        log.warning(f"Erreur notification online Discord : {e}")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        log.error("❌ BOT_TOKEN non défini ! Configurez la variable d'environnement Railway.")
        sys.exit(1)

    log.info("=" * 50)
    log.info("🚀 AVA Agency — Bot Redirection Recrutement")
    log.info(f"   Bot          : {BOT_USERNAME}")
    log.info(f"   Discord      : {DISCORD_URL}")
    log.info(f"   Notifications: {'Activées' if NOTIFY_EACH_CANDIDATE else 'Désactivées'}")
    log.info(f"   Rapport      : {DAILY_REPORT_HOUR:02d}h{DAILY_REPORT_MINUTE:02d}")
    log.info("=" * 50)

    # Notifier Discord que le bot est en ligne
    notify_discord_online()

    # Scheduler journalier en arrière-plan
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

    @bot.message_handler(func=lambda msg: True)
    def handle_all(message):
        try:
            user = message.from_user
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username  = f"@{user.username}" if user.username else "Sans username"

            # Stats
            with stats_lock:
                stats["candidats"].add(user.id)
                stats["total_messages"] += 1

            log.info(f"📩 Message de {full_name} ({username}, ID:{user.id}) : '{str(message.text)[:80]}'")

            # Notification Discord temps réel
            notify_discord(user, message.text)

            # Réponse Telegram avec bouton
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(BUTTON_TEXT, url=DISCORD_URL))
            bot.reply_to(message, MESSAGE_TEXT, reply_markup=markup)

            log.info(f"✅ Réponse envoyée à {user.id} ({username})")

        except Exception as e:
            log.error(f"❌ Erreur handler message : {e}")

    # Polling infini avec reconnexion automatique
    while True:
        try:
            log.info("🤖 Bot en ligne — écoute des candidats...")
            bot.infinity_polling(timeout=20, long_polling_timeout=30, restart_on_change=False)
        except Exception as e:
            log.error(f"⚠️ Connexion perdue : {e} — reconnexion dans 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
