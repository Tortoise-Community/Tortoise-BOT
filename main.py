import discord
from discord.ext import commands
import praw
import os
import random
from algorithm  import *
import time
import asyncio
from itertools import cycle
import welcome
from welcome import *
from dictionary import *
import botmessages
from botmessages import *
client = commands.Bot(command_prefix='t.')
game = 'Managing Tortoise community'
botid = 4446546548594480650

reddite = praw.Reddit(client_id='Your-id',
                      client_secret='Your-secret',
                      user_agent='your-agent',
                      username='your-user-name')



status=['the Community','t.report for MOD-MAIL','the Server','out for Spam','t.report for MOD-MAIL']


async def change_status():
  await client.wait_until_ready()
  NowPlaying = cycle(status)
  tortoise = client.get_guild(577192344529404154)
  while not client.is_closed():
    CurrentStatus=next(NowPlaying)
    await client.change_presence(status =discord.Status.online, activity = discord.Activity
    (type=discord.ActivityType.watching, name= CurrentStatus))
    await asyncio.sleep(15)

    
@client.event
async def on_message(message):
  if message.author.bot:
        return     
  for i in bannedwords:
    if i in message.content.lower():
        xchannel = client.get_channel(597119801701433357)
        if len(message.author.roles)==2:
         if bannedwords[i]=='swear':
          await message.delete()
          dembed = discord.Embed(title="Warning!",description=f"Swear detected: ||{i}||  by **{message.author.name}** in {message.channel}\n {message.author.mention} Get yourself a role to use swears , Also if found offensive for the community guidlines or to any members you will be booted from the community \n Use <#603651772950773761> to get a role",color=0xFFC300)
          msg="**MESSAGE CLEARED**   REASON: `Use of curse detected`"
          await message.channel.send(msg)
          await xchannel.send(embed=dembed)
        if bannedwords[i]=='Racial Abuse':
         await message.delete()
         msg="**MESSAGE CLEARED**   REASON: `Use of Racial Abuse detected`"
         await message.channel.send(msg)
         dembed = discord.Embed(title = f"**Infraction information**",description= f"\n**NAME: **{message.author.name}\n**TYPE: **Ban\n**REASON: **Usage of Racial Abuse inside the community.\n**ATTEMPT: **1\n**DURATION: **Permenent"  , color = 0xFF0000)
         dembed.set_footer(text="Tortoise Community")
         dmembed = discord.Embed(title = f"**Infraction information**",description= f"""\n**TYPE: **Ban\n**REASON: **Usage of Racial Abuse inside the community.  \n**DURATION: **Permenent\n"""  , color = 0xFF0000)
         dmembed.set_footer(text="Tortoise Community")
         await xchannel.send(embed=dembed)
         await message.author.send(embed=dmembed)
         await message.author.ban()
         
        tortoise = client.get_guild(577192344529404154)
        Admin= tortoise.get_role(577196762691928065) 
        mod = tortoise.get_role(577368219875278849) 
        '''if Admin not in message.author.roles : 
         if bannedwords[i]=='Discord link':
           await message.delete()
           await message.channel.send("**MESSAGE CLEARED**   REASON: `Discord link detected`")
           Advertiser_id=str(message.author.id)
           Advertisers=open("selfpromotion.txt","r+")
           Warned_once=Advertisers.read().splitlines()
           if Advertiser_id in Warned_once:
             await xchannel.send(f"Use of **Discord link** by**{message.author}**  detected  in {message.channel.mention}\n  {message.author.mention} is here by **BANNED** from the server\n\n** DURATION:** `Permenent ` \n **REASON:**`Self-Advertising in the server `" )
             await message.author.send("You have violated the Rules of the community and action is taken against you. \n**TYPE: **`Ban`\n**REASON: **` Self-Advertising inside the community `\n**DURATION: **`Permenent` \n\n             **Tortoise community** ")
             await message.author.ban()
           else:
            await xchannel.send(f"Discord link detected. Used by **{message.author}** in {message.channel.mention}.\n {message.author.mention} Self-Advertisement is  **NOT-ALLOWED ** inside the Community. If you are caught again with this, you will be directly banned. " )
            Advertisers.write("\n"+Advertiser_id)
           Advertisers.close()'''
        if bannedwords[i]=='Racial Slur' or bannedwords[i]=='Homophobic Slur':
         await message.delete()
         guy=str(message.author.id)
         if bannedwords[i]=='Racial Slur':
           reason="Racial Slur"
         else:
            reason="Homophobic Slur"
         await message.channel.send(f"**MESSAGE CLEARED**   REASON: `Use of {reason} detected`")
         person=str(message.author)
         msg=str(message.content)
         record=open("deletedmessages.txt","r+")
         record.write("\n"+person+" : "+msg)
         record.close()
         blacklist=open("blacklist1.txt","r+")
         blacklisted=blacklist.read().splitlines()
         if guy in blacklisted:
            attempt='2'
            warnn='FINAL-WARNING!'
            warn=open("blacklist2.txt","r+")
            warned = warn.read().splitlines()
            if guy in warned:
              attempt='3'
              dembed = discord.Embed(title = f"**Infraction information**",description= f"\n**NAME: **{message.author.name}\n**TYPE: **Ban\n**REASON: **Using {reason}s\n**ATTEMPT: **{attempt}\n**DURATION: **Permenent"  , color = 0xFF0000)
              dembed.set_footer(text="Tortoise Community")
              dmembed = discord.Embed(title = f"**Infraction information**",description= f"""\n**TYPE: **Ban\n**REASON: **Use of {reason}s inside the community.\n**DURATION: **Permenent\n(If this happened by a mistake,contact <@125759308515246080> for reviewal)"""  , color = 0xFF0000)
              dmembed.set_footer(text="Tortoise Community")
              await xchannel.send(embed=dembed)
              await message.author.send(embed=dmembed)
              await message.author.ban()
            else:
              warn.write("\n"+guy)
            warn.close()
         else:
            attempt='1'
            warnn='FIRST-WARNING!'
            blacklist.write("\n"+guy)
         blacklist.close()
         if attempt!='3':
          dembed = discord.Embed(title="**Warning!**",description=f"{reason} detected : ||{i}||  by **{message.author}** in {message.channel.mention}\n **{warnn}** {message.author.mention}  {reason}s are **STRICTLY BANNED ** inside the Community \n**ATTEMPTS:**{attempt}",color=0xFF8B00)
          dembed.set_footer(text="Tortoise Community")
          await channelx.send(embed=dembed)

         if attempt=='2':
          dembed = discord.Embed(title="Warning!",description=f"We have detected your use of {reason} which are **STRICTLY PROHIBITED** inside the community.\nThis an infringement of our server rules stated in <#591662973307584513>.\nConsider this as the **FINAL WARNING**. If you are picked up repeating this again, Direct action will be taken.\nIf this happened by a mistake please contact one of the moderators to review the messages",color=0xFF8B00)
          dembed.set_footer(text="Tortoise Community")
          await message.author.send(embed=dembed)

  await client.process_commands(message)    
    

