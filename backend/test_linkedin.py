import asyncio
import sys
from services.linkedin_finder import find_linkedin_profile

async def test():
    print("Testing find_linkedin_profile for Sam Altman...")
    res = await find_linkedin_profile("Sam Altman")
    print(res)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test())
