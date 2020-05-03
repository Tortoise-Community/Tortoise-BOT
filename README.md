![Python-Versions](https://img.shields.io/badge/python-3.7-blue?style=flat-square)
![Discord.py-Version](https://img.shields.io/badge/discord.py-1.3.3-blue?style=flat-square)

# Tortoise-BOT
**Fully functional Bot for Discord coded in Discord.py**

<img alt="Tortoise logo" align="right" src="https://i.imgur.com/7LrGjdG.jpg" width=40%>

This bot is intended to work only in Tortoise Community guild and it's
mostly tied to one guild. 

Code here serves for education purposes and for
transparency - also to make coding easier as everyone can improve it.

## Features and Commands

To do, check out cogs source code directory to see for yourself.

## Contributing

All updates welcome but please only push to `dev`.

See section below on Installation Instructions and follow it as developer as that
way the setup of pre-commit hook will be correct. 

## Installation Instructions

Python 3.7 required

```bash

# Your global Python installation needs to have pipenv
pip install pipenv

# Clone the repo
git clone https://github.com/Tortoise-Community/Tortoise-BOT.git

# Change directories into the project
cd Tortoise-BOT

# [developer only] If you are developer you need to install dependencies for dev
pipenv install --dev

# If you're not a developer just install required dependencies like this
pipenv install

# Activate the Pipenv shell (aka tell your terminal/whatever to use dependencies from the env in this project)
pipenv shell

# [developer only] Install pre-commit hook
pipenv run precommit

# Before we run the bot we need to create .env file where all secret keys will be (tokens etc)
# it needs to be in /bot/.env
cd bot

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
```

`PRAW_CLIENT_ID` and `PRAW_CLIENT_SECRET`
are for Reddit commands (memes etc), see [Reddit script app OAuth2](https://github.com/reddit-archive/reddit/wiki/OAuth2)
for info how to get them.

`BOT_TOKEN` the most important one. You can get one by [creating a Discord bot](https://discordapp.com/developers/applications)

`API_ACCESS_TOKEN` token to access our API. You don't need this but some features
will be unavailable, we use this for example: checking if user is verified,
verifying new users, putting new users, editing users(infractions, leave date) etc..

`SOCKET_AUTH_TOKEN` token to connect to our bot socket. 
This is so the API can communicate with the bot,
for example when member verifies on website the bot receives this verification trough the socket
and adds roles to members/send him message etc

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
pipenv run start
```

# License

MIT - see [LICENSE](LICENSE) file for details.
