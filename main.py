from json import load,loads
import asyncio
import aiomysql
from aiomysql.cursors import DictCursor
#from InstaBear.queries import sql_queries
from uvloop import EventLoopPolicy
from Token import tokens_list
from os import getenv
#from BackupTool.Backuper import Backuper

asyncio.set_event_loop_policy(EventLoopPolicy())
pool = False

async def main():
    db_host = getenv('db_host')
    db_user = getenv('db_user')
    db_pass = getenv('db_pass')
    db_db = getenv('db_db')
    try:
        pool = await aiomysql.create_pool(host=db_host, user=db_user, password=db_pass, db=db_db, port=3306, autocommit=True)
        print("Connected to database at {}@{}".format(db_user, db_host))
    except Exception as e:
        print("Could not connect to database")
        print(str(e))
        exit(1)
    async with pool.acquire() as conn:
        db = await conn.cursor()
        #for i in sql_queries:
        #    await db.execute(i)
    if getenv('webserver'):
        from WebClient.WebClient import WebClient
        coros = [(await WebClient(pool, getenv('webserver')).init())]
    else:
        coros = []

    from Token import Token
#    backuper = Backuper("/home/marios/instabear_backups")
    async with pool.acquire() as conn:
        db = await conn.cursor(DictCursor)
        await db.execute("SELECT * FROM tokens")
        res = await db.fetchall()
        for i in res:
            tokens_list[i['token']] = Token(i, pool)
            if await tokens_list[i['token']].storybear.check_auth():
                coros.append(tokens_list[i['token']].storybear.start())
                coros.append(tokens_list[i['token']].postbear.start())
    await asyncio.gather(*coros)


asyncio.get_event_loop().run_until_complete(main())