@client.event
async def on_ready():
    print('All set')

#----------------------------------------------------------------------------------------------------------------------
#Adds role to the user based on reaction
"""You will need to make a role and a custom emoji of the same name and add a seperate channel for this function to work"""
reaction_channel_id = 56518465156515646546
@client.event
async def on_raw_reaction_add(payload):
  if payload.channel_id == reaction_channel_id:
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g : g.id == guild_id, client.guilds)
        member = discord.utils.find(lambda m : m.id == payload.user_id,guild.members)
        role = discord.utils.get(guild.roles,name = payload.emoji.name )
        await member.add_roles(role)


@client.event
async def on_raw_reaction_remove(payload):
  if payload.channel_id == reaction_channel_id:
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g : g.id == guild_id, client.guilds)
        member = discord.utils.find(lambda m : m.id == payload.user_id,guild.members)
        role = discord.utils.get(guild.roles,name = payload.emoji.name )
        await member.remove_roles(role)
#----------------------------------------------------------------------------------------------------------------------


@client.event
async def on_guild_join(ctx):
    print(f'joined {ctx.guild.name}')
    embed = discord.Embed(description="I'm the Tortoise BOT (beta. I'm here for Bot testing and development.  use `T.` before a command",
                          color=0x3498db)


@client.event
async def on_member_join(member: discord.Member):
    tortoise = client.get_guild(577192344529404154)
    unverified = tortoise.get_role(605808609195982864)
    await member.add_roles(unverified)

