import asyncio
import re
import json
import yaml
import logging
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from crawler.pattern_generator import suggest_patterns
from playwright.async_api import async_playwright
import aiohttp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ASSET_EXTENSIONS = re.compile(r'\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ttf|ico)(\?.*)?$')
INTERESTING_PATH_PARTS = re.compile(
    r'(product|products|c-|p-|item|shop|men|women|kids|beauty|clothing|accessories|footwear|bags|brands|makeup|jewellery|home|kitchen|electronics|watches|sportswear|sale|offers|deals|category)',
    re.IGNORECASE
)

class Crawler:
    def __init__(self, config_path, max_urls_per_domain=None):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.config = config
        self.domains = config['domains']
        self.max_depth = config.get('max_depth', 5)
        self.concurrency = config.get('concurrency', 50)
        self.patterns = [re.compile(pat) for pat in config['product_url_patterns']]
        self.use_playwright = config.get('use_playwright', True)
        self.timeout = config.get('render_timeout', 30000)
        self.proxy = config.get('proxy')
        self.playwright_domains = config.get("playwright_domains", [])
        self.playwright_max_depth = config.get("playwright_max_depth", 2)
        self.max_urls_per_domain = max_urls_per_domain or float("inf")

        self.results = defaultdict(set)
        self.seen = defaultdict(set)
        self.all_urls = defaultdict(set)

    async def fetch_playwright(self, url, engine='chromium'):
        try:
            logger.info(f"Rendering URL with Playwright: {url}")
            async with async_playwright() as p:
                browser_args = ["--no-sandbox", "--disable-http2"]
                launch_options = {
                    "headless": True,
                    "args": browser_args
                }
                if self.proxy:
                    launch_options["proxy"] = {"server": self.proxy}
                browser_launcher = getattr(p, engine)
                browser = await browser_launcher.launch(**launch_options)
                page = await browser.new_page()
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document"
                })
                await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                content = await page.content()
                await browser.close()
                return content
        except Exception as e:
            logger.error(f"Playwright fetch error for {url}: {e}")
        return ''

    async def fetch_aiohttp(self, session, url):
        for attempt in range(2):
            try:
                logger.info(f"Fetching URL with aiohttp: {url}")
                async with session.get(url, timeout=10) as response:
                    if response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                        return await response.text()
            except Exception as e:
                logger.warning(f"aiohttp fetch attempt {attempt + 1} failed for {url}: {e}")
                await asyncio.sleep(1)
        return ''

    async def fetch(self, session, url, depth=0):
        parsed_domain = urlparse(url).netloc
        use_browser = (
            self.use_playwright and
            any(domain in parsed_domain for domain in self.playwright_domains) and
            depth <= self.playwright_max_depth
        )
        if use_browser:
            engine = 'firefox' if 'nykaafashion.com' in parsed_domain else 'chromium'
            return await self.fetch_playwright(url, engine=engine)
        return await self.fetch_aiohttp(session, url)

    def extract_links(self, base_url, html):
        links = set(re.findall(r'href=["\'](.*?)["\']', html))
        for link in links:
            logger.debug(f"Found link on page: {link}")
        return links

    def is_product_url(self, url):
        return any(p.search(url) for p in self.patterns)

    async def crawl_worker(self, session, domain, queue, use_patterns):
        while not queue.empty():
            url, depth = await queue.get()
            if depth > self.max_depth:
                continue
            if len(self.seen[domain]) >= self.max_urls_per_domain:
                continue

            html = await self.fetch(session, url, depth)
            if not html:
                continue

            for link in self.extract_links(url, html):
                full_url = urljoin(url, link)
                parsed = urlparse(full_url)
                if parsed.netloc != urlparse(domain).netloc:
                    continue
                full_url = parsed.scheme + "://" + parsed.netloc + parsed.path
                if full_url in self.seen[domain]:
                    continue
                if ASSET_EXTENSIONS.search(full_url):
                    continue
                if not INTERESTING_PATH_PARTS.search(full_url):
                    continue
                if len(self.seen[domain]) >= self.max_urls_per_domain:
                    break
                self.seen[domain].add(full_url)
                self.all_urls[domain].add(full_url)
                if use_patterns and self.is_product_url(full_url):
                    logger.info(f"Product URL found: {full_url}")
                    self.results[domain].add(full_url)
                await queue.put((full_url, depth + 1))

    async def crawl_domain(self, domain, use_patterns=True):
        logger.info(f"Starting crawl for domain: {domain}")
        queue = asyncio.Queue()
        await queue.put((domain, 0))
        self.seen[domain].add(domain)

        async with aiohttp.ClientSession() as session:
            workers = [asyncio.create_task(self.crawl_worker(session, domain, queue, use_patterns))
                       for _ in range(self.concurrency)]
            await asyncio.gather(*workers)

    async def run(self):
        await asyncio.gather(*(self.crawl_domain(domain, use_patterns=False) for domain in self.domains))

        pattern_map = suggest_patterns(self.all_urls)
        new_patterns = list({p for p in pattern_map.values() if p})
        self.patterns = [re.compile(pat.replace('*', '[^/]+')) for pat in new_patterns]
        logger.info(f"Discovered new patterns: {new_patterns}")

        self.results = defaultdict(set)
        self.seen = defaultdict(set)

        await asyncio.gather(*(self.crawl_domain(domain, use_patterns=True) for domain in self.domains))

        with open("output/product_url.json", "w") as f:
            json.dump({k: sorted(list(v)) for k, v in self.results.items()}, f, indent=2)
        logger.info("Final crawling completed. Results saved to output/product_url.json")
