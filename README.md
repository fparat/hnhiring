This is a small dependency-less, async, pure Python script that scrap the
comments of any Hacker New story.

It only downloads the root comments, so it is useful for "Who is hiring?" posts
like: https://news.ycombinator.com/item?id=24038520

To use it download
[`hnhiring.py`](https://raw.githubusercontent.com/fparat/hnhiring/master/hnhiring.py)
and run it with Python 3.8+.

Example:

```
# Find jobs mentioning Python or Flask (the case is ignored)
python3 hnhiring.py -r "(python|flask)" > jobs.txt
```

If you need more power, you might be interested by haxor-news:
https://github.com/donnemartin/haxor-news

License: MIT
