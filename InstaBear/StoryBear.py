from aiohttp import ClientSession
from time import ctime
from os import path,makedirs
from InstaBear import queries
from json import dumps
from asyncio import sleep
from InstaBear.data_classes import User,Story
import traceback
from InstaBear.PostBear import PostBear


class Bear:
    def __init__(self,config,pool):
        self.running = False
        self.pool = pool
        self.username = config['username'] if 'username' in config else ""
        self.password = config['password'] if 'password' in config else ""
        self.userId = True
        self.excluded = config['excluded'] if 'excluded' in config and type(config['excluded']) is list else []
        if 'interval' in config:
            try:
                self.interval = int(config['interval'])
            except Exception:
                self.interval = 300
        else:
            self.interval = 300
        self.client = ClientSession(cookies=config['cookies'])
        self.users = []
        self.no_posts = config['no_posts'] if 'no_posts' in config and type(config['no_posts'])==bool else False
    def warn(self,msg):
        print("\033[1;33;40m WARNING [{}] [{}] {} \033[0m".format(ctime(),self.username,msg))
    def error(self,msg):
        print("\033[1;31;40m ERROR [{}] [{}] {} \033[0m".format(ctime(),self.username,msg))
    def info(self,msg):
        print("INFO [{}] [{}] {} \033[0m".format(ctime(),self.username,msg))

    async def _connectdb(self):
        self.conn = await self.pool.acquire()
        self.db = await self.conn.cursor()

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

    async def _scrapeStoriesDb(self):
        if self.userId and len(self.users)>0:
            for i in self.users:
                await i.save_to_db(self)
                count = 0
                for ii in i.stories:
                    count+=await ii.save_to_db(self,i)
                    await sleep(3)
                if count>0:
                    self.info("Saved {} story(s) by {}".format(count,i.name))

    async def check_auth(self):
        res = await self.client.get("https://www.instagram.com/graphql/query/?query_hash=7c16654f22c819fb63d1183034a5162f")
        if res.status==200:
            jar = self.client.cookie_jar
            for i in jar:
                if i.key=="ds_user_id":
                    return i.value

    def update_creds(self,session_id,user_id):
        self.client = ClientSession(cookies={'sessionid':session_id,'ds_user_id':user_id})
        return

    async def start(self):
        self.running = True
        self.info("Starting storybear...")
        await self._connectdb()
        while self.userId and self.running:
            try:
                await self._fetchStories()
                await sleep(5)
                await self._scrapeStoriesDb()
            except Exception as e:
                self.error(str(e))
                #print(traceback.format_exc())
            finally:
                await sleep(self.interval)

    def stop(self):
        self.running = False
