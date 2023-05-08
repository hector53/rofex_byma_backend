#iterator

import asyncio

from aiocat import get_cat_fact

class CatFactIterator:
    # how many facts were produced
    count: int

    def __init__(self):
        # initialize
        self.count = 0

    def __aiter__(self):
        return self

    def __anext__(self):
        if self.count == 5:
            # stop after 5 facts
            raise StopAsyncIteration("Ran out of cat facts!")

        self.count += 1
        return get_cat_fact()

async def main():
    # create instance of iterator
    facts = CatFactIterator()
    # iterate asynchronously over iterator
    async for fact in facts:
        print(fact)

asyncio.run(main())