import asyncio

from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright

import os

async def get_scrapybara_browser():
    client = Scrapybara(api_key=os.environ.get("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance

def requestMade(request):
    if request.url.startswith("https://www.doordash.com/graphql/itemPage?operation=itemPage"):
        print("Method: " + request.method)
        print("URL: " + request.url)
        return None
    return None

async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    :args:
    instance: the scrapybara instance to use
    url: the initial url to navigate to

    :desc:
    this function navigates to {url}. then, it will collect the detailed
    data for each menu item in the store and return it.

    (hint: click a menu item, open dev tools -> network tab -> filter for
            "https://www.doordash.com/graphql/itemPage?operation=itemPage")

    one way to do this is to scroll through the page and click on each menu
    item.

    determine the most efficient way to collect this data.

    :returns:
    a list of menu items on the page, represented as dictionaries
    """
    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()

        page.on("request", requestMade)

        await page.goto(start_url)

        await page.wait_for_load_state("networkidle")

        last_count = 0
        new_items = 0
        
        viewport_height = await page.evaluate("window.innerHeight")
        current_scroll = 0
        
        print("Starting to scroll and collect menu items...")
        
        while True:
            current_items = await page.locator('div[data-testid="MenuItem"]').all()
            current_count = len(current_items)
            
            print(f"Found {current_count} menu items so far")

            for item in current_items:
                text = await item.inner_text()
                print(text)
            
            if current_count == last_count:
                new_items += 1
                if new_items >= 3:
                    print("No more items")
                    break
            else:
                new_items = 0

            last_count = current_count
            
            current_scroll += viewport_height * 0.8
            await page.evaluate(f"window.scrollTo(0, {current_scroll})")
            await page.wait_for_timeout(1000)
        
        return []

        # browser automation ...


async def main():
    instance = await get_scrapybara_browser()

    try:
        await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
    finally:
        # Be sure to close the browser instance after you're done!
        instance.stop()


if __name__ == "__main__":
    asyncio.run(main())