@client.event
async def on_member_remove(member: discord.Member):
  systemlog=client.get_channel(593883395436838942)
  embed = discord.Embed(title = f"""**Goodbye!**\n{member.name} has left the Tortoise Community""" , color = 0xFF0000)
  await systemlog.send(embed = embed)


class MyHelpCommand(commands.MinimalHelpCommand):
    def get_command_signature(self, command):
        return '{0.clean_prefix}{1.qualified_name} {1.signature}'.format(self, command)

class MyCog(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = MyHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

class admins(commands.Cog):
    """You will require admin permissions to use these commands """

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason='No specific reason'):
        channelx=client.get_channel(597119801701433357)
        """kick a member , You will require the permissions to use this command"""
        dmembed = discord.Embed(title = f"**Infraction information**",description= f"""\n**TYPE: **Ban\n**REASON: **{reason}\n**DURATION: **24 hours\n(If this happened by a mistake,contact <@125759308515246080> for reviewal)\nYou can rejoin the server after the cooldown from here"""  , color = 0xFF0000)
        dmembed.set_footer(text="Tortoise Community")
        dembed = discord.Embed(title = f"**{member.name} is kicked from the server.**",description= f"\n**REASON: **`{reason}`\n**DURATION: **`24 hours`"  , color = 0xFF0000)
        await member.send(embed = dmembed)
        await channelx.send(embed = dembed)
        await member.kick(reason = reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason='No specific reason'):
        """Bans a member , You will require the permissions to use this command"""
        channelx=client.get_channel(597119801701433357)
        dmembed = discord.Embed(title = f"**Infraction information**",description= f"""\n**TYPE: **Ban\n**REASON: **{reason}\n**DURATION: **Permenent\n(If this happened by a mistake,contact <@125759308515246080> for reviewal)"""  , color = 0xFF0000)
        dmembed.set_footer(text="Tortoise Community")
        dembed = discord.Embed(title = f"**{member.name} is banned from the server.**",description= f"\n**REASON: **{reason}\n**DURATION: **Permenent"  , color = 0xFF0000)
        await member.send(embed = dmembed)
        await channelx.send(embed = dembed)
        await member.ban(reason=reason)


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self,ctx,member:discord.Member,*,reason):
       """Warns a member , you will require the permissions to use this command """
       channelx=client.get_channel(597119801701433357)
       embed = discord.Embed(title = f"**{member.name} You have been warned for {reason}**",description= f" If you are planning to repeat this again, the mods may administer punishment for the action."  , color = 0xF4D03F )
       await ctx.channel.purge(limit=1)
       await channelx.send(f"{member.mention}")
       await channelx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, role_: discord.Role, member: discord.Member):
        # adds a role to a member

        if member is None:
            await ctx.send('mention the member')
        else:
            await member.add_roles(role_)
            embed=discord.Embed(title = f"Role Added!",description= f"{member.mention} is now a {role_.name}"  , color = 0x1ADB43 )
            dmbed=discord.Embed(title = f"**Congratulations!** \n\nYou are now promoted to a **{role_.name}** of the community.\n`'With great power comes great responsibility'`\nBe active and keep the community safe."  , color = 0xFFC300   )
            dmbed.set_footer(text="Tortoise community")
            await ctx.send(embed=embed)
            await member.send(embed=dmbed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """clears messages, you will require the Manage messages permission to use this command"""

        if amount == None:
            await ctx.send('Please specify the number of messages you want to clear ... example ```t.clear 6```')
        else:
            await ctx.channel.purge(limit=amount+1)
            await ctx.send('**MESSAGES CLEARED** ' + ctx.message.author.mention)
            time.sleep(3)
            await ctx.channel.purge(limit=1)


class fun(commands.Cog):
    @commands.command()
    async def slap(self, ctx, *, member: discord.Member):
        """Slaps a member"""

        if member is None:
            await client.say('mention who you want to slap you fool' + ctx.message.author.mention)
        else:
            if member.id == ctx.message.author.id:
                await ctx.send(ctx.message.author.mention + " slapped him/her self LOL")
            elif member.id == 247292930346319872:
                embed = discord.Embed(
                    description=ctx.message.author.mention + "Nah you can't slap my dad!.....wait I will kick him in the balls for you ;-)")
                embed.set_image(url="https://media.giphy.com/media/3o7TKwVQMoQh2At9qU/giphy.gif")
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(
                    description=member.mention + " got slapped in the face by: " + ctx.message.author.mention + "!")
                embed.set_image(
                    url="https://66.media.tumblr.com/05212c10d8ccfc5ab190926912431344/tumblr_mt7zwazvyi1rqfhi2o1_400.gif")
                await ctx.send(embed=embed)

    @commands.command()
    async def shoot(self, ctx, *, member: discord.Member):
        """Shoots a member"""

        if member.id == 247292930346319872:
            embed = discord.Embed(description=ctx.message.author.mention + "Anyday!")
            embed.set_image(url="https://media.giphy.com/media/oQfhD732U71YI/giphy.gif")
            await ctx.send(embed=embed)

        elif ctx.message.author.id == 247292930346319872 and member.id == 247292930346319872:

            embed = discord.Embed(description=ctx.message.author.mention + ' DAD! DONT SHOOT YOURSELF')
            embed.set_image(url="https://media.giphy.com/media/f2fVSJWddYb6g/giphy.gif")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=member.mention + ' shot by ' + ctx.message.author.mention + ' :gun: :boom: ')
            embed.set_image(url='https://i.gifer.com/XdhK.gif')
            await ctx.send(embed=embed)


