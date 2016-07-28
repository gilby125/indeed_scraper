# indeed_scraper
An Indeed custom job search script.

This consists of two scripts: a scraper (indeed_scraper.py) and a web interface (indeed_api.py).

The scraper is intended to run on a regular basis via cron (once a day is enough). It populates a local MongoDB database with matching job posts from the Indeed API.

The web interface is used to browse through the scraped results.
