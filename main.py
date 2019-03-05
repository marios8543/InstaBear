from StoryBear import Bear
from PostBear import PostBear
from json import load
import asyncio
import aiomysql

async def main():
    configs = load(open("config.json","r"))
    db = configs['database'] if 'database' in configs else None
    db_host = db['host'] if 'host' in db else ""
    db_user = db['user'] if 'user' in db else ""
    db_pass = db['password'] if 'password' in db else ""
    db_db = db['database'] if 'database' in db else ""
    try:
        pool = await aiomysql.create_pool(host=db_host,user=db_user,password=db_pass,db=db_db,port=3306,autocommit=True)
        print("Connected to database at {}@{}".format(db_user,db_host))
    except Exception as e:
        print("Could not connect to database")
        print(str(e))
        exit(1)
    storybears = [Bear(i,pool) for i in configs['accounts']]
    postbears = [PostBear(i,pool) for i in storybears]
    await asyncio.wait([bear.start() for bear in storybears+postbears])

asyncio.get_event_loop().run_until_complete(main())