class other(commands.Cog):

    @commands.command()
    async def say(self, ctx, arg):
        """Says something"""

        await ctx.send(arg)

    @commands.command()
    async def members(self, ctx):
        """returns the number of members in a server"""
        await ctx.send(f'```{ctx.guild.member_count}```')

    @commands.command()
    async def status(self, ctx, *, member: discord.Member):
        """Returns the status of a member"""

        if member.id == 577140178791956500:
            await ctx.send("**I AM ONLINE , CAN'T YOU SEE?**")

        elif member.is_on_mobile():
            await ctx.send(f"```{member} is {member.status} but is on phone```")


        else:
            await ctx.send(f"```{member} is {member.status}```")

    @commands.command()
    async def pfp(self, ctx, *, member: discord.Member):
        """Displays the profile picture of a member"""

        if member.id == botid:
            await ctx.send(f' my avatar {member.avatar_url} ')

        await ctx.send(f'{member.mention} avatar {member.avatar_url} ')


    @commands.command()
    async def github(self,ctx):
      """GitHub repository"""

      embed = discord.Embed(title = """ Github repository""" , url = "https://github.com/fwizzz/Tortoise-Discord-Bot/" , color = 0x206694)

      await ctx.send(embed = embed)


class tortoise_server(commands.Cog):
    """these commands will only work in the tortoise discord server"""
    @commands.command()
    async def accept(self,ctx):
      if ctx.message.channel.id==602156675863937024:
       if len(ctx.message.author.roles)== 2:
        cpointchannel=client.get_channel(602156675863937024)
        tortoise = client.get_guild(577192344529404154)
        unverified = tortoise.get_role(605808609195982864)
        await ctx.message.author.remove_roles(unverified)
        role = tortoise.get_role(599647985198039050)
        systemlog=client.get_channel(593883395436838942)
        await ctx.message.author.add_roles(role)
        syslog = discord.Embed(title = f"""**Welcome!**\n{ctx.message.author.name} has joined the Tortoise Community""" , color = 0x13D910)
        await systemlog.send(embed = syslog)
        await ctx.author.send(embed=verified)
        await cpointchannel.purge(limit=100)
        await cpointchannel.send("<@&605808609195982864>")
        await cpointchannel.send("Hi there!\nWelcome to **Tortoise Community** discord server.\n"+rules+'\n If you are ready to abide the rules of the community, Please Type **t.accept** to join the server\n(If you are having trouble verifying,contact Admin)')



    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, arg):
        channel = client.get_channel(578197131526144024)
        await channel.send(arggg)
        await ctx.send('Announced ✅')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def welcome(self, ctx, arg):
        channel = client.get_channel(591662973307584513)
        await channel.send(text)
        await ctx.send('Added in Welcome✅')


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def test(self, ctx, arg):
       tortoise = client.get_guild(577192344529404154)
       pass


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def events(self, ctx, arg):
      EventManage(arg.lower())
      embed=discord.Embed(title="**Success!**",description=f"Events Turned {arg.upper()} successfully  ",color= 0x13D910)
      await ctx.send(embed = embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def announcements(self, ctx, arg):
      AnnounceManage(arg.lower())
      embed=discord.Embed(title="**Success!**",description=f"Announcements Turned **{arg.upper()}** successfully  ",color= 0x13D910)
      await ctx.send(embed = embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def attend(self, ctx):
      tortoise = client.get_guild(577192344529404154)
      xchannel = tortoise.get_channel(581139962611892229)
      if ctx.channel.id==580809054067097600:
       report_attend=False
       data= get_data()
       for i in data["reporters"]:
         if i["status"]=="false":
           report_attend=True
           i.update(status="True")
           set_data(data)
           member=tortoise.get_member(i["user_id"])
           await member.send(embed = modbed)
           embed = discord.Embed(title = f"You can chat and resolve the issue here:" ,description=f"**MEMBER ONLINE:** {member.name} \n type `t.stop` to end the session. " ,color = 0xF2771A)
           embed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")
           await ctx.author.send(embed=embed)
           def check_2(m):
             return m.guild is None and (m.author.id == ctx.author.id or m.author.id == i["user_id"])

           while True:
            try:

             wait_msg = await client.wait_for('message',check=check_2, timeout=500)
             if wait_msg.content == "t.stop":
                await member.send(embed=endbed)
                await ctx.author.send(embed=stembed)
                break
             elif wait_msg.author.id == ctx.author.id:
                await member.send(wait_msg.content)
             elif wait_msg.author.id == i["user_id"]:
                await ctx.author.send(wait_msg.content)
            except asyncio.TimeoutError:
                await member.send(embed = mailtimeout)
                break
           break
       if report_attend==False:
         await ctx.send(embed=Freport_bed)
       elif report_attend == True:
         await ctx.send(embed=Treport_bed)

    @commands.command()
    @commands.dm_only()
    async def submit(self, ctx):
     """To submit answer of events.(Works only on dm)"""
     Event=get_event()
     if Event=="off":
      embed = discord.Embed(title = f"""**There are no live events at this moment**\nStay tuned for more events.""" , color = 0xFF0000)
      await ctx.send(embed = embed)
     elif Event == "on":
      contestant=str(ctx.author.id)
      submitted=open("contestants.txt","r+")
      participated=submitted.read().splitlines()
      if contestant in participated:
         embed = discord.Embed(title = f"""It seems you have already participated in the contest.\nYou cannot submit the code again.""" , color = 0xFF0000)
         await ctx.send(embed = embed)
      else:
       def check(author,channel):
        def inner_check(message):
          return message.author == author and message.channel==channel
        return inner_check
       await ctx.send("**Paste your code below : **")
       try:
        msg=await client.wait_for('message',check=check(ctx.author,ctx.channel), timeout=30)
        tortoise = client.get_guild(577192344529404154)
        channel = tortoise.get_channel(610079185569841153)
        events = tortoise.get_channel(607597453545570325)
        if "```"in msg.clean_content:
         await channel.send(f"{ctx.message.author.name}'s submission\n\n{msg.clean_content}")
        else:
          await channel.send(f"{ctx.message.author.name}'s submission\n\n```py\n{msg.clean_content}```")
        await ctx.send(embed = subsuccess)
        submitted.write("\n"+contestant)
        embed = discord.Embed(title = f"""{ctx.author.name} has submitted the code!:thumbsup:""" , color = 0xF2771A)
        await events.send(embed = embed)
       except asyncio.TimeoutError:
        await ctx.send(embed = subtimeout)
      submitted.close()

    @commands.command()
    @commands.dm_only()
    async def bug(self, ctx):
       """To report bugs with in the bot functions.(Works only on dm)"""
       def check(author,channel):
        def inner_check(message):
          return message.author == author and message.channel==channel
        return inner_check
       await ctx.send("**Describe the bug below :**")
       try:
        msg=await client.wait_for('message',check=check(ctx.author,ctx.channel), timeout=60)
        tortoise = client.get_guild(577192344529404154)
        channel = tortoise.get_channel(581139962611892229)
        if "```"in msg.clean_content:
         await channel.send(f"<@&594468482859663370>\n{ctx.message.author.name} just reported a possible bug:\n\n{msg.clean_content}")
        else:
          await channel.send(f"<@&594468482859663370>\n{ctx.message.author.name} just reported a possible bug:\n\n```\n{msg.clean_content}```")
          await ctx.send(embed = bugsuccess)
       except asyncio.TimeoutError:
          await ctx.send(embed = bugtimeout)

    @commands.command()
    @commands.dm_only()
    async def report(self, ctx):
       data=get_data()
       for user in data["reporters"]:
        if user["user_id"]== ctx.author.id and user["status"]=="false":
          await ctx.send(embed=errorbed)
          return
       tortoise = client.get_guild(577192344529404154)
       xchannel = tortoise.get_channel(580809054067097600)
       await ctx.send(embed=membed)
       create_issue(ctx.author.id)
       embed = discord.Embed(title = f"**OPEN-REPORT!**" ,description=f"{ctx.author.mention} just opened up a report.\n\nType in` t.attend` to attend " ,color = 0xF2771A)
       embed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")
       await xchannel.send(f"<@&605808609128873985>")
       await xchannel.send(embed=embed)


    @commands.command()
    async def stop(self, ctx):
      pass


class reddit(commands.Cog):
    @commands.command()
    async def meme(self, ctx):
        """sends you the dankest of the dank memes from reddit"""
        subred = reddite.subreddit('memes')
        neewmeem = subred.hot(limit=100)
        lstmeem = list(neewmeem)
        randsub = random.choice(lstmeem)
        embed = discord.Embed(title=randsub.title,
                              description=f':thumbsup: {randsub.score} \n \n :speech_balloon:{len(randsub.comments)} ',
                              url=randsub.url, colour=0x3498d)
        embed.set_image(url=randsub.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def newpost(self, ctx, subreddit):
        """sends you the fresh posts from a subreddit"""
        subred = reddite.subreddit(f'{subreddit}')
        neewmeem = subred.new(limit=10)
        lstmeem = list(neewmeem)
        randsub = random.choice(lstmeem)
        embed = discord.Embed(title=randsub.title,
                              description=f':thumbsup: {randsub.score} \n \n :speech_balloon: {len(randsub.comments)} ',
                              url=randsub.url, colour=0x3498d)
        embed.set_image(url=randsub.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def hotpost(self, ctx, subreddit):
        """sends you the hottest posts from a subreddit"""
        subred = reddite.subreddit(f'{subreddit}')
        neewmeem = subred.hot(limit=10)
        lstmeem = list(neewmeem)
        randsub = random.choice(lstmeem)
        embed = discord.Embed(title=randsub.title,
                              description=f':thumbsup: {randsub.score} \n \n :speech_balloon: {len(randsub.comments)} ',
                              url=randsub.url,
                              colour=0x3498db)
        embed.set_image(url=randsub.url)
        await ctx.send(embed=embed)

@client.event
async def on_command_error(ctx, error):
   embed=discord.Embed(title="**Not your day boi!**",description=f"{error}",color=0xF40000)
   await ctx.send(embed=embed)

client.add_cog(admins(client))
client.add_cog(fun(client))
client.add_cog(other(client))
client.add_cog(tortoise_server(client))
client.add_cog(reddit(client))
client.loop.create_task(change_status())
client.run(TOKEN)
