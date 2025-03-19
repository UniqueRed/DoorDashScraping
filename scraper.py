import asyncio

from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright

import os

menu_items = {}

async def get_scrapybara_browser():
    client = Scrapybara(api_key=os.environ.get("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance

async def handle_response(response):
    if response.url.startswith("https://www.doordash.com/graphql/itemPage?operation=itemPage"):
        body = await response.json()
        item_page = body.get("data", {}).get("itemPage", {})
        item_header = item_page.get("itemHeader", {})
        name = item_header.get("name")
        description = item_header.get("description", "No description")
        unit_amount = item_header.get("unitAmount", 0) / 100

        optionLists = item_page.get("optionLists", [])

        formatted_options = [
            {"name": option["name"], "unitAmount": option["unitAmount"] / 100}
            for optionList in optionLists if "options" in optionList
            for option in optionList["options"]
        ]

        print(name)
        menu_items[name] = {
            "description": description,
            "price": unit_amount,
            "options": formatted_options
        }
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
    seenItems = set()

    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()

        page.on("response", handle_response)

        await page.goto(start_url)

        await page.wait_for_load_state("networkidle")
        
        viewport_height = await page.evaluate("window.innerHeight")
        current_scroll = 0
        
        print("Start scrolling")
        
        while True:
            current_items = await page.locator('div[data-testid="MenuItem"]').all()
            current_count = len(current_items)
            
            print(f"Found {current_count} menu items")
            print("-------------------------------")

            for item in current_items:
                try:
                    id = await item.get_attribute("data-item-id", timeout=5000)
                except Exception:
                    print("ID not found")

                if id and id not in seenItems:
                    seenItems.add(id)

                    await item.click()
                    print("CLICKED ITEM")

                    await page.wait_for_load_state("load", timeout=5000)

                    print("REQUESTED")

                    await page.locator('button[aria-label="Close"]').first.click(timeout=3000)
                    print("CLOSED")
                else:
                    print("SKIPPING, ALREADY SEEN")

                await page.wait_for_timeout(1000)
                print("-------------------------------")
            
            current_scroll += viewport_height * 0.8
            await page.evaluate(f"window.scrollTo(0, {current_scroll})")
            await page.wait_for_timeout(1000)

            is_at_bottom = await page.evaluate("window.innerHeight + window.scrollY >= document.body.scrollHeight")

            if is_at_bottom:
                print("Reached the bottom")
                break
        
        return menu_items

        # browser automation ...


async def main():
    instance = await get_scrapybara_browser()

    try:
        menu = await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )

        for item_name, details in menu.items():
            price_display = f" (${details['price']:.2f})" if details["price"] > 0 else ""
            print(f"\n{item_name} - {details['description']}{price_display}\n{'-' * 50}")

            if details["options"]:
                print("Options:")
                for option in details["options"]:
                    option_price_display = f" (${option['unitAmount']:.2f})" if option["unitAmount"] > 0 else ""
                    print(f"  - {option['name']}{option_price_display}")
            else:
                print("No options available.")

            print("=" * 50)

    finally:
        # Be sure to close the browser instance after you're done!
        instance.stop()


if __name__ == "__main__":
    asyncio.run(main())