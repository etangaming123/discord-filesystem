import os
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

def splitPathInput(current: str):
    current = (current or "").replace("\\", "/")
    if "/" in current:
        prefix, partial = current.rsplit("/", 1)
    else:
        prefix, partial = "", current
    return prefix.strip("/"), partial

def listChildren(prefix: str, includefiles: bool = True, includedirs: bool = True):
    directory = resolvePath(prefix)
    if directory is None or not os.path.isdir(directory):
        return []
    children = []
    for entry in sorted(os.listdir(directory)):
        isdir = os.path.isdir(os.path.join(directory, entry))
        if isdir and not includedirs:
            continue
        if not isdir and not includefiles:
            continue
        value = f"{prefix}/{entry}" if prefix else entry
        if isdir:
            value += "/"
        children.append((entry, value, isdir))
    return children

def matchChildren(current: str, includefiles: bool = True, includedirs: bool = True, allowroot: bool = False):
    prefix, partial = splitPathInput(current)
    lower_partial = partial.lower()
    choices = []

    if allowroot and prefix == "" and lower_partial in "root":
        choices.append(("files/ (root)", ""))

    for name, value, isdir in listChildren(prefix, includefiles, includedirs):
        if lower_partial in name.lower():
            label = f"files/{value}"
            choices.append((label, value))

    return choices[:25]

class Filesystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(FILES_ROOT, exist_ok=True)

    @app_commands.command(name="fs-create-directory", description="Create a directory.")
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

    @app_commands.command(name="fs-create-file", description="Create a text file via a form.")
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
            await interaction.response.send_message(content="That directory doesn't exist. Use /fs-create-directory first.", ephemeral=True)
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
        choices = matchChildren(current, includefiles=False, includedirs=True, allowroot=True)
        return [app_commands.Choice(name=label[:100], value=value) for label, value in choices]

    @app_commands.command(name="fs-open", description="Open a file's contents.")
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
        choices = matchChildren(current, includefiles=True, includedirs=True, allowroot=False)
        return [app_commands.Choice(name=label[:100], value=value) for label, value in choices]

    @app_commands.command(name="fs-delete", description="Delete a file or directory.")
    @app_commands.describe(path="File or directory path to delete, e.g. notes/2026/todo.txt")
    async def delete(self, interaction: discord.Interaction, path: str):
        if not await handleCommandAccess(interaction, interaction.user.id):
            return
        if not isPoweruser(interaction.user.id):
            await interaction.response.send_message(content="You don't have permission to use this command.", ephemeral=True)
            return

        fullpath = resolvePath(path)
        if fullpath is None or not os.path.exists(fullpath):
            await interaction.response.send_message(content="That file or directory doesn't exist.", ephemeral=True)
            return

        if os.path.isdir(fullpath):
            try:
                os.rmdir(fullpath)
                await interaction.response.send_message(content=f"Deleted directory `files/{os.path.relpath(fullpath, FILES_ROOT)}`.", ephemeral=True)
            except OSError:
                await interaction.response.send_message(content="Directory is not empty. Cannot delete.", ephemeral=True)
        else:
            os.remove(fullpath)
            await interaction.response.send_message(content=f"Deleted file `files/{os.path.relpath(fullpath, FILES_ROOT)}`.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Filesystem(bot))
