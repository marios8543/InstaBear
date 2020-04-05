from aiohttp import ClientSession
from InstaBear import queries
from json import dumps
from asyncio import sleep
from InstaBear.data_classes import User,Story
from pbot_orm import ORM
from logging import getLogger, StreamHandler, Formatter
from traceback import print_exc
from sys import stdout
from os import getenv

class Bear:
    def __init__(self,config,pool):
        self.pool = pool
        self.username = config['username'] if 'username' in config else ""
        self.excluded = config['excluded'] if 'excluded' in config and type(config['excluded']) is list else []
        try:
            self.interval = int(config['interval'])
        except Exception:
            self.interval = 300
        self.client = ClientSession(cookies=config['cookies'])
        self.users = []
        self.log = getLogger(str(self.username))
        handler = StreamHandler(stdout)
        handler.setFormatter(Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
        self.log.addHandler(handler)
        self.log.setLevel(getenv('LOGLEVEL', 'INFO').upper())

    async def _connectdb(self):
        self.db = ORM(await self.pool.acquire())

    async def _fetchStories(self):
        async with self.client.get(queries.FETCH_STORY_REEL) as res:
            if res.status==200:
                self.users = []
                res = await res.json()
                data = res['data']['user']['feed_reels_tray']['edge_reels_tray_to_reel']['edges']
                for i in data:
                    i = i['node']
                    if not i['user']['username'] in self.excluded:
                        self.users.append(User(i))
                self.log.debug("Keeping {} users".format(len(self.users)))
                reel_ids = [i.id for i in self.users]
                async with self.client.get(queries.FETCH_STORIES.format(dumps(reel_ids))) as res:
                    if res.status==200:
                        res = await res.json()
                        data = res['data']['reels_media']
                        self.log.debug("Processing {} stories".format(len(data)))
                        for idx,val in enumerate(data):
                            for ii in val['items']:
                                self.users[idx].stories.append(Story(ii))
                    elif res.status==403:
                        self.log.warn("There was an authentication self.log.error fetching stories")
            elif res.status==403:
                self.log.warn("There was an authentication self.log.error fetching stories")

    async def _scrapeStoriesDb(self):
        self.log.debug("Holding {} users".format(len(self.users)))
        if len(self.users)>0:
            for i in self.users:
                await i.save_to_db(self)
                count = 0
                for ii in i.stories:
                    c = await ii.save_to_db(self, i)
                    count += c
                    if c:
                        self.log.debug("Saved {}".format(ii.id))
                    await sleep(0.1)
                if count>0:
                    self.log.info("Saved {} story(s) by {}".format(count,i.name))

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
        self.log.info("Starting storybear...")
        await self._connectdb()
        while True:
            try:
                self.log.debug("Fetching stories")
                await self._fetchStories()
                self.log.debug("Waiting for a second")
                await sleep(1)
                self.log.debug("Downloading stories")
                await self._scrapeStoriesDb()
            except Exception as e:
                self.log.error(str(e))
                print_exc()
            finally:
                self.log.debug("Sleeping for {}s".format(self.interval))
                await sleep(self.interval)