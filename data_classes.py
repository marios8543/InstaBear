from aiohttp import ClientSession,CookieJar
from asyncio import sleep
from datetime import datetime
from json import dumps
from os import path,makedirs
from time import ctime
import aiofiles
import queries

class User:
    def __init__(self,data):
        self.id = data['user']['id']
        self.name = data['user']['username']
        self.picture = data['user']['profile_pic_url']
        self.stories = []

class Story:
    def __init__(self,data):
        self.id = data['id']
        self.uploaded = datetime.fromtimestamp(data['taken_at_timestamp'])
        self.expires = datetime.fromtimestamp(data['expiring_at_timestamp'])
        if data['is_video']:
            self.link = data['video_resources'][-1]['src']
            self.mime = data['video_resources'][-1]['mime_type']
            self.ext = self.mime.split(";")[0].split("/")[-1]
        else:
            self.link = data['display_resources'][-1]['src']
            self.ext = 'jpg'

class Bear:
    def __init__(self,config):
        self.username = config['username'] if 'username' in config else ""
        self.password = config['password'] if 'password' in config else ""
        if 'photo_dir' in config and path.isdir(config['photo_dir']):
            self.photo_dir = config['photo_dir']
        else:
            self.error("Photo directory not specified or invalid")
            exit(1)
        self.excluded = config['excluded'] if 'excluded' in config and type(config['excluded']) is list else []
        if 'interval' in config:
            try:
                self.interval = int(config['interval'])
            except Exception:
                self.interval = 300
        else:
            self.interval = 300
        cookie_jar = CookieJar(unsafe=True)
        self.client = ClientSession(cookie_jar=cookie_jar,cookies=config['cookies'])
        self.users = []
        self.userId = config['cookies']['ds_user_id']
        self.scraped = []


    def warn(self,msg):
        print("WARNING [{}] {}".format(self.username,msg))
    def error(self,msg):
        print("ERROR [{}] {}".format(self.username,msg))
    def info(self,msg):
        print("INFO [{}] {}".format(self.username,msg))

    async def _login(self):
        return
        c = 0
        self.info("Logging in...")
        await self.client.get(queries.HOME)
        while not self.userId and c<5:
            async with self.client.post(queries.LOGIN,data={'username':self.username,'password':self.password,'queryParams':'"{"source":"auth_switcher"}"'}) as res:
                if res.status==200:
                    res = await res.json()
                    if res['authenticated']==True:
                        self.info("Account {} ({}) logged in successfully".format(self.username,res['userId']))
                        self.userid = res['userId']
                        self.excluded.append(self.username)
                    else:
                        self.warn("Authentication for {} failed".format(self.username))
                else:
                    self.error("Something went wrong with Instagram login")
                    print(res.status)
            c+=1
            await sleep(10,loop=self.client.loop)
        if c>=5:
            return self.error("Login for {} failed 5 times. Aborting...".format(self.username))

    async def _fetchStories(self):
        if self.userId:
            async with self.client.get(queries.FETCH_STORY_REEL) as res:
                if res.status==200:
                    self.users = []
                    res = await res.json()
                    data = res['data']['user']['feed_reels_tray']['edge_reels_tray_to_reel']['edges']
                    for i in data:
                        i = i['node']
                        if not i['user']['username'] in self.excluded:
                            self.users.append(User(i))
                    reel_ids = [i.id for i in self.users]
                    async with self.client.get(queries.FETCH_STORIES.format(dumps(reel_ids))) as res:
                        if res.status==200:
                            res = await res.json()
                            data = res['data']['reels_media']
                            for idx,val in enumerate(data):
                                for ii in val['items']:
                                    self.users[idx].stories.append(Story(ii))
                        elif res.status==403:
                            self.warn("There was an authentication error fetching stories")
                elif res.status==403:
                    self.warn("There was an authentication error fetching stories")

    async def _scrapeStories(self):
        if self.userId and len(self.users)>0:
            for i in self.users:
                if not path.exists(path.join(self.photo_dir,i.name)):
                    makedirs(path.join(self.photo_dir,i.name))
                count = 0
                for ii in i.stories:
                    p = path.join(self.photo_dir,i.name,ii.uploaded.strftime("%Y-%m-%d_%H-%M-%S"))+"."+ii.ext
                    if path.exists(p):
                        continue
                    count+=1
                    async with self.client.get(ii.link) as res:
                        if res.status==200:
                            async with aiofiles.open(p,mode="wb",loop=self.client.loop) as f:
                                await f.write(await res.read())
                                await f.close()
                                self.scraped.append(ii.id)
                                sleep(3)
                self.info("Saved {} story(s) by {}".format(count,i.name))

    async def start(self):
        self.info("Starting scraper...")
        await self._login()
        while self.userId:
            try:
                await self._fetchStories()
                await sleep(5,loop=self.client.loop)
                await self._scrapeStories()
            except Exception as e:
                self.error(str(e))
            await sleep(self.interval,loop=self.client.loop)


