import discord
from discord.ext import commands
import json
from discord.utils import get


class RoleCommands(commands.Cog):
    def __init__(self, client):
        self.bot = client

    @commands.group(name='joinrole', invoke_without_command=True)
    async def joinrole(self,ctx):
        try:    
            detectjoin = open("./autorole.json")
            object = json.load(detectjoin)
            guild = ctx.guild
            role= object[str(guild.id)]
            role = discord.utils.get(guild.roles,id=role)
            embed=discord.Embed(title="Autorole settuped for the guild",
            description=f"{role.mention} ", color=0x04fb42)
            await ctx.send(embed=embed)
        except:
            embed=discord.Embed(title="Join role not settuped", description=f"Not giving any role to joining user", color=0xFE0000)
            embed.set_footer(text=f'Use (.joinrole add @role) command if you want to setup autorole/joinrole')
            await ctx.send(embed=embed)

    @joinrole.command()
    async def add(self,ctx,role:discord.Role):
        rdata = open("./autorole.json", "r")
        role_object = json.load(rdata)
        rdata.close()
        guild = ctx.guild
        role_object[str(guild.id)] = role.id
        rdata = open("./autorole.json", "w")
        json.dump(role_object, rdata,indent=4)
        rdata.close()

        embed=discord.Embed(title="Join role added successfully ", description=f"{role.mention} will be given to joining members from now", color=0x04fb42)
        embed.set_footer(text=f'Setted By - {ctx.author}',
        icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @joinrole.command()
    async def remove(self,ctx):
        try:
            with open("./autorole.json","r") as f:
                roles = json.load(f)
            guild = ctx.guild
            roles.pop(str(guild.id))
            with open("./autorole.json","w") as f:
                json.dump(roles,f,indent=4)

            embed=discord.Embed(title="Removed", description=f"Succesfuly disabled autorle", color=0xFE0000)
            await ctx.send(embed=embed)
        except:
            embed=discord.Embed(title="Failed", description=f"Not found", color=0xFE0000)
            await ctx.send(embed=embed)
            



    @commands.command()
    @commands.has_permissions(manage_roles=True) 
    async def rcreate(self,ctx,*, name):
        guild = ctx.guild
        await guild.create_role(name=name)
        await ctx.send(f'Role `{name}` has been created')

    @commands.command()
    @commands.has_permissions(manage_roles=True) 
    async def rdelete(self,ctx,*, name):
        await ctx.send(f"We don't do that, go delete it by yourself lazy ass")

    @commands.command(name='role',pass_context=True)
    @commands.has_permissions(administrator=True,manage_roles=True)
    async def role(self,ctx,rtype,user:discord.Member=None,*,role:discord.Role):
        if rtype=='add' or rtype=='give':
            if role in user.roles:
                embed1=discord.Embed(title="Failed", description=f"{user.mention} already have {role.mention}", color=0xFE0000)
                embed1.set_footer(text=f'Use (.role remove) command if you want to remove it from the user')
                await ctx.send(embed=embed1)

            else:
                await user.add_roles(role)
                embed2=discord.Embed(title="Role added successfully ", description=f"{role.mention} is added to {user.mention}", color=0x04fb42)
                embed2.set_footer(text=f'Given By - {ctx.author}',
            icon_url=ctx.author.avatar_url)
                await ctx.send(embed=embed2)

        elif rtype=='remove' or rtype=='rm':
            if role not in user.roles:
                embed3=discord.Embed(title="Failed", description=f"{user.mention} dont have {role.mention} so you can't remove it", color=0xFE0000)
                embed3.set_footer(text=f'Use (.role add) command if you want to add it to the user')
                await ctx.send(embed=embed3)

            else:
                await    user.remove_roles(role)
                embed4=discord.Embed(title="Role removed successfully ", description=f"{role.mention} is removed from {user.mention}", color=0x04fb42)
                embed4.set_footer(text=f'Removed By - {ctx.author}',
                icon_url=ctx.author.avatar_url)
                await ctx.send(embed = embed4)

        elif rtype==None: 
            await ctx.send("Please sellect a valid type (add/remove)")
        else:
            await ctx.send("Please sellect a valid type (add/remove)")

def setup(client):
    client.add_cog(RoleCommands(client)) 
