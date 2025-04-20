from fastapi import FastAPI, Request, Body
import uvicorn
from crawler.crawler import Crawler
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/crawl")
async def crawl_api(payload: dict = Body(...)):
    max_urls = payload.get("max_urls_per_domain", None)

    logger.info("Crawl request received")
    crawler = Crawler(config_path="config.yaml", max_urls_per_domain=max_urls)

    await crawler.run()

    logger.info("Crawl completed")
    return {"status": "completed", "message": f"Crawling done. Max URLs per domain: {max_urls or 'unlimited'}"}


@app.get("/results")
def get_results():
    try:
        with open("output/product_url.json") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading results: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)