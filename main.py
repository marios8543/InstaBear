from json import load
import asyncio
import aiomysql
from aiomysql.cursors import DictCursor
from InstaBear.queries import sql_queries
from uvloop import EventLoopPolicy
from Token import tokens_list
import queries

asyncio.set_event_loop_policy(EventLoopPolicy())
pool = False

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
    async with pool.acquire() as conn:
        db = await conn.cursor()
        for i in queries.sql_queries:
            await db.execute(i)
    if 'webserver_binds' in configs and len(configs['webserver_binds'])>0:
        from WebClient.WebClient import WebClient
        coros = [(await WebClient(pool,i).init()) for i in configs['webserver_binds']]
    else:
        coros = []
    
    from Token import Token
    async with pool.acquire() as conn:
        db = await conn.cursor(DictCursor)
        await db.execute("SELECT * FROM tokens")
        res = await db.fetchall()
        for i in res:
            tokens_list[i['token']] = Token(i,pool)
            if await tokens_list[i['token']].storybear.check_auth():
                coros.append(tokens_list[i['token']].storybear.start())
                coros.append(tokens_list[i['token']].postbear.start())
    await asyncio.gather(*coros)


asyncio.get_event_loop().run_until_complete(main())
