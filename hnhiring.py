#!/usr/bin/env python3
# coding: utf-8

"""
Fetch the comments of a Hacker News story. Useful for "Who is hiring" posts.
"""

import re
import sys
import html
import json
import asyncio
import argparse
import urllib.request


HN_TEMPLATE = " https://hacker-news.firebaseio.com/v0/item/{}.json"
SEP = "\n" + ("-" * 80) + "\n"

verbose = False

# asyncio Semaphore for limiting concurrency. Must be initialized "inside" async.run
sem = None


def eprint(*args, **kwargs):
    if verbose:
        print(*args, **kwargs, file=sys.stderr, flush=True)


async def download_id(item_id) -> dict:
    def sync_download():
        with urllib.request.urlopen(HN_TEMPLATE.format(item_id)) as f:
            return json.load(f) or {}

    loop = asyncio.get_running_loop()
    async with sem:
        return await loop.run_in_executor(None, sync_download)


async def download_comment(kid_id) -> dict:
    comment = await download_id(kid_id)
    by = comment.get("by", "?")
    extract_len = 80 - len(by) - len(str(kid_id)) - len(", : ...")
    extract = comment.get("text", "?")[:extract_len].replace("\n", " ")
    feedback = f"{kid_id}, {by}: {extract}..."
    eprint(feedback)
    return comment


def format_comment(comment):
    id_ = comment.get("id", "?")
    text = html.unescape(comment.get("text", "?!"))
    formatted = f"{id_}\n{text}"
    # basic html processing, don't want to add to much boilerplate, so just "newlines"
    formatted = formatted.replace("<p>", "\n")
    return formatted


def validate_comment(text, regex):
    return regex is None or all(re.search(r, text, re.I | re.S) is not None for r in regex)


async def main(story_id, output, *, regex=None, num=None, jobs=10):
    # Setup global semaphore for force-limiting concurrent downloads
    global sem
    sem = asyncio.Semaphore(jobs)

    # Download post page
    eprint(f"Scraping id {story_id}...")
    story = await download_id(story_id)
    eprint(story["title"])
    eprint(f"Expecting {len(story['kids'])} jobs")

    # Select comments ids
    targets = story["kids"]
    if num is not None:
        targets = targets[: int(num)]

    # Define a wrapper function for processing comments when ready
    async def download_process_comment(item_id):
        comment = await download_comment(item_id)
        formatted = format_comment(comment)
        if validate_comment(formatted, regex):
            if output == "-":
                print(SEP + formatted)
            return formatted
        else:
            return None

    # Download the comments asynchronously
    tasks = [asyncio.create_task(download_process_comment(kid)) for kid in targets]
    comments = await asyncio.gather(*tasks)
    eprint(f"Scraped {len(comments)} comments")

    selected = list(filter(None, comments))
    eprint(f"Selected {len(selected)} comments")

    # Write the selected comments
    if output != "-":
        with open(output, "w", encoding="utf-8") as o:
            o.write(SEP.join(selected))
        eprint(f"Written to {output}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "id", nargs="?", default="24038520", help="Item ID of the story"
    )

    parser.add_argument(
        "-o", "--output", default="-", help="Output file name ('-' for stdout)"
    )

    parser.add_argument(
        "-j", "--jobs", type=int, default=10, help="Max concurrent download"
    )

    parser.add_argument("-n", "--num", help="Number of comments to download")

    parser.add_argument(
        "-r",
        "--regex",
        action="append",
        help="Regex applied to items content for filtering, using"
        " Python syntax and flags re.IGNORECASE and re.DOTALL."
        " If used multiple times, the checks and ANDed.",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable status output to stderr"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    verbose = args.verbose
    asyncio.run(
        main(args.id, args.output, regex=args.regex, num=args.num, jobs=args.jobs)
    )
