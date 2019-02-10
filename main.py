from Bear import Bear
from json import load
import asyncio

async def main():
    configs = load(open("config.json","r"))
    db_config = configs['database'] if 'database' in configs else None
    await asyncio.wait([Bear(i,db_config).start() for i in configs['accounts']])

asyncio.get_event_loop().run_until_complete(main())