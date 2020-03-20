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
<!-- Use this if you only have Python 3 installed. -->

touch .env
<!-- Create env file used to store tokens -->

nano .env
<!-- Edit the .env files and add tokens -->
```

Sample layout of `.env` file:
```bash
PRAW_CLIENT_ID=put_something_here
PRAW_CLIENT_SECRET=put_something_here
BOT_TOKEN=put_something_here
API_REFRESH_TOKEN=put_something_here
```

Values other than `BOT_TOKEN` are not needed, 

```bash
python main.py
<!-- Run the bot -->
```

For playing music see [discord.py dependencies](https://discordpy.readthedocs.io/en/latest/intro.html#installing)
and you'll need ffmpeg either in the root directory or in your PATH.