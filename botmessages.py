import discord

verified = discord.Embed(title = f"""Greetings from the ** Tortoise Community!** \n\nYou are now a verified member of the community <:verified:610713784268357632> \nBy joining the server you have agreed to abide by its rules .\nPlease read #welcome and make yourself at home.\n   """ , color = 0x13D910)

bugtimeout = discord.Embed(title = f"**Submission timed out**",description=" \nTo retry type **t.bugreport**" , color = 0xFF0000)

bugsuccess = discord.Embed(title = f"**Processed!**",description="\nThe bug info is successfully submitted.\nThank you!" , color = 0x00FF59)
bugsuccess.set_footer(text="Tortoise community")
subtimeout = discord.Embed(title = f"**Submission timed out **",description="\nTo retry type **t.submit**" , color = 0xFF0000)

subsuccess = discord.Embed(title = f"**Your Code is sucessfully submitted!**",description="\n Thank you for participating in the event." , color = 0xF2771A)
subsuccess.set_footer(text="Tortoise community")

mailtimeout = discord.Embed(title = f"**Session timed out **",description="\nTo restart type **t.report**" , color = 0xFF0000)
mailtimeout.set_footer(text="Tortoise Community")
mailtimeout.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")



membed = discord.Embed(title = f"**You have opened a private report session with the Staff of the Tortoise Community!** ",description="Someone will respond shortly, You can get on with your work.\n We will notify you." , color = 0xFF7000)
membed.set_footer(text="Tortoise Community")
membed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")


endbed = discord.Embed(title = f"**The Staff have closed the report session** ",description="If you want to continue please type **t.report**" , color = 0xF92AFF)
endbed.set_footer(text="Tortoise Community")
endbed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")

modbed = discord.Embed(title = f"**MOD connected!** ",description="You can use `t.stop `to end the session.\n(Do not misuse the Mod-mail)" , color = 0x13D910)
modbed.set_footer(text="Tortoise Community")
modbed.set_author(name="MOD-MAIL",icon_url="https://i.ibb.co/rxM1zqC/bot-2.png")

Freport_bed = discord.Embed(title = f"""**There are now live reports at this moment**""" , color = 0xFF0000)

Treport_bed = discord.Embed(title = f"""**Report attended successfully!**.""" , color = 0x13FE00)

errorbed= discord.Embed(title = f"""**You have already opened one report**\nYou cannot open multiple reports at one time.""" , color = 0x13FE00)

stembed = discord.Embed(title = f"**Report session closed!\n Thank you!** " , color = 0xF92AFF)
