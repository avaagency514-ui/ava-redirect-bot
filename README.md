# ava-redirect-bot

Bot Telegram de redirection permanente vers Discord.

## Fonctionnalités
- Répond à **TOUS les messages** reçus sur le bot avec un lien Discord + bouton
- **Notifie en temps réel** sur Discord (embed avec nom, username, ID du candidat)
- **Rapport journalier** automatique à 23h00 sur Discord
- Reconnexion automatique infinie sur Railway 24/7

## Variables d'environnement Railway
| Variable | Description | Exemple |
|----------|-------------|---------|
| `BOT_TOKEN` | Token du bot Telegram | `123456:ABC...` |
| `BOT_USERNAME` | Username du bot | `@rcruting_bot` |
| `DISCORD_URL` | Lien d'invitation Discord | `https://discord.gg/xxx` |
| `BUTTON_TEXT` | Texte du bouton Telegram | `👉 Rejoindre Discord` |
| `DISCORD_BOT_TOKEN` | Token bot Discord (logs) | `MTUz...` |
| `DISCORD_LOG_CHANNEL_ID` | ID salon Discord logs | `1564832120067596318` |
| `NOTIFY_EACH_CANDIDATE` | Notif par candidat | `true` |
| `DAILY_REPORT_HOUR` | Heure rapport (24h) | `23` |
| `DAILY_REPORT_MINUTE` | Minute rapport | `0` |

## Déploiement Railway
1. Créer un nouveau projet Railway
2. Connecter ce repo GitHub
3. Configurer les variables d'env ci-dessus
4. Railway détecte automatiquement le `Procfile` et démarre
