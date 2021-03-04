#!/usr/bin/env python
# encoding: utf-8
import time
import json
import os
import sys
import subprocess
import sqlite3
import shutil
from urlparse import urlparse

from workflow import Workflow3

__version__ = '1.0.1'
log = None


def get_all_tabs():
    return json.loads(
        subprocess.check_output(["./resources/chrome-control/chrome.js", "list"])
    )['items']


def cache_db():
    history = 'History'
    cache = wf.datafile(history)
    if os.path.isfile(cache) and time.time() - os.path.getmtime(cache) < 300:
        return cache
    shutil.copy(
        os.path.join(
            os.path.expanduser("~/Library/Application Support/Google/Chrome/Default"),
            history
        ),
        cache
    )
    return cache


def get_history(search):
    conn = sqlite3.connect(cache_db())
    search_terms = search.strip().split(' ')
    filters = ' AND '.join(
        ['(urls.title like ? OR urls.url like ?)'] * len(search_terms)
    )
    query = """
        SELECT
            urls.title,
            urls.url
        FROM urls
        WHERE {}
        ORDER BY visit_count DESC, last_visit_time DESC
    """.format(filters)
    search_args = [
        t
        for term in search_terms
        for t in ['%{}%'.format(term)] * 2
    ]
    return [
        {
            "title": title,
            "url": url,
        }
        for idx, (title, url) in enumerate(conn.execute(query, search_args))
        # ignore google or duckduckgo history
        if (
            all(seg not in ('google', 'duckduckgo') for seg in urlparse(url).netloc.split('.'))
            and urlparse(url).scheme in ('http', 'https')
        )
    ]


def main(wf):
    # The Workflow instance will be passed to the function
    # you call from `Workflow.run`

    # Your imports here if you want to catch import errors
    # Get args from Workflow as normalized Unicode
    query = wf.args[0]
    tabs = wf.cached_data('tabs', get_all_tabs, max_age=60)
    history = get_history(query)

    matched_tabs = wf.filter(query, tabs, key=lambda t: t['title'] + ' ' + t['url'])
    for item in matched_tabs:
        wf.add_item(
                title=item['title'],
                subtitle='[T]: {}'.format(item['url']),
                arg='focus {}'.format(item['arg']),
                valid=True,
                icon='./resources/icons/open-in-browser-32.png'
        )
    tab_urls = set(tab['url'] for tab in tabs)
    count = len(matched_tabs)
    for item in history:
        if item['url'] not in tab_urls:
            wf.add_item(
                title=item['title'],
                subtitle='[H]: {}'.format(item['url']),
                arg=item['url'],
                valid=True,
                icon='./resources/icons/watch-32.png'
            )
            count += 1
            if count >= 18:
                break

    wf.add_item(
        title='Google Search: {}'.format(query),
        subtitle="search on google",
        arg='https://www.google.com/search?q={}'.format(query),
        valid=True,
        icon='./resources/icons/google.png'
    )
    wf.add_item(
        title='Duduckgo Search: {}'.format(query),
        subtitle="search on Duckduckgo",
        arg='https://www.google.com/search?q={}'.format(query),
        valid=True,
        icon='./resources/icons/duckduckgo.png'
    )
    # Send output to Alfred
    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow3(
        update_settings={
            'github_slug': 'lydian/alfred-goto',
            'version': __version__,

        }
    )
    # Assign Workflow logger to a global variable for convenience
    log = wf.logger
    sys.exit(wf.run(main))
