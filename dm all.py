
import discord
from discord.ext import commands, tasks
from discord import app_commands # Pour les commandes slash
import asyncio
import time
import os
from dotenv import load_dotenv

# Charger les variables d'environnement du fichier .env
load_dotenv()

# --- CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT ---
# Récupérer le token du bot
TOKEN = os.getenv("TMyMjYxNTgxMDM1MDM4MzIzNw.GSt6Qq.af3EHilA4GtoSodgGG5bB8FSrFwoEdbwDD6Yzo")
if not TOKEN:
    raise ValueError("Le token Discord n'est pas défini dans le fichier .env (DISCORD_TOKEN).")

# Récupérer l'index du bot (pour la répartition des membres)
try:
    BOT_INDEX = int(os.getenv("BOT_INDEX", "1")) # Valeur par défaut 1 si non défini
except ValueError:
    raise ValueError("BOT_INDEX dans le .env doit être un nombre entier.")

# Récupérer le nombre de membres gérés par chaque bot
try:
    MEMBERS_PER_BOT = int(os.getenv("MEMBERS_PER_BOT", "500")) # Valeur par défaut 500
except ValueError:
    raise ValueError("MEMBERS_PER_BOT dans le .env doit être un nombre entier.")

# Récupérer l'ID du salon de logs
try:
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
except (TypeError, ValueError):
    LOG_CHANNEL_ID = None # Le salon de logs est optionnel, mais fortement recommandé

# --- CONFIGURATION DES INTENTS ---
# Les intents sont cruciaux pour que le bot reçoive les événements nécessaires
intents = discord.Intents.default()
intents.members = True          # Nécessaire pour accéder à la liste des membres du serveur
intents.message_content = True  # Nécessaire pour lire le contenu des messages (commandes préfixées)
intents.guilds = True           # Nécessaire pour accéder aux informations des serveurs

# Initialisation du bot
bot = commands.Bot(command_prefix="!", intents=intents) # Préfixe changé à "!" pour être plus commun

# Variable pour suivre l'état de l'envoi de DMs
dm_in_progress = False

# --- ÉVÉNEMENTS DU BOT ---
@bot.event
async def on_ready():
    """Appelé lorsque le bot est connecté et prêt."""
    activity = discord.Game(f"DM en masse | ZPCK.1 Bot {BOT_INDEX}")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ Bot prêt ! Connecté en tant que {bot.user} (BOT {BOT_INDEX} de ZPCK.1)")

    # Synchronisation des commandes slash
    try:
        synced = await bot.tree.sync()
        print(f"✨ Commandes slash synchronisées : {len(synced)} commande(s).")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes slash : {e}")

    # Envoi d'un message de démarrage dans le salon de logs (si configuré)
    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🚀 Bot **{bot.user.name}** (BOT {BOT_INDEX}) a démarré avec succès ! Prêt à envoyer des DMs.")
        else:
            print(f"⚠️ Le salon de logs (ID: {LOG_CHANNEL_ID}) n'a pas pu être trouvé.")

