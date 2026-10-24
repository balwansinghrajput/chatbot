import asyncio
from linkedin_scraper import BrowserManager
import os

async def create_session():
    print("="*60)
    print("LinkedIn Session Creator")
    print("="*60)
    print("\nThis script will open a Chromium browser.")
    print("Please log in manually. The script will wait until you are fully logged in,")
    print("and then save your session to 'linkedin_session.json'.")
    print("\nStarting browser...")
    
    async with BrowserManager(headless=False) as browser:
        print("Navigating to LinkedIn login page...")
        await browser.page.goto("https://www.linkedin.com/login")
        
        print("\n*** PLEASE LOG IN MANUALLY NOW ***")
        
        # Wait for the feed page to load (which means login is successful)
        try:
            await browser.page.wait_for_url("https://www.linkedin.com/feed/**", timeout=300000) # Wait up to 5 mins
            print("\nLogin detected! Saving session...")
            
            session_path = os.path.join(os.path.dirname(__file__), "linkedin_session.json")
            await browser.save_session(session_path)
            
            print(f"✅ Session successfully saved to {session_path}")
            print("You can now close the browser.")
        except Exception as e:
            print(f"\n❌ Login timed out or failed: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(create_session())
