#aqui ejecuto cada llamada de api en un hilo diferente pero igual se ejecutan uno tras otro

import asyncio
import time

from aiocat import get_cat_fact

async def main():
    for i in range(5):
        print(f'Cat fact #{i + 1}')
        print(await get_cat_fact())

start = time.perf_counter()
asyncio.run(main())
print(f'Completed in {time.perf_counter() - start} seconds')