@bot.event
async def on_command_error(ctx, error):
    """Gère les erreurs des commandes."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"🚫 **ZPCK.1 dit :** Tu n'as pas la permission de faire ça, mon ami. Il te faut la permission Administrateur !")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **ZPCK.1 dit :** Doucement, l'envoi est en période de rechargement. Réessaye dans {error.retry_after:.2f} secondes.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"🤔 **ZPCK.1 dit :** Il manque quelque chose ! Utilise la commande correctement, par exemple : `/dm_all <ton message>` ou `!dm_all <ton message>`.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ **ZPCK.1 dit :** Je n'ai pas les permissions nécessaires pour exécuter cette commande. Assure-toi que j'ai bien la permission d'**envoyer des messages privés** et de **voir les membres**.")
    else:
        await ctx.send(f"🚫 **ZPCK.1 dit :** Une erreur imprévue est survenue : `{error}`. Contacte mon développeur !")
        print(f"❌ Erreur non gérée pour la commande {ctx.command.name}: {error}")
        if LOG_CHANNEL_ID:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"❌ Erreur dans la commande `{ctx.command.name}` : `{error}` (par {ctx.author.mention})")

# --- COMMANDES DU BOT ---

@bot.command(name="dm_all", description="Envoie un message privé à tous les membres du serveur (partie allouée au bot).")
@commands.has_permissions(administrator=True)
@commands.cooldown(1, 300, commands.BucketType.guild) # 1 utilisation toutes les 5 minutes par serveur
async def dm_all_command(ctx, *, message: str):
    """Commande préfixée pour envoyer un DM à tous les membres alloués au bot."""
    global dm_in_progress
    await handle_dm_all(ctx, message)

@app_commands.command(name="dm_all", description="[ADMIN] Envoie un message privé à tous les membres du serveur (partie allouée au bot).")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(message="Le message à envoyer à tous les membres.")
async def dm_all_slash(interaction: discord.Interaction, message: str):
    """Commande slash pour envoyer un DM à tous les membres alloués au bot."""
    global dm_in_progress
    # Utilisation d'un contexte de type Command pour le passage à handle_dm_all
    # Cela permet de réutiliser la même logique pour les deux types de commandes
    ctx = await bot.get_context(interaction.message) # Ceci peut être None si l'interaction n'est pas un message
    # Alternative plus simple pour les slash commands :
    # Si le message vient d'un slash command, on peut créer un objet "context-like"
    class SlashContext:
        def __init__(self, interaction_obj, bot_obj):
            self.interaction = interaction_obj
            self.bot = bot_obj
            self.guild = interaction_obj.guild
            self.author = interaction_obj.user
            self.channel = interaction_obj.channel
            self.me = interaction_obj.guild.me if interaction_obj.guild else bot_obj.user

        async def send(self, *args, **kwargs):
            # Pour les slash commands, la première réponse doit être via interaction.response.send_message
            if not self.interaction.response.is_done():
                await self.interaction.response.send_message(*args, **kwargs)
            else:
                await self.channel.send(*args, **kwargs)

        async def defer(self, ephemeral=False):
            if not self.interaction.response.is_done():
                await self.interaction.response.defer(ephemeral=ephemeral)

    ctx = SlashContext(interaction, bot)
    await handle_dm_all(ctx, message, is_slash=True)


async def handle_dm_all(ctx, message: str, is_slash=False):
    """Logique principale pour l'envoi de DMs, partagée entre les commandes préfixées et slash."""
    global dm_in_progress

    if dm_in_progress:
        response_msg = "⏳ **ZPCK.1 dit :** Un envoi est déjà en cours. Patientez s'il vous plaît."
        if is_slash:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(response_msg, ephemeral=True)
            else:
                await ctx.channel.send(response_msg)
        else:
            await ctx.send(response_msg)
        return

    # Vérification des permissions si ce n'est pas déjà fait par les décorateurs
    if not isinstance(ctx, discord.Interaction): # Si c'est un Command context (préfixé)
        if not ctx.author.guild_permissions.administrator:
            response_msg = "🚫 **ZPCK.1 dit :** Tu n’as pas la permission d'utiliser cette commande. (Administrateur requis)"
            if is_slash:
                if not ctx.interaction.response.is_done():
                    await ctx.interaction.response.send_message(response_msg, ephemeral=True)
                else:
                    await ctx.channel.send(response_msg)
            else:
                await ctx.send(response_msg)
            return

    guild = ctx.guild
    if not guild:
        response_msg = "❌ **ZPCK.1 dit :** Cette commande ne peut être utilisée que sur un serveur Discord."
        if is_slash:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(response_msg, ephemeral=True)
            else:
                await ctx.channel.send(response_msg)
        else:
            await ctx.send(response_msg)
        return

    # S'assurer que tous les membres sont chargés
    await guild.chunk()

    members = [m for m in guild.members if not m.bot]
    total_guild_members = len(members)

    # Calcul des membres ciblés par ce bot
    start_index = (BOT_INDEX - 1) * MEMBERS_PER_BOT
    end_index = start_index + MEMBERS_PER_BOT
    target_members = members[start_index:end_index]

    if not target_members:
        response_msg = f"ℹ️ **ZPCK.1 dit :** BOT {BOT_INDEX} n'a aucun membre à envoyer dans cette tranche ({start_index}-{end_index})."
        if is_slash:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(response_msg, ephemeral=True)
            else:
                await ctx.channel.send(response_msg)
        else:
            await ctx.send(response_msg)
        return

    initial_response_msg = f"📤 **ZPCK.1 dit :** BOT {BOT_INDEX} commence l'envoi de DMs à {len(target_members)} membres ({start_index}-{end_index} sur {total_guild_members} membres du serveur). Soyez patient !"
    if is_slash:
        if not ctx.interaction.response.is_done():
            await ctx.interaction.response.send_message(initial_response_msg, ephemeral=False)
        else:
            await ctx.channel.send(initial_response_msg)
    else:
        await ctx.send(initial_response_msg)

    # Envoi au salon de logs
    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🟢 **ZPCK.1** (BOT {BOT_INDEX}) a démarré un envoi de DMs.\n"
                                   f"Cible : {len(target_members)} membres ({start_index}-{end_index}).\n"
                                   f"Message : ```{message[:100]}...```" if len(message) > 100 else f"Message : ```{message}```")


    count = 0
    failed_count = 0
    start_time = time.time()
    dm_in_progress = True

    for i, member in enumerate(target_members):
        try:
            await member.send(message)
            count += 1
            print(f"✅ DM envoyé ({count}/{len(target_members)}) à : {member} (ID: {member.id})")
            # Petite pause pour éviter les limitations de l'API Discord
            await asyncio.sleep(0.5)
            if count % 100 == 0: # Pause plus longue toutes les 100 DMs
                print(f"⏸️ Pause stratégique de 10 secondes après {count} DMs. ZPCK.1 pense à tout !")
                await asyncio.sleep(10)
        except discord.Forbidden:
            failed_count += 1
            print(f"⛔ DM refusé par {member} (ID: {member.id}) - messages privés fermés.")
        except discord.HTTPException as e:
            failed_count += 1
            print(f"❌ Erreur HTTP ({e.status}) avec {member} (ID: {member.id}) : {e}")
            await asyncio.sleep(15) # Pause plus longue en cas d'erreur HTTP
        except Exception as e:
            failed_count += 1
            print(f"⚠️ Autre erreur avec {member} (ID: {member.id}) : {e}")
            await asyncio.sleep(5) # Pause plus courte pour d'autres erreurs

    elapsed = time.time() - start_time
    dm_in_progress = False

    final_msg = (
        f"✅ **ZPCK.1 dit :** Envoi terminé pour BOT {BOT_INDEX} !\n"
        f"Statistiques : {count} DMs envoyés, {failed_count} échecs (MPs fermés/erreurs).\n"
        f"Temps total : {int(elapsed // 60)} minutes et {int(elapsed % 60)} secondes.\n"
        f"Prochaine utilisation possible dans 5 minutes (cooldown)."
    )

    if is_slash:
        # Si la réponse initiale était deferred, on utilise follow_up
        if ctx.interaction.response.is_done():
            await ctx.interaction.followup.send(final_msg)
        else: # Sinon, c'est la première réponse
            await ctx.interaction.response.send_message(final_msg)
    else:
        await ctx.send(final_msg)

    # Envoi au salon de logs
    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"✅ **ZPCK.1** (BOT {BOT_INDEX}) a terminé l'envoi de DMs.\n"
                                   f"**Résumé :** {count} envoyés, {failed_count} échecs en {int(elapsed // 60)}m {int(elapsed % 60)}s.")


# --- EXÉCUTION DU BOT ---
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    