from asyncio import get_event_loop
from data_classes import Bear
from json import load
MAIN_LOOP = get_event_loop()

async def main():
    configs = load(open("config.json","r"))
    for i in configs['accounts']:
        await Bear(i).start()

get_event_loop().run_until_complete(main())
