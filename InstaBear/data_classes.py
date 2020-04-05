from datetime import datetime
from hashlib import md5
from os import path,makedirs

def dt_to_unix(dt):
    return (dt-datetime(1970,1,1)).total_seconds()

class User:
    def __init__(self,data):
        self.id = data['user']['id']
        self.name = data['user']['username']
        self.picture = data['user']['profile_pic_url']
        self.stories = []

    async def save_to_db(self,bear):
        res = await bear.db.select(table="users", fields=["name", "current_pfp"], params={"id":self.id, "account":bear.username})
        if not res:
            await bear.db.insert(table="users", values={"id":self.id, "name":self.name, "current_pfp":self.picture, "account":bear.username})
        else:
            if res.name!=self.name or res.current_pfp!=self.picture:
                await bear.db.update(table="users", values={"name":self.name, "current_pfp":self.picture}, params={"id":self.id, "account":bear.username})
        
        pfp_id = self.picture.split("/")[4]
        res = await bear.db.select(table="profile_pictures", fields=["id"], params={"id": pfp_id})
        if not res:
            async with bear.client.get(self.picture) as img:
                if img.status==200:
                    img = await img.read()
                    await bear.db.insert(table="profile_pictures", values={"id":pfp_id, "user_id":self.id, "media":img})
                else:
                    bear.log.warn("Profile picture link did not return 200 ({})".format(self.id))

class Story:
    def __init__(self,data):
        self.id = data['id']
        self.uploaded = datetime.utcfromtimestamp(data['taken_at_timestamp'])
        if data['is_video']:
            self.link = data['video_resources'][-1]['src']
            self.mime = data['video_resources'][-1]['mime_type']
            self.ext = self.mime.split(";")[0].split("/")[-1]
        else:
            self.link = data['display_resources'][-1]['src']
            self.ext = 'jpg'

    async def check_exists(self,bear):
        res = await bear.db.select(table="stories", fields="1", params={"id":self.id})
        if res:
            return True

    async def save_to_db(self,bear,user):
        if not await self.check_exists(bear):
            async with bear.client.get(self.link) as res:
                if res.status==200:
                    if await bear.db.insert(table="stories", values={
                        "id":self.id,
                        "uploaded":dt_to_unix(self.uploaded),
                        "media":await res.read(),
                        "user_id":user.id,
                        "ext":self.ext
                    }):
                        return 1
        return 0

