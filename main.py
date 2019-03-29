from InstaBear import StoryBear,PostBear
from json import load
import asyncio
import aiomysql
from uvloop import EventLoopPolicy

asyncio.set_event_loop_policy(EventLoopPolicy())

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
    if 'webserver_bind' in configs and configs['webserver_bind']:
        from WebClient.WebClient import WebClient
        webserver = [(await WebClient(pool,configs['webserver_bind']).init())]
    else:
        webserver = []
    storybears = [StoryBear.Bear(i,pool) for i in configs['accounts']]
    postbears = [PostBear.PostBear(i,pool) for i in storybears if not i.no_posts]
    return await asyncio.wait(webserver+[bear.start() for bear in storybears+postbears])

asyncio.get_event_loop().run_until_complete(main())
