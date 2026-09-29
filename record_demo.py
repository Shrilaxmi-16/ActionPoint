import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def run():
    video_dir = "/tmp/playwright_video"
    os.makedirs(video_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        print("Navigating to ActionPoint on 8088...")
        await page.goto("http://127.0.0.1:8088", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Step 1: Ingesting transcript
        print("Clicking Load Sample Transcript...")
        await page.click("button:has-text('Load Sample Transcript')")
        await asyncio.sleep(2)
        
        print("Clicking Extract Action Items...")
        await page.click("#btn-extract")
        # Wait for extraction to switch to Review screen
        await page.wait_for_selector("#screen-review.active", timeout=20000)
        await asyncio.sleep(3)
        
        # Step 2: Review Screen
        print("Confirming and saving meeting...")
        await page.click("#btn-confirm")
        # Wait for table to switch to actions screen
        await page.wait_for_selector("#screen-actions.active", timeout=15000)
        await asyncio.sleep(3)
        
        # Step 3: Action Items Registry
        print("Viewing Action Items Table...")
        await page.mouse.wheel(0, 300)
        await asyncio.sleep(2)
        await page.mouse.wheel(0, -300)
        await asyncio.sleep(1)
        
        # Step 4: Communications & Agendas Screen with Project & Attendee Scoping
        print("Switching to Communications & Agendas...")
        await page.click("#tab-comms")
        await asyncio.sleep(2)
        
        # Select Project Horizon
        print("Selecting Project Horizon...")
        await page.select_option("#project-select", "Project Horizon")
        await asyncio.sleep(1.5)
        
        # Select individual: Dave
        print("Selecting Dave...")
        await page.select_option("#attendee-select", "Dave")
        await asyncio.sleep(1.5)
        
        print("Drafting Individual Email for Dave...")
        await page.click("button:has-text('Draft Email for Selected Person')")
        await asyncio.sleep(4)
        
        print("Generating Team Sync Agenda...")
        await page.click("button:has-text('Generate Team Sync Agenda')")
        await asyncio.sleep(4)
        
        # Step 5: Visual Dashboard
        print("Switching to Visual Dashboard...")
        await page.click("#tab-dashboard")
        await asyncio.sleep(3)
        await page.mouse.wheel(0, 200)
        await asyncio.sleep(2)
        await page.mouse.wheel(0, -200)
        await asyncio.sleep(1)
        
        # Step 6: Rich Interactive Prompt in Agent Chat Sidebar (Tool calls / DB lookups)
        print("Interacting with Co-Pilot Agent Chat...")
        chat_input = page.locator("#chat-input")
        await chat_input.fill("Show all high priority action items for Project Horizon and summarize Dave's blockers")
        await asyncio.sleep(1)
        await page.click("form#chat-form button[type='submit']")
        
        # Wait for agent co-pilot response
        print("Waiting for co-pilot response...")
        await asyncio.sleep(7)
        
        # Second rich prompt: query open questions / decisions
        await chat_input.fill("What were the confirmed architectural decisions and open technical questions?")
        await asyncio.sleep(1)
        await page.click("form#chat-form button[type='submit']")
        await asyncio.sleep(7)
        
        print("Demo flow completed successfully!")
        await context.close()
        await browser.close()

asyncio.run(run())
