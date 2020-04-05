from InstaBear import queries
from aiohttp import ClientSession
from json import loads,dumps
from asyncio import sleep
from pbot_orm import ORM
from logging import getLogger, StreamHandler, Formatter
from os import getenv
from sys import stdout
import traceback

class PBpost:
    def __init__(self,data,bear,uid,):
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
        res = await self.bear.db.select(table="posts", fields=["id"], params={"id":self.id})
        if res:
            self.bear.dld_posts.append(self.id)
            return 1

    async def download(self):
        if not await self.check_exists():
            async with self.bear.client.get(self.url) as res:
                if res.status==200:
                    try:
                        media = await res.read()
                        await self.bear.db.insert(table="posts", values={
                            "id":self.id,
                            "user_id":self.user_id,
                            "shortcode":self.shortcode,
                            "caption":self.caption,
                            "ext":self.ext,
                            "timestamp":self.timestamp,
                            "media":media
                        })
                        self.bear.dld_posts.append(self.id)
                        self.bear.log.debug("Downloaded post {} by {}".format(self.id,self.user_id))
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
                    if 'edge_sidecar_to_children' in i:
                        for ii in i['edge_sidecar_to_children']['edges']:
                            ii = ii['node']
                            i['id'] = ii['id']
                            i['display_url'] = ii['display_url']
                            i['is_video'] = ii['is_video']
                            if not next((post for post in self.posts if post.id == i['id']), None):
                                self.posts.append(PBpost(i,self.bear,self.id))
                    else:
                        if not next((post for post in self.posts if post.id == i['id']), None):
                            self.posts.append(PBpost(i, self.bear, self.id))
            await sleep(3)
        self.bear.log.debug("Holding {} posts".format(len(self.posts)))


class PostBear:
    def __init__(self,sbear,pool):
        self.client = sbear.client
        self.username = sbear.username
        self.users = []
        self.dld_posts = []
        self.pool = pool
        
        self.log = getLogger(str(self.username)+" PostBear")
        handler = StreamHandler(stdout)
        handler.setFormatter(Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
        self.log.addHandler(handler)
        self.log.setLevel(getenv('LOGLEVEL', 'INFO').upper())

    async def _connectdb(self):
        self.db = ORM(await self.pool.acquire())

    def update_creds(self,session_id,user_id):
        self.client = ClientSession(cookies={'sessionid':session_id,'ds_user_id':user_id})
        return

    async def _get_users(self):
        while True:
            try:
                async with self.db.conn.cursor() as db:
                    await db.execute("SELECT DISTINCT id FROM users WHERE scrape_posts=1 AND account=%s",(self.username,))
                    res = await db.fetchall()
                    break
            except RuntimeError:
                self.log.debug("ID fetch failed. Retrying...")
                await sleep(1)
                continue
        if res:
            for i in res:
                while True:
                    self.log.debug("Processing user {}".format(i))
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
                        break
                    except (KeyError, TypeError):
                        if r and "status" in r and r["status"] == "ok":
                            break
                        else:
                            self.log.warn("PostBear is getting rate-limited. Cooling down...")
                            await sleep(10)
                    except Exception as e:
                        self.log.error("Failed processing user {} ({})".format(i[0],str(e)))
                        traceback.print_exc()
                        break

    async def _save_posts(self):
        for i in self.users:
            count = 0
            for ii in i.posts:
                count += (await ii.download())
                await sleep(1)
            if count>0:
                self.log.info("Saved {} posts by {}".format(count,i.id))
            await sleep(3)

    async def start(self):
        await self._connectdb()
        self.log.info("Starting postbear...")
        while True:
            try:
                await self._get_users()
                await self._save_posts()
            except Exception as e:
                self.log.error(str(e))
                print(traceback.format_exc())
            finally:
                await sleep(60)