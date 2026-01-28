![Python-Versions](https://img.shields.io/badge/python-3.7-blue?style=flat-square)
![Discord.py-Version](https://img.shields.io/badge/discord.py-1.3.3-blue?style=flat-square)

# Tortoise-BOT
**Fully functional Bot for Discord coded in Discord.py**

<img alt="Tortoise logo" align="right" src="https://i.imgur.com/bKk1StC.png" width=40%/>

This bot is intended to work only in Tortoise Community guild and it's
mostly tied to one guild. 

Code here serves for education purposes and for
transparency - also to make coding easier as everyone can improve it.

## Features and Commands

There are a lot of features - note that some features are heavily tied to API and are not usable without it.

Backend:

* Custom error handler, custom paginator.

* Security system that block members posting other guild invites & monitors editing/deleting messages and 
has basic support for detecting bad words.

* Custom socket API for website -> bot communication, this way the website can verify members, send custom messages, 
get member data directly from the bot, signal cache updates etc.

* Custom DM commands, message the bot and you will get option (depending if they are enabled, all of them can be disabled 
on need) to make suggestion, event code submission, bug report or initialize  mod-mail.

* Custom API communication for bot -> website API so we can debug verifications/member data or approve/deny/delete 
suggestions, get rules etc.

* Custom self-assignable roles upon reaction on message.

* Custom greetings for new members or members who came back.

* If members leave their non-colored roles are saved and restored if they ever return.

Commands:


> Fun: slap, shoot, throw

> Bot owner commands: load/unload cogs

> Moderation kick, ban, unban, warnings (multiple commands, tied with API), promote, clear, mute, unmute, dm_members, send

> Other: say, members, status, pfp, github, ping, stats, countdown, issues, ask, markdown, paste, zen, antigravity

> Reddit: meme, newpost, hotpost


And more such as music commands, documentation commands for python/dpy docs etc.

## Contributing

All updates welcome but please only push to `dev`.

See section below on Installation Instructions and follow it as developer as that
way the setup of pre-commit hook will be correct. 

## Installation Instructions

Python 3.8 required

```bash

# Your global Python installation needs to have poetry
pip install poetry

# Clone the repo
git clone https://github.com/Tortoise-Community/Tortoise-BOT.git

# Change directories into the project
cd Tortoise-BOT

# Install dependencies (includes dev dependencies)
poetry install

# Activate the Poetry shell (aka tell your terminal/whatever to use dependencies from the env in this project)
poetry shell

# [developer only] Install pre-commit hook
poetry run pre-commit install

# Before we run the bot we need to create .env file where all secret keys will be (tokens etc)

# Create it
touch .env

# Edit it and change the keys to your values (see section below for sample layout)
nano .env
```

#### Sample layout of `.env` file

```bash
PRAW_CLIENT_ID=put_something_here
PRAW_CLIENT_SECRET=put_something_here
BOT_TOKEN=put_something_here
API_ACCESS_TOKEN =put_something_here
SOCKET_AUTH_TOKEN=put_something_here
SOCKET_SERVER_PORT=put_something_here
```

`PRAW_CLIENT_ID` and `PRAW_CLIENT_SECRET`
are for Reddit commands (memes etc), see [Reddit script app OAuth2](https://github.com/reddit-archive/reddit/wiki/OAuth2)
for info how to get them.

`BOT_TOKEN` the most important one. You can get one by [creating a Discord bot](https://discordapp.com/developers/applications)

`API_ACCESS_TOKEN` token to access our API. You don't need this but some features
will be unavailable, we use this for example: checking if user is verified,
verifying new users, putting new users, editing users(infractions, leave date) etc.

`SOCKET_AUTH_TOKEN` token to connect to our bot socket. 
This is so the API can communicate with the bot,
for example when member verifies on website the bot receives this verification trough the socket
and adds roles to members/send him message etc.

`SOCKET_SERVER_PORT` port on which the socket will listen.

#### Additional dependencies

For music cog to work you need ffmpeg (either in the Tortoise-BOT/bot/ directory or in your PATH).

For linux you can install it with `sudo apt install ffmpeg`

### Once everything is ready

Run the bot!

Depending on how you set up `.env` you might get some errors about some cogs not loading 
(for example if you did not set up `PRAW_CLIENT_SECRET` the `cogs/reddit.py` cog will fail to load).
You can safely ignore these errors as they will not stop the bot from functioning and loading other cogs.

```bash
# You need to be in the root of Tortoise-Bot directory
# Once you are in Tortoise-Bot/

# Run the bot
poetry run start
```

# License

MIT - see [LICENSE](https://github.com/Tortoise-Community/Tortoise-BOT/blob/dev/LICENSE) file for details.
