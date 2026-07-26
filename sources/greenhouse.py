"""
Placeholder for a future source: company career pages hosted on
Greenhouse (boards.greenhouse.io/<company>) or Lever (jobs.lever.co/<company>).

Both platforms expose free public JSON APIs per-company, no key needed, e.g.:
  https://boards-api.greenhouse.io/v1/boards/<company>/jobs
  https://api.lever.co/v0/postings/<company>?mode=json

To activate: implement fetch() below returning the same normalized shape
used by the other sources ({"title", "company", "location", "link", "source"}),
then call it from main.py alongside adzuna.fetch() and reliefweb.fetch().
"""


def fetch(companies):
    """Not implemented yet. `companies` will be a list of company board slugs."""
    return []
