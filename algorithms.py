import json
s
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


def EventManage(arg):
    announcements =get_announce()
    data={

       "AnnounceSchedule":announcements,
       "Event"          : str(arg)

         }
    with open("controlpanel.txt","w") as outfile:
      json.dump(data,outfile)

def AnnounceManage(arg):
    eventss=get_event()
    data={

       "AnnounceSchedule":str(arg) ,
       "Event"          : eventss

         }
    with open("controlpanel.txt","w") as outfile:
      json.dump(data,outfile)

def get_announce():
  with open("controlpanel.txt","r") as jsonfile:
    saca = json.load(jsonfile)
    return str( saca["AnnounceSchedule"])

def get_event():
  with open("controlpanel.txt","r") as jsonfile:
    data = json.load(jsonfile)
    return str( data["Event"])

def create_issue(author_id):
  with open('tortoise.txt') as json_file:
    data = json.load(json_file)
    data["reporters"].append({
    "user_id":author_id,
    "status":"false"})
    with open('tortoise.txt', 'w') as outfile:
     json.dump(data, outfile)



def get_data():
  with open("tortoise.txt","r") as jsonfile:
    data = json.load(jsonfile)
    return (data)



def set_data(data):
  with open("tortoise.txt","w") as outfile:
    json.dump(data, outfile)
