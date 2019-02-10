from aiohttp import ClientSession,CookieJar
from time import ctime
from os import path,makedirs
import queries
import aiomysql
from json import dumps
from asyncio import sleep
from data_classes import User,Story
import traceback


class Bear:
    def __init__(self,config,db=None):
        self.username = config['username'] if 'username' in config else ""
        self.password = config['password'] if 'password' in config else ""
        self.userId = config['cookies']['ds_user_id']
        self.db_host = None
        if 'photo_dir' in config:
            if config['photo_dir'] != "__database__":
                if path.isdir(config['photo_dir']):
                    self.photo_dir = config['photo_dir']
                else:
                    self.error("Photo directory not specified or invalid")
                    self.userId = None
            else:
                if db:
                    self.db_host = db['host'] if 'host' in db else ""
                    self.db_user = db['user'] if 'user' in db else ""
                    self.db_pass = db['password'] if 'password' in db else ""
                    self.db_db = db['database'] if 'database' in db else ""
                    self.db_port = db['port'] if 'port' in db else 3306
                    self.photo_dir = None
                else:
                    self.error("Database not specified or invalid")
                    self.userId = None
        else:
            self.error("Photo directory not specified or invalid")
            self.userId = None
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
        self.db_connected = False

    def warn(self,msg):
        print("WARNING [{}] [{}] {}".format(ctime(),self.username,msg))
    def error(self,msg):
        print("ERROR [{}] [{}] {}".format(ctime(),self.username,msg))
    def info(self,msg):
        print("INFO [{}] [{}] {}".format(ctime(),self.username,msg))

    async def _connectdb(self):
        if self.db_host:
            self.info("Connecting to database")
            try:
                self.conn = await aiomysql.connect(host=self.db_host,user=self.db_user,password=self.db_pass,db=self.db_db,port=self.db_port,autocommit=True)
                self.db = await self.conn.cursor()
                self.db_connected = True
                self.info("Connected to database")
            except Exception as e:
                self.error(str(e))
                self.db_connected = False
    """
    async def _login(self):
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
    """
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
                    sleep(3)
                self.info("Saved {} story(s) by {}".format(count,i.name))

    async def _scrapeStoriesFs(self):
        if not self.photo_dir:
            return
        if self.userId and len(self.users)>0:
            for i in self.users:
                count = 0
                for ii in i.stories:
                    count+=await ii.save_to_fs(self,i)
                    sleep(3)
                self.info("Saved {} story(s) by {}".format(count,i.name))

    async def start(self):
        self.info("Starting scraper...")
        await self._connectdb()
        while self.userId:
            try:
                await self._fetchStories()
                await sleep(5,loop=self.client.loop)
                if self.db_connected:
                    await self._scrapeStoriesDb()
                else:
                    await self._scrapeStoriesFs()
            except Exception as e:
                self.error(str(e))
                print(traceback.format_exc())
            await sleep(self.interval,loop=self.client.loop)
