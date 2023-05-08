#aqui igual ejecuto en paralelo la cantidad de veces que venga del input 
import asyncio

from aiocat import get_cat_fact

async def main():
    n = int(input('How many cat facts would you like? '))
    requests = [get_cat_fact() for i in range(n)]
    facts = await asyncio.gather(*requests)
    print(*facts, sep='\\n\\n')

asyncio.run(main())