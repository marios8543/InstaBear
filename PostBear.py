from json import loads,dumps
from asyncio import sleep
from json import dumps
import traceback
import queries

class PBpost:
    def __init__(self,data,bear,uid):
        self.id = data['id']
        self.shortcode = data['shortcode']
        self.timestamp = data['taken_at_timestamp']
        self.caption = data['edge_media_to_caption']['edges'][0]['node']['text'] if len(data['edge_media_to_caption']['edges'])>0 else ""
        self.url = data['display_url']
        self.ext = "mp4" if data['is_video'] else "jpg"
        self.bear = bear
        self.user_id = uid

    async def check_exists(self):
        if self.id in self.bear.dld_posts:
            return 1
        res = await self.bear.db.execute("SELECT id FROM posts WHERE id=%s",self.id)
        if res:
            self.bear.dld_posts.append(self.id)
            return 1

    async def download(self):
        if not await self.check_exists():
            async with self.bear.client.get(self.url) as res:
                if res.status==200:
                    try:
                        media = await res.read()
                        await self.bear.db.execute("INSERT INTO posts(user_id,id,shortcode,caption,ext,timestamp,media) values(%s,%s,%s,%s,%s,%s,%s)"
                        ,(self.user_id,self.id,self.shortcode,self.caption,self.ext,self.timestamp,media,))
                        self.bear.dld_posts.append(self.id)
                        self.bear.info("Downloaded post {} by {}".format(self.id,self.user_id))
                        return 1
                    except Exception:
                        self.bear.error("Something went wrong with post {}".format(self.id))
                        return 0
                else:
                    self.bear.warn("Post fetch did not return 200")
                    return 0
        else:
            return 0

class PBuser:
    def __init__(self,data,bear):
        self.posts = []
        self.id = data['id']
        data = data['data']['user']['edge_owner_to_timeline_media']
        self.count = data['count']
        self.end_cursor = data['page_info']['end_cursor']
        self.bear = bear

    async def fetch_more(self):
        while len(self.posts) < self.count:
            async with self.bear.client.get(queries.POSTS.format(dumps({'id':self.id,'first':50,'after':self.end_cursor}))) as res:
                data = await res.json()
                data = data['data']['user']['edge_owner_to_timeline_media']
                self.end_cursor = data['page_info']['end_cursor']
                for i in data['edges']:
                    i = i['node']
                    if not next((post for post in self.posts if post.id == i['id']), None):
                        self.posts.append(PBpost(i,self.bear,self.id))
            await sleep(3)


class PostBear:
    def __init__(self,sbear,pool):
        self.client = sbear.client
        self.username = sbear.username
        self.users = []
        self.dld_posts = []
        self.pool = pool
        def warn(msg):
            return sbear.warn("[PostBear] {}".format(msg))
        def error(msg):
            return sbear.error("[PostBear] {}".format(msg))
        def info(msg):
            return sbear.info("[PostBear] {}".format(msg))
        self.warn = warn
        self.error = error
        self.info = info

    async def _connectdb(self):
        self.conn = await self.pool.acquire()
        self.db = await self.conn.cursor()

    async def _get_users(self):
        await self.db.execute("SELECT DISTINCT id FROM users WHERE scrape_posts=1 AND account=%s",(self.username,))
        res = await self.db.fetchall()
        if res:
            for i in res:
                exists = False
                try:
                    async with self.client.get(queries.POSTS.format(dumps({'id':i[0],'first':1}))) as r:
                        r = await r.json()
                        r['id'] = i[0]
                        if len(self.users)==0:
                            self.users.append(PBuser(r,self))
                            await self.users[-1].fetch_more()
                        else:
                            for idx,v in enumerate(self.users):
                                if v.id == i[0]:
                                    self.users[idx] = PBuser(r,self)
                                    await self.users[idx].fetch_more()
                                    exists = True
                                    break
                            if not exists:
                                self.users.append(PBuser(r,self))
                                await self.users[-1].fetch_more()
                    await sleep(2)
                except Exception:
                    self.error("Failed processing user {}".format(i[0]))
                    continue

    async def _save_posts(self):
        for i in self.users:
            count = 0
            for ii in i.posts:
                count+=(await ii.download())
                await sleep(1)
            if count>0:
                self.info("Saved {} posts by {}".format(count,i.id))
            await sleep(3)

    async def start(self):
        await self._connectdb()
        self.info("Starting postbear...")
        while True:
            try:
                await self._get_users()
                await self._save_posts()
            except Exception as e:
                self.error(str(e))
                print(traceback.format_exc())
            finally:
                await sleep(60)