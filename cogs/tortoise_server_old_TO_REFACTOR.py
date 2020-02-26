import asyncio
import discord
from discord.ext import commands

announcements_channel_id = 578197131526144024
welcome_channel_id = 591662973307584513


class TortoiseServer(commands.Cog):
    """These commands will only work in the tortoise discord server."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role("Admin", "Moderator")
    async def events(self, ctx, arg):
        EventManage(arg.lower())
        embed = discord.Embed(title="**Success!**",
                              description=f"Events turned **{arg.upper()}** successfully!",
                              color=0x13D910)
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_any_role("Admin", "Moderator")
    async def announcements(self, ctx, arg):
        AnnounceManage(arg.lower())
        embed = discord.Embed(title="**Success!**",
                              description=f"Announcements turned **{arg.upper()}** successfully!",
                              color=0x13D910)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_any_role("Admin", "Moderator", "Helpers")
    async def attend(self, ctx):
      tortoise = client.get_guild(577192344529404154)
      xchannel = tortoise.get_channel(580809054067097600) 
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
           gembed = discord.Embed(title = f"You can chat and resolve the issue here:" ,description=f"**MEMBER ONLINE:** {member.name} \n type `t.stop` to end the session. " ,color = 0xF2771A)
           gembed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")
           await ctx.author.send(embed=gembed)
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
                if wait_msg.attachments:
                    url = wait_msg.attachments[0].url
                    xembed.set_image(url=url)
                    await member.send(embed=xembed)
                else:    
                 await member.send(wait_msg.content)
             elif wait_msg.author.id == i["user_id"]:
                if wait_msg.attachments:
                    url = wait_msg.attachments[0].url
                    xembed.set_image(url=url)
                    await ctx.author.send(embed=xembed)
                else:    
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
     """To submit answer of events. - works only on dm!"""
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
       await ctx.send("**Paste your code below : (no formatting required) **")
       try:
        msg=await client.wait_for('message',check=check(ctx.author,ctx.channel), timeout=30)
        tortoise = client.get_guild(577192344529404154)
        channel = tortoise.get_channel(610079185569841153)
        events = tortoise.get_channel(607597453545570325)
        winner = tortoise.get_role(615629355875565568)
        member = tortoise.get_member(ctx.message.author.id)
        '''if "HaveYouSeenTheMockTurtleYet" in msg.clean_content:
          eventend=discord.Embed(title="The Event has officially ended",description=f"\n\n**WINNER: {ctx.author.mention}\nFLAG: HaveYouSeenTheMockTurtleYet**\n\nThank you for participating in the event. Stay tuned for more events...",color=0x3498DB)
          eventend.set_author(name="Tortoise Community",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")
          mess = await events.send("<@&610834658267103262><@&603157798225838101>")
          await mess.delete()
          await events.send(embed=eventend) 
          await member.add_roles(winner)
          EventManage("off")
          await ctx.send(embed=eventends)
        else :
          msgg=randommessage()
          mess=await ctx.send(msgg)
          time.sleep(5)
          await mess.delete()  '''
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
        """To report bugs with in the bot functions. - works only on dm!"""
        def check(author, channel):
            def inner_check(message):
                return message.author == author and message.channel == channel
            return inner_check
        await ctx.send("**Describe the bug below :**")
        try:
            msg = await self.bot.wait_for("message", check=check(ctx.author, ctx.channel), timeout=60)
            tortoise = self.bot.get_guild(577192344529404154)
            channel = tortoise.get_channel(581139962611892229)
            if "```"in msg.clean_content:
                await channel.send(f"<@&594468482859663370>\n{ctx.message.author.name} just reported a possible bug:\n\n{msg.clean_content}")
            else:
                await channel.send(f"<@&594468482859663370>\n{ctx.message.author.name} just reported a possible bug:\n\n```\n{msg.clean_content}```")
                await ctx.send(embed=bugsuccess)
        except asyncio.TimeoutError:
            await ctx.send(embed=bugtimeout)
       
    @commands.command()
    @commands.dm_only()
    async def report(self, ctx):
        data = get_data()
        for user in data["reporters"]:
            if user["user_id"] == ctx.author.id and user["status"] == "false":
                await ctx.send(embed=errorbed)
                return
        tortoise = self.bot.get_guild(577192344529404154)
        xchannel = tortoise.get_channel(580809054067097600)
        await ctx.send(embed=membed)
        create_issue(ctx.author.id)

        embed = discord.Embed(title=f"**OPEN-REPORT!**",
                              description=f"{ctx.author.mention} just opened up a report.\n\nType in` t.attend` to attend ",
                              color=0xF2771A)
        embed.set_author(name="MOD-MAIL", icon_url=ctx.me.avatar_url)
        await xchannel.send(f"<@&605808609128873985>")
        await xchannel.send(embed=embed)


def setup(bot):
    bot.add_cog(TortoiseServer(bot))
