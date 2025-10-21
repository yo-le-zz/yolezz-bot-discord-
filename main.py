import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from flask import Flask
import threading

app = Flask("")

@app.route("/")
def home():
    return "Bot actif ✅"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Token Discord introuvable !")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=intents)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("✅ Commandes slash synchronisées.")
        except Exception as e:
            print(f"❌ Erreur de synchronisation : {str(e)}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et prêt à recevoir des commandes slash !")

@bot.tree.command(name="dm", description="Envoie un message privé à un utilisateur")
@app_commands.describe(utilisateur="L'utilisateur à qui envoyer le message", message="Le contenu du message")
async def dm(interaction: discord.Interaction, utilisateur: discord.User, message: str):
    try:
        await utilisateur.send(message)
        await interaction.response.send_message(f"✅ Message envoyé à {utilisateur.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Impossible d'envoyer le message à {utilisateur.mention} (DM désactivés ou rôle supérieur).", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Erreur : {type(e).__name__} → {e}", ephemeral=True)

@bot.tree.command(name="purge", description="Supprime tous les messages d'un salon")
@app_commands.describe(salon="Le salon à purger")
async def purge(interaction: discord.Interaction, salon: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Vous n'avez pas la permission de gérer les messages.", ephemeral=True)
        return

    await interaction.response.send_message(f"🧹 Suppression des messages dans {salon.mention}...", ephemeral=True)

    try:
        deleted = 0
        async for msg in salon.history(limit=None):
            await msg.delete()
            deleted += 1

        await interaction.followup.send(f"✅ {deleted} messages supprimés dans {salon.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de supprimer les messages.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur : {type(e).__name__} → {e}", ephemeral=True)

AUTHORIZED_ROLES = ["✨Fondateur✨", "🔨administration🔨", "🔨Juge🔨"]

@bot.tree.command(name="vk", description="Lancer un sondage pour expulser un utilisateur")
@app_commands.describe(utilisateur="Utilisateur à voter pour l'expulsion", reason="Raison du vote")
async def vk(interaction: discord.Interaction, utilisateur: discord.Member, reason: str):
    try:
        # Vérification des permissions
        if not any(role.name in AUTHORIZED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("❌ Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
            return

        # Vérification si l'utilisateur vote contre lui-même
        if utilisateur.id == interaction.user.id:
            await interaction.response.send_message("❌ Vous ne pouvez pas voter contre vous-même.", ephemeral=True)
            return

        # Création de l'embed pour le vote
        vote_embed = discord.Embed(
            title="🗳️ Sondage d'expulsion",
            description=f"Faut-il expulser {utilisateur.mention} ?\n**Raison :** {reason}\n\nRépondez avec ✅ pour OUI ou ❌ pour NON",
            color=discord.Color.red()
        )
        vote_embed.set_footer(text="Le sondage dure 5 minutes.")
        
        # Envoi du message et ajout des réactions
        await interaction.response.send_message(embed=vote_embed)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        # Attente de 5 minutes
        await asyncio.sleep(300)

        # Récupération des votes
        message = await interaction.channel.fetch_message(message.id)
        yes = no = 0
        
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅":
                yes = reaction.count - 1
            elif str(reaction.emoji) == "❌":
                no = reaction.count - 1

        # Traitement du résultat
        if yes > no:
            try:
                await utilisateur.kick(reason=f"Vote d'expulsion : {yes} pour, {no} contre. Raison: {reason}")
                result_text = f"✅ {utilisateur.mention} a été expulsé suite au vote majoritaire !"
            except discord.Forbidden:
                result_text = f"❌ Je n'ai pas pu expulser {utilisateur.mention} (permissions insuffisantes)"
            except Exception as e:
                result_text = f"❌ Erreur lors de l'expulsion : {str(e)}"
        else:
            result_text = f"❌ Le vote pour expulser {utilisateur.mention} n'a pas abouti"

        # Envoi du résultat
        result_embed = discord.Embed(
            title="📊 Résultat du vote d'expulsion",
            description=f"{result_text}\n\n**Votes finaux :**\n✅ Pour : {yes}\n❌ Contre : {no}",
            color=discord.Color.green() if yes > no else discord.Color.red()
        )
        
        await interaction.channel.send(embed=result_embed)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Une erreur est survenue : {str(e)}", ephemeral=True)

# candidature commande
@bot.tree.command(name="candidature", description="Postuler pour un rôle dans le serveur")
@app_commands.describe(
    role_souhaite="Le rôle pour lequel vous postulez (ex: admin, organisateur d'événements, etc.)",
    motivation="Expliquez pourquoi vous devriez être choisi pour ce rôle"
)
async def candidature(interaction: discord.Interaction, role_souhaite: str, motivation: str):
    try:
        # Trouver le salon des candidatures
        candidatures_channel = discord.utils.get(interaction.guild.channels, name="📄-candidatures")
        if not candidatures_channel:
            await interaction.response.send_message("❌ Le salon #📄-candidatures n'existe pas.", ephemeral=True)
            return

        # Créer l'embed de candidature
        candidature_embed = discord.Embed(
            title=f"📝 Nouvelle Candidature - {role_souhaite}",
            color=discord.Color.blue()
        )
        
        candidature_embed.add_field(
            name="📋 Candidat",
            value=f"**Nom:** {interaction.user.mention}\n**ID:** {interaction.user.id}",
            inline=False
        )
        
        candidature_embed.add_field(
            name="🎯 Poste souhaité",
            value=role_souhaite,
            inline=False
        )
        
        candidature_embed.add_field(
            name="💭 Motivation",
            value=motivation,
            inline=False
        )
        
        candidature_embed.set_footer(text=f"Candidature soumise le {interaction.created_at.strftime('%d/%m/%Y à %H:%M')}")
        
        # Ajouter l'avatar du candidat
        candidature_embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Envoyer l'embed dans le salon des candidatures
        await candidatures_channel.send(embed=candidature_embed)
        
        # Confirmer l'envoi au candidat et supprimer le message de commande
        await interaction.response.send_message(
            "✅ Votre candidature a été envoyée avec succès ! L'équipe de modération l'examinera prochainement.",
            ephemeral=True
        )

    except Exception as e:
        await interaction.response.send_message(
            f"⚠️ Une erreur est survenue lors de l'envoi de votre candidature : {str(e)}",
            ephemeral=True
        )

keep_alive()
bot.run(TOKEN)