import os
import difflib
import discord
from discord import app_commands
from discord.ext import commands

from common import handleCommandAccess, config

FILES_ROOT = os.path.join(os.curdir, "files")

def resolvePath(relpath: str):
    relpath = (relpath or "").replace("\\", "/").strip().strip("/")
    fullpath = os.path.normpath(os.path.join(FILES_ROOT, relpath))
    root = os.path.normpath(FILES_ROOT)
    if fullpath != root and not fullpath.startswith(root + os.sep):
        return None  # path escapes files/
    return fullpath

def isPoweruser(userid: int):
    return config.get("poweruserid") is not None and userid == int(config["poweruserid"])

def collectPaths(onlyfiles: bool = False, onlydirs: bool = False):
    paths = [""] if onlydirs else []
    for root, dirs, files in os.walk(FILES_ROOT):
        relroot = os.path.relpath(root, FILES_ROOT)
        relroot = "" if relroot == "." else relroot.replace(os.sep, "/")
        if not onlyfiles:
            for d in dirs:
                paths.append(f"{relroot}/{d}" if relroot else d)
        if not onlydirs:
            for f in files:
                paths.append(f"{relroot}/{f}" if relroot else f)
    return paths

def matchPaths(current: str, paths):
    if not current:
        return sorted(paths)[:25]
    lower_current = current.lower()
    substring_matches = sorted(p for p in paths if lower_current in p.lower())
    close_matches = difflib.get_close_matches(lower_current, [p.lower() for p in paths], n=25, cutoff=0.6)
    lower_to_path = {p.lower(): p for p in paths}
    seen = set(substring_matches)
    for lower_path in close_matches:
        p = lower_to_path[lower_path]
        if p not in seen:
            seen.add(p)
            substring_matches.append(p)
    return substring_matches[:25]

class Filesystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(FILES_ROOT, exist_ok=True)

    @app_commands.command(name="fs-mkdir", description="Create a directory.")
    @app_commands.describe(path="Directory path to create, e.g. notes/2026")
    async def mkdir(self, interaction: discord.Interaction, path: str):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        fullpath = resolvePath(path)
        if fullpath is None:
            await interaction.response.send_message(content="Invalid path.", ephemeral=True)
            return
        if os.path.exists(fullpath) and not os.path.isdir(fullpath):
            await interaction.response.send_message(content="A file already exists at that path.", ephemeral=True)
            return

        os.makedirs(fullpath, exist_ok=True)
        await interaction.response.send_message(content=f"Created directory `files/{os.path.relpath(fullpath, FILES_ROOT)}`.", ephemeral=True)

    @app_commands.command(name="fs-newfile", description="Create a text file via a form.")
    @app_commands.describe(path="File path to create, e.g. notes/2026/todo.txt")
    async def newfile(self, interaction: discord.Interaction, path: str):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        fullpath = resolvePath(path)
        if fullpath is None:
            await interaction.response.send_message(content="Invalid path.", ephemeral=True)
            return
        if os.path.isdir(fullpath):
            await interaction.response.send_message(content="That path is a directory.", ephemeral=True)
            return
        if not os.path.isdir(os.path.dirname(fullpath)):
            await interaction.response.send_message(content="Parent directory doesn't exist. Use /fs-mkdir first.", ephemeral=True)
            return

        class newFileForm(discord.ui.Modal, title="Create text file"):
            content = discord.ui.TextInput(label="File content", style=discord.TextStyle.paragraph, placeholder="Enter file content here.", required=True, max_length=4000)

            async def on_submit(self, modalinteraction: discord.Interaction):
                with open(fullpath, "w", encoding="utf-8") as f:
                    f.write(self.content.value)
                await modalinteraction.response.send_message(content=f"Created file `files/{os.path.relpath(fullpath, FILES_ROOT)}`.", ephemeral=True)

        await interaction.response.send_modal(newFileForm())

    @app_commands.command(name="fs-upload", description="Upload a file into a directory.")
    @app_commands.describe(path="Directory to upload into, e.g. notes/2026", file="The file to upload", overwrite="Overwrite if a file with the same name exists (defaults to false)")
    async def upload(self, interaction: discord.Interaction, path: str, file: discord.Attachment, overwrite: bool = False):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        directory = resolvePath(path)
        if directory is None:
            await interaction.response.send_message(content="Invalid path.", ephemeral=True)
            return
        if not os.path.isdir(directory):
            await interaction.response.send_message(content="That directory doesn't exist. Use /fs-mkdir first.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        destination = os.path.join(directory, file.filename)
        if os.path.exists(destination) and not overwrite:
            await interaction.edit_original_response(content="A file with that name already exists. Set overwrite to true to replace it.")
            return

        await file.save(destination)
        await interaction.edit_original_response(content=f"Saved `files/{os.path.relpath(destination, FILES_ROOT)}`.")

    @app_commands.command(name="fs-list", description="List contents of a directory.")
    @app_commands.describe(path="Directory to list, defaults to the root.")
    async def list_(self, interaction: discord.Interaction, path: str = ""):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        directory = resolvePath(path)
        if directory is None or not os.path.isdir(directory):
            await interaction.response.send_message(content="That directory doesn't exist.", ephemeral=True)
            return

        entries = sorted(os.listdir(directory))
        if not entries:
            await interaction.response.send_message(content="Empty directory.", ephemeral=True)
            return

        lines = []
        for entry in entries:
            entrypath = os.path.join(directory, entry)
            lines.append(f"[dir]  {entry}/" if os.path.isdir(entrypath) else f"[file] {entry}")

        relpath = os.path.relpath(directory, FILES_ROOT)
        header = "files/" if relpath == "." else f"files/{relpath}/"
        await interaction.response.send_message(content=f"**{header}**\n```\n" + "\n".join(lines) + "\n```", ephemeral=True)

    @list_.autocomplete("path")
    async def list_autocomplete(self, interaction: discord.Interaction, current: str):
        paths = matchPaths(current, collectPaths(onlydirs=True))
        return [app_commands.Choice(name=("files/ (root)" if p == "" else f"files/{p}/")[:100], value=p) for p in paths]

    @app_commands.command(name="fs-read", description="Read a file's contents.")
    @app_commands.describe(path="File path to read, e.g. notes/2026/todo.txt", public="Whether to send the file publicly or privately (defaults to false)")
    async def read(self, interaction: discord.Interaction, path: str, public: bool = False):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        fullpath = resolvePath(path)
        if fullpath is None or not os.path.isfile(fullpath):
            await interaction.response.send_message(content="That file doesn't exist.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=not public)
        relpath = os.path.relpath(fullpath, FILES_ROOT)

        try:
            with open(fullpath, "r", encoding="utf-8") as f:
                text = f.read()
            if len(text) <= 1900:
                await interaction.edit_original_response(content=f"**files/{relpath}**\n```\n{text}\n```")
                return
        except (UnicodeDecodeError, ValueError):
            pass

        await interaction.edit_original_response(content=f"`files/{relpath}`", attachments=[discord.File(fullpath)])

    @read.autocomplete("path")
    async def read_autocomplete(self, interaction: discord.Interaction, current: str):
        paths = matchPaths(current, collectPaths(onlyfiles=True))
        return [app_commands.Choice(name=f"files/{p}"[:100], value=p) for p in paths]

async def setup(bot: commands.Bot):
    await bot.add_cog(Filesystem(bot))
