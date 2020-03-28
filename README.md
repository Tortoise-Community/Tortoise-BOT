![Python-Versions](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue?style=flat-square)
![Discord.py-Version](https://img.shields.io/badge/discord.py-1.3.2-blue?style=flat-square)

# Tortoise-BOT
**Fully functional Bot for Discord coded in Discord.py**

<img align="right" src="https://i.imgur.com/7LrGjdG.jpg" width=40%>

## Features and Commands :

To do, check out cogs source code directory to see for yourself.

## Installation Instructions

```bash
git clone https://github.com/Tortoise-Community/Tortoise-BOT.git
<!-- Clone the repo -->  

cd Tortoise-BOT
<!-- Change directories into the project -->

pip install -r requirements.txt
<!-- Python 3.6 minimum required -->

touch .env
<!-- Create env file used to store tokens -->

nano .env
<!-- Edit the .env files and add tokens -->
```

#### Sample layout of `.env` file

```bash
PRAW_CLIENT_ID=put_something_here
PRAW_CLIENT_SECRET=put_something_here
BOT_TOKEN=put_something_here
API_ACCESS_TOKEN =put_something_here
SOCKET_AUTH_TOKEN=put_something_here
DEBUG=False
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

For playing music see [discord.py dependencies](https://discordpy.readthedocs.io/en/latest/intro.html#installing)
and you'll need ffmpeg either in the root directory or in your PATH.
For linux you can install it with `sudo apt install ffmpeg`

### Once everything is ready

Run the bot!

```bash
python main.py
<!-- Run the bot -->
```

# License

MIT - see [LICENSE](LICENSE) file for details.