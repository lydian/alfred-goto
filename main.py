#!/usr/bin/env python
# encoding: utf-8
import time
import json
import os
import sys
import subprocess
import sqlite3
import shutil

from workflow import Workflow3

log = None


def get_all_tabs():
    return json.loads(
        subprocess.check_output(["./resources/chrome-control/chrome.js", "list"])
    )['items']


def maybe_copy_db():

    def cache_db(name):
        cache = wf.datafile(name)
        if os.path.isfile(cache) and time.time() - os.path.getmtime(cache) < 300:
            return cache
        shutil.copy(
            os.path.join(
                os.path.expanduser("~/Library/Application Support/Google/Chrome/Default"), name
            ),
            cache
        )
        return cache

    return cache_db('History'), cache_db('Favicons')


def get_history(search):
    history_db, favicon_db = maybe_copy_db()
    conn = sqlite3.connect(history_db)
    conn.cursor().execute('ATTACH DATABASE ? AS favicons', (favicon_db,)).close()
    query = """
        SELECT
            urls.title,
            urls.url,
            favicon_bitmaps.image_data,
            favicon_bitmaps.last_updated
        FROM urls
        LEFT JOIN icon_mapping ON icon_mapping.page_url = urls.url
        LEFT JOIN favicon_bitmaps ON favicon_bitmaps.id =(
            SELECT id
            FROM favicon_bitmaps
            WHERE favicon_bitmaps.icon_id = icon_mapping.icon_id
            ORDER BY width DESC LIMIT 1
        )
        WHERE urls.title like ? OR urls.url like ?
        ORDER BY visit_count DESC, last_visit_time DESC
    """
    search = '%{}%'.format(search)
    return [
        {
            "title": title,
            "url": url,
            "icon": image_data if image_data and image_last_updated else None
        }
        for (title, url, image_data, image_last_updated) in conn.execute(query, (search, search))
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
                valid=True
        )
    tab_urls = set(tab['url'] for tab in tabs)
    count = len(matched_tabs)
    for item in history:
        if item['url'] not in tab_urls:
            wf.add_item(
                title=item['title'],
                subtitle='[H]: {}'.format(item['url']),
                arg=item['url'],
                valid=True
            )
            count += 1
            if count >= 18:
                break

    wf.add_item(
        title='google {}'.format(query),
        subtitle="search on google",
        arg='https://www.google.com/search?q={}'.format(query),
        valid=True
    )
    wf.add_item(
        title='Duduckgo {}'.format(query),
        subtitle="search on Duckduckgo",
        arg='https://www.google.com/search?q={}'.format(query),
        valid=True
    )
    # Send output to Alfred
    wf.send_feedback()


if __name__ == '__main__':
    wf = Workflow3()
    # Assign Workflow logger to a global variable for convenience
    log = wf.logger
    sys.exit(wf.run(main))
