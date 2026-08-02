print("Loading modules...")
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os 
import json
from git import Repo
repo = Repo(os.curdir)

if not os.path.isdir("files"):
    os.mkdir("files")

if not os.path.exists("config.json"):
    with open("config.json", "w") as f:
        json.dump({"token": "your token here", "poweruserid": "your user id here (for certain commands)"}, f, indent=4)
    input("Created config.json with default values. Please edit the file with your bot token and user id, then press enter to continue...")

from common import ensure_datastores, config, handleCommandAccess, setCooldown, getLatestCommitHash, currentcommithash

intents = discord.Intents.default()
ensure_datastores()

with open('config.json') as f:
    config = json.load(f)

cogs = ["listing"]

print("Loading additional commands...")
class etanBot(commands.Bot):
    async def setup_hook(self):
        for item in cogs:
            try:
                await self.load_extension(f"cogs.{item}")
                print(f"Loaded cog {item}")
            except Exception as e:
                print(f"Failed to load cog {item}: {e}")

bot = etanBot(command_prefix='!', intents=intents)
bot.tree.allowed_installs = app_commands.AppInstallationType(guild=True, user=True)
bot.tree.allowed_contexts = app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)

async def updateStatus(newstatus):
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=newstatus))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        print("Syncing commands...")
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')
    await updateStatus("mfw")
    print("Bot is up and running!")

# general
@bot.tree.command(name="ping", description="Ping the bot")
async def ping(interaction: discord.Interaction):
    if not await handleCommandAccess(interaction, interaction.user.id):
        return
    await interaction.response.defer()
    await interaction.edit_original_response(content=f"Pong! [{round(bot.latency * 1000)}ms]")

@bot.tree.command(name="status", description="Are we running the latest commit?")
async def status(interaction: discord.Interaction):
    if not await handleCommandAccess(interaction, interaction.user.id, "status"):
        return
    await interaction.response.defer()
    setCooldown(interaction.user.id, "status", 10)
    if repo.is_dirty():
        await interaction.edit_original_response(content="filesystem is running on a modified commit!")
        return
    latesthash = getLatestCommitHash()
    if latesthash == currentcommithash:
        await interaction.edit_original_response(content=f"filesystem is up to date! Running commit: {currentcommithash}")
    elif latesthash == "unknown":
        await interaction.edit_original_response(content=f"filesystem is running commit: {currentcommithash}, we couldn't get the latest commit")
    else:
        await interaction.edit_original_response(content=f"filesystem is not up to date. Running commit: {currentcommithash}, latest commit: {latesthash}. Please contact the developer to update the bot!")

bot.run(config['token'])