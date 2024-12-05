import asyncio
import json
from aiohttp import ClientSession
from .proxy_maintainer import ProxyMaintainer


class OzonParser:
    BASE_URL = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/"
    proxy_maintainer = ProxyMaintainer("proxylist.txt")

    @staticmethod
    def get_slug_from_url(url: str):
        if(url.find("https://www.ozon.ru/") == -1):
            raise Exception("Not an OZON url")
        url = url.replace("https://www.ozon.ru/", "")
        if(url.find("category/") == -1):
            raise Exception("Not a category")
        url = url.replace("category/", "")
        
        url = url[:url.find("/")]
    
        return url

    @classmethod
    async def get_sellers_from_category(cls, session: ClientSession, category_url):
        sellers_info = []
        
        async for slug, name in cls.get_products_slugs_and_names_from_category(
            session, category_url, amount_pages=10
        ):
            sellers_info.append(
                cls.get_seller_info_from_product_slug(session, slug, name)
            )

        sellers_info = list({d.get('Информация'): d for d in (await asyncio.gather(*sellers_info)) if d}.values())
        return sellers_info

    @classmethod
    async def get_seller_info_from_product_slug(
        cls, session, product_slug, product_name
    ):
        ans = {}
        url = (
            cls.BASE_URL
            + f"product/{product_slug}/?layout_container=pdpPage2column&layout_page_index=2"
        )
        response = await cls.proxy_maintainer.async_get_url(
            url=url,
            session=session,
        )
        
        content = await response.text()
        if response.status != 200:
            print(f"Server returned error: {response.status} while parsing product: {product_slug}")
            raise Exception("OZON server returned error")

        try:
            json_content = json.loads(content)
        except Exception as e:
            json_content = {}
            print("Error while getting content", e)

        product_info_raw = json_content.get("widgetStates", {})

        for key in product_info_raw.keys():
            if key.startswith("webCurrentSeller"):
                seller_info = json.loads(product_info_raw[key])

                ans.update(
                    {
                        "Наименование": product_name,
                    }
                )
                ans.update(cls.get_seller_creds_dict(seller_info.get("credentials")))
                ans.update(
                    {
                        "Товар": f"https://www.ozon.ru/product/{product_slug}/",
                        "Продавец": seller_info.get("link"),
                    }
                )

                if not ans["ОГРН"]:
                    return {}
                return ans

    @staticmethod
    def get_seller_creds_dict(raw_creds):
        creds = {}
        try:
            creds["Информация"] = raw_creds[0]
        except Exception:
            creds["Информация"] = ""

        try:
            for i in range(1, 5):
                if all([c.isdigit() for c in raw_creds[i]]):
                    creds["ОГРН"] = raw_creds[i]
                    break
        except Exception:
            creds["ОГРН"] = ""

        try:
            creds["Работает с озон"] = raw_creds[4]
        except Exception:
            creds["Работает с озон"] = ""
        return creds

    @classmethod
    async def get_products_slugs_and_names_from_category(
        cls, session, category_url, amount_pages=None
    ):
        page = 1
        while True:
            url = (
                cls.BASE_URL
                + "category/"
                + cls.get_slug_from_url(category_url)
                + f"/?layout_container=categorySearchMegapagination&layout_page_index={page}&page={page}"
            )
            response = await cls.proxy_maintainer.async_get_url(
                url=url,
                session=session,
            )
            content = await response.text()
            if response.status != 200:
                print(f"Server returned error: {response.status}")
                raise Exception("OZON server returned error")

            widgets = json.loads(content).get("widgetStates", {})
            positions = {}

            for key in widgets.keys():
                if key.startswith("searchResultsV2"):
                    positions = json.loads(widgets[key])
                    break

            items = positions.get("items", [])

            print(
                f"Api page {page} parsing gave: {[item.get('skuId') for item in items]}"
            )

            if items:
                for item in items:
                    ans = []
                    action = item.get("action")
                    link = action.get("link")
                    sku = item.get("skuId")
                    for link_element in link.split("/"):
                        if sku in link_element:
                            ans.append(link_element)
                            break

                    main_state = item.get("mainState")
                    for atom in main_state:
                        if atom.get("id") == "name":
                            ans.append(
                                atom.get("atom", {}).get("textAtom", {}).get("text")
                            )
                    yield ans

                page += 1
                if amount_pages and page > amount_pages:
                    break
            else:
                break
