from base64 import b64encode
from aiofiles import open as aopen
from os import getenv, path

try:
    STORIES_PER_FILE = int(getenv("stories_per_file"))
except Exception:
    STORIES_PER_FILE = 1000

class ArchiveFullException(Exception):
    pass

class InvalidArchiveException(Exception):
    pass

class Archive:
    keys = ['id','timestamp','user_id','ext','media']

    def __init__(self, path):
        self.path = path
        self.count = 0

    async def init(self):
        if self.path.split(".")[-1]=="instabearbackup" and self.path.split(".")[0].isnumeric():
            if not path.isfile(self.path):
                async with aopen(self.path,'w+') as f:
                    await f.write(",".join(self.keys))
            else:
                async with aopen(self.path,'r') as f:
                    csv_keys = [i.strip() for i in f.readline().split(",")]
                    for i in csv_keys:
                        if i not in self.keys:
                            raise InvalidArchiveException
                    for i in self.keys:
                        if i not in csv_keys:
                            raise InvalidArchiveException
                    self.count = sum(1 for i in f)
            self.file = await aopen(self.path,'a')
        else:
            raise InvalidArchiveException

    async def add_story(self, story):
        if self.count >= STORIES_PER_FILE:
            raise ArchiveFullException(int(self.path.split(".")[0])+1)
        id = story['id']
        timestamp = story['uploaded']
        user_id = story['user_id']
        ext = story['ext']
        media = b64encode(story['media'])
        await self.file.write("{},{},{},{},{}".format(id,timestamp,user_id,ext,media))


    def __del__(self):
        self.file.close()
