import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from flask import Flask

import os
import threading

# ---------- FLASK ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot en ligne !"

# Thread Flask pour Render
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

# ---------- DISCORD ----------
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} est en ligne!")

# ---------- COMMANDE DM ----------
@bot.tree.command(name="dm", description="Envoyer un DM à un utilisateur")
@app_commands.describe(utilisateur="Utilisateur à qui envoyer le DM", message="Message à envoyer")
async def dm(interaction: discord.Interaction, utilisateur: discord.Member, message: str):
    try:
        await utilisateur.send(message)
        await interaction.response.send_message(f"✅ Message envoyé à {utilisateur.mention}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {type(e).__name__} → {e}", ephemeral=True)

# ---------- COMMANDE CANDIDATURE ----------
@bot.tree.command(name="candidature", description="Envoyer votre candidature")
@app_commands.describe(message="Votre candidature")
async def candidature(interaction: discord.Interaction, message: str):
    try:
        channel = get(interaction.guild.text_channels, name="candidatures")
        if channel:
            await channel.send(f"{interaction.user.mention} a posté sa candidature : {message}")
        await interaction.response.send_message("✅ Candidature envoyée !", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {type(e).__name__} → {e}", ephemeral=True)

# ---------- COMMANDE VK ----------
@bot.tree.command(name="vk", description="Commande VK")
async def vk(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("🌐 Commande VK exécutée!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {type(e).__name__} → {e}", ephemeral=True)

# ---------- LANCEMENT DU BOT ----------
TOKEN = os.environ.get("DISCORD_TOKEN")  # Ton token stocké dans Render comme variable d'environnement
bot.run(TOKEN)
