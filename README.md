#  ASYNCRAWLER: Product Crawler

A scalable, intelligent product URL crawler for e-commerce websites.  
Supports static and JavaScript-rendered content, with smart pattern learning.

---

##  Features

-  Async crawling using `aiohttp`
-  JavaScript rendering via Playwright (`chromium`, `firefox`)
-  Learns product URL patterns automatically
-  Configurable via API and `config.yaml`
-  Outputs clean `product_url.json` for each domain

---

##  Project Structure

```
.
├── main.py                    # FastAPI API server
├── config.yaml                # Domain + crawler config
├── output/product_url.json    # Final crawl results
├── requirements.txt           # Dependencies
├── crawler/
│   ├── crawler.py             # Crawler logic
│   └── pattern_generator.py   # Pattern learning logic
```

---

##  Setup

```bash
pip install -r requirements.txt
playwright install
playwright install chromium
playwright install firefox

```

Then start the API:

```bash
uvicorn main:app --reload
```

---

##  API Usage

### `POST /crawl`

**Trigger a crawl** via API with optional limit:

```json
{
  "max_urls_per_domain": 100
}
```

---

## Config Example (`config.yaml`)

```yaml
domains:
  - https://www.tatacliq.com/
  - https://www.nykaafashion.com/

max_depth: 5
concurrency: 50
use_playwright: true
render_timeout: 30000
playwright_domains:
  - tatacliq.com
  - nykaafashion.com
playwright_max_depth: 2
product_url_patterns:
  - "/product/"
  - "/p/"
  - "/item/"
  - "/shop/"
  - "/men"
  - "/women"
  - "/brands"
  - "/sale"
```

---

##  Output

A file at `output/product_url.json`:

```json
{
  "https://www.tatacliq.com/": [
    "https://www.tatacliq.com/mens-clothing/c-msh11",
    "https://www.tatacliq.com/womens-clothing/c-msh10"
  ]
}
```

---

##  Pattern Learning

After the first crawl pass:
- The crawler learns generalized URL structures
- Applies them in the second pass to extract deeper product pages

---

##  Future Improvements

- [ ] `/results` endpoint
- [ ] Docker support
- [ ] Scheduled crawling
- [ ] URL deduplication cache