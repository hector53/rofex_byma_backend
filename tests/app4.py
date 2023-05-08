#aqui las voy a ejecutar en paralelo , todas a la vez 
import asyncio
import time

from aiocat import get_cat_fact

async def main():
    facts = await asyncio.gather(
        get_cat_fact(),
        get_cat_fact(),
        get_cat_fact(),
        get_cat_fact(),
        get_cat_fact()
    )
    print(*facts, sep='\\n')

start = time.perf_counter()
asyncio.run(main())
print(f'Completed in {time.perf_counter() - start}s')