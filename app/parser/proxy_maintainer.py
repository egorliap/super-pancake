import asyncio
import random

from aiohttp import ClientSession

VALID_STATUSES = [200, 301, 302, 307, 404]


class ProxyMaintainer:
    def __init__(self, proxy_file_path):
        self.proxy_file_path = proxy_file_path
        self.proxies_list = self.get_proxies_from_file(proxy_file_path)

        self.unchecked = set(self.proxies_list)
        self.working = set()
        self.not_working = set()

    @staticmethod
    def get_proxies_from_file(proxy_file_path):
        try:
            raw_addresses = open(proxy_file_path, "r").read().strip().split("\n")
        except FileNotFoundError:
            raise FileNotFoundError("No proxies found")
        proxy_list = []
        for addr in raw_addresses:
            proxy = ""
            # user:pass@some.proxy.com
            splitted_addr = addr.split(":")
            if not splitted_addr[0]:
                continue
            if splitted_addr:
                proxy = splitted_addr[0] + ":" + splitted_addr[1]
            if len(splitted_addr) >= 4:
                proxy = splitted_addr[2] + ":" + splitted_addr[3] + "@" + proxy
            proxy_list.append(proxy)
        return proxy_list

    def get_random_proxy(self):
        available_proxies = tuple(self.unchecked.union(self.working))
        if not available_proxies:
            raise Exception("No proxies available!")
        return random.choice(available_proxies)

    def reset_proxy(self, proxy):
        self.unchecked.add(proxy)
        self.working.discard(proxy)
        self.not_working.discard(proxy)

    def set_working(self, proxy):
        self.unchecked.discard(proxy)
        self.working.add(proxy)
        self.not_working.discard(proxy)

    def set_not_working(self, proxy):
        self.unchecked.discard(proxy)
        self.working.discard(proxy)
        self.not_working.add(proxy)

    async def async_get_url(self, url, session: ClientSession, proxy=None):
        if not proxy:
            proxy = self.get_random_proxy()
        retries = 1

        while True:
            try:
                proxy_url = f"http://{proxy}"
                response = await session.get(url, proxy=proxy_url)
                if response.status in VALID_STATUSES:
                        self.set_working(proxy)
                else:
                        self.set_not_working(proxy)
                        raise Exception(f"Status {response.status}")

                return response
            except Exception as e:
                self.set_not_working(proxy)
                print("Session exception:", e)
                try:
                    proxy = self.get_random_proxy()
                except Exception as e:
                    print(e)

                    self.proxies_list = self.get_proxies_from_file(self.proxy_file_path)
                    self.unchecked = set(self.proxies_list)
                    self.working = set()
                    self.not_working = set()
                    
                    proxy = self.get_random_proxy()
                    
                    print(f"sleep for {retries/2} minute(s)")
                    retries += 1
                    if retries == 4:
                        raise Exception("Need to update proxies")
                    await asyncio.sleep(retries / 2 * 60)
