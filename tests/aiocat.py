import asyncio
import requests
import random
ENDPOINT = "https://catfact.ninja/fact"

async def get_cat_fact():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: requests.get(ENDPOINT))
    return result.json().get('fact')

async def real_get_cat_fact_with_errors():
    await asyncio.sleep(random.random())
    if (random.random() > .3):
        return await get_cat_fact()
    else:
        raise Exception('API Error!')