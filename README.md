# Discord Filesystem

A simple Discord bot that lets you upload and download files, I guess.

Best used on a continuously running computer/laptop at home.

> [!NOTE]
> This bot was designed to be installed for one user only.

## Setup

You will need:

* A Discord bot
* Python (3.0 or above)
* The required Python libraries in `requirements.txt`

The following are optional, but recommended:

* A device capable of running the Python program for a while (if you plan on leaving the bot online most of the time)

### Discord Bot

1. Log on to the [Discord Developer Portal](https://discord.com/developers/applications "Leads you to the Discord Developer Portal").
2. Create a new application using the button on the top right.
3. Add a new app icon. This will be the bot's profile picture.
4. Under the Overview tab, click on "Bot", and reset the bot's token. Copy the new token and keep it somewhere, you'll need it later.
5. Go to the Installation tab, and make sure the installation context is set to "User Install". Select "Discord Provided Link" for the Install link, then copy the generated URL.
6. Paste the url into your favourite browser, and add the bot to your account.

> [!TIP]
> It's best if your Discord bot is set to private.
> You can do this by setting the "Install Link" (under the Installation tab) to None, then toggling off "Public Bot" under the Bot tab.

### Python Code

Ensure you have everything with:
`git clone https://github.com/etangaming123/discord-filesystem`

Get all the required modules with:
`pip install -r requirements.txt`

Then, create a `config.json` file in the same directory as `main.py` with the following content:

```json
{
	"token": "Your Discord Bot Token here",
	"poweruserid": "Your Discord User ID here (optional, for owner-only commands)"
}
```

Finally, run the bot with:
`python main.py`

Refresh your Discord client, and press `/` on your keyboard. You should see the bot's commands in the list, and you can start using it!

Do note that the program has to be continuously running for the bot to work. If you close the terminal or stop the program, the bot will go offline and become unusable until you run it again. (Closing the program will keep your files, though!)

## Encryption keys

Your bot token is encrypted at rest in `config.json`, not stored as plain text.

Out of the box, this needs no setup: the first time the bot runs, it generates a `bot_token.key` file next to `main.py` and uses it to encrypt the token in place. As long as that file stays put, the bot keeps working with no further action from you.

If you'd rather keep the key out of a file on disk (e.g. so it's not sitting next to the repo), you can opt into an environment variable instead:

* **Windows:** double-click `setup_encryption_keys.bat`. It generates a key and sets it as a permanent environment variable (`BOT_TOKEN_ENCRYPTION_KEY`) for your user account. Close and reopen your terminal (or just restart the bot) afterwards.
* **macOS/Linux:** run `python generate_env_keys.py`, then paste the printed `export BOT_TOKEN_ENCRYPTION_KEY="..."` line into your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) and restart your shell.

If a token was already encrypted under the file key before you set the environment variable, it's automatically re-encrypted under the new key the next time the bot starts — no manual migration needed.

> [!WARNING]
> If you lose the encryption key (the `bot_token.key` file, or the environment variable's value), the stored token can't be recovered. You'll need to reset your bot's token in the Discord Developer Portal and reconfigure `config.json`.