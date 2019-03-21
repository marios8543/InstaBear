from datetime import datetime
from hashlib import md5
from os import path,makedirs
import aiofiles

def dt_to_unix(dt):
    return (dt-datetime(1970,1,1)).total_seconds()

class User:
    def __init__(self,data):
        self.id = data['user']['id']
        self.name = data['user']['username']
        self.picture = data['user']['profile_pic_url']
        self.stories = []

    async def save_to_db(self,bear):
        await bear.db.execute("INSERT INTO users (id,name,current_pfp) values(%s,%s,%s) ON DUPLICATE KEY UPDATE name=%s, current_pfp=%s",(self.id,self.name,self.picture,self.name,self.picture,))
        pfp_id = self.picture.split("/")[4]
        res = await bear.db.execute("SELECT id FROM profile_pictures WHERE id=%s",(pfp_id,))
        if not res:
            async with bear.client.get(self.picture) as img:
                if img.status==200:
                    img = await img.read()
                    await bear.db.execute("INSERT INTO profile_pictures(id,user_id,media) values(%s,%s,%s)",(pfp_id,self.id,img,))
                else:
                    bear.warning("Profile picture link did not return 200 ({})".format(self.id))

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
        res = await bear.db.execute("SELECT 1 FROM stories WHERE id=%s",(self.id,))
        if res:
            return True

    async def save_to_db(self,bear,user):
        if not await self.check_exists(bear):
            async with bear.client.get(self.link) as res:
                if res.status==200:
                    if await bear.db.execute("INSERT INTO stories (id,uploaded,media,user_id,ext) values(%s,%s,%s,%s,%s)",(self.id,dt_to_unix(self.uploaded),await res.read(),user.id,self.ext,)):
                        return 1
        return 0

    async def save_to_fs(self,bear,user):
        if not path.exists(path.join(bear.photo_dir,user.name)):
            makedirs(path.join(bear.photo_dir,user.name))
        p = path.join(bear.photo_dir,user.name,self.uploaded.strftime("%Y-%m-%d_%H-%M-%S"))+"."+self.ext
        if path.exists(p):
            return 0
        async with bear.client.get(self.link) as res:
            if res.status==200:
                async with aiofiles.open(p,mode="wb",loop=bear.client.loop) as f:
                    await f.write(await res.read())
                    await f.close()
                    return 1
        return 0


