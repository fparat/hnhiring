#!/usr/bin/env python3
# coding: utf-8

import sys
import html
import json
import asyncio
import argparse
import urllib.request


HN_TEMPLATE = " https://hacker-news.firebaseio.com/v0/item/{}.json"
SEP = "\n" + ("-" * 80) + "\n"

# asyncio Semaphore for limiting concurrency. Must be initialized "inside" async.run
sem = None


def eprint(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr, flush=True)


async def download_id(item_id) -> dict:
    def sync_download():
        with urllib.request.urlopen(HN_TEMPLATE.format(item_id)) as f:
            return json.load(f)

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


async def main(story_id, output, *, num=None, jobs=10):
    global sem
    sem = asyncio.Semaphore(jobs)

    eprint(f"Scraping id {story_id}...")
    story = await download_id(story_id)
    eprint(story["title"])
    eprint(f"Expecting {len(story['kids'])} jobs")

    targets = story["kids"]
    if num is not None:
        targets = targets[: int(num)]

    tasks = [asyncio.create_task(download_comment(kid_id)) for kid_id in targets]
    comments = await asyncio.gather(*tasks)
    eprint(f"Scraped {len(comments)} comments")

    result = SEP.join(format_comment(c) for c in comments)
    if output == "-":
        print(result)
    else:
        with open(output, "w", encoding="utf-8") as o:
            o.write(result)
        eprint(f"Written to {output}")


def parse_args():
    parser = argparse.ArgumentParser(
        description='Fetch the comments of a Hacker News story. Useful for "Who is hiring" posts.'
    )
    parser.add_argument(
        "id", nargs="?", default="24038520", help="Item ID of the story"
    )

    parser.add_argument(
        "-o", "--output", default="-", help="Output file name ('-' for stdout)"
    )

    parser.add_argument(
        "-j", "--jobs", type=int, default=10, help="Max concurrent download"
    )

    parser.add_argument(
        "-n", "--num", default=None, help="Number of comments to download"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.id, args.output, num=args.num, jobs=args.jobs))
