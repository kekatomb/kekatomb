import datetime
import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree

GITHUB_USER = "kekatomb"
RSS_URL = "https://lindg.re/rss.xml"
GITHUB_API = f"https://api.github.com/users/{GITHUB_USER}"
REPOS_API = f"https://api.github.com/repos/{GITHUB_USER}"

MAX_POSTS = 3
TOP_LANGUAGES = 3
RSS_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
README_PATH = os.path.join(REPO_ROOT, "README.md")
PROFILE_PATH = os.path.join(REPO_ROOT, "PROFILE.md")


def fetch_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": "profile-readme"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.read()
    except urllib.error.URLError:
        return None


def fetch_json(url):
    content = fetch_bytes(url)
    if content is None:
        return None
    return json.loads(content)


ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal_suffix(day):
    if 10 <= day % 100 <= 20:
        return "th"
    return ORDINAL_SUFFIXES.get(day % 10, "th")


def parse_rss_date(value):
    try:
        return datetime.datetime.strptime(value, RSS_DATE_FORMAT)
    except (ValueError, TypeError):
        return None


def format_post_date(parsed):
    return f"{parsed.strftime('%B')} {parsed.day}{ordinal_suffix(parsed.day)}, {parsed.year}"


def build_blog_section():
    feed = fetch_bytes(RSS_URL)
    if feed is None:
        return []

    root = ElementTree.fromstring(feed)
    posts = []
    for item in root.iter("item"):
        parsed = parse_rss_date(item.findtext("pubDate", default=""))
        if parsed is None:
            continue
        posts.append(
            {
                "title": item.findtext("title", default="").strip(),
                "link": item.findtext("link", default="").strip(),
                "pub_date": format_post_date(parsed),
                "parsed": parsed,
            }
        )

    posts.sort(key=lambda post: post["parsed"], reverse=True)
    if not posts:
        return []

    lines = ["## Latest Blog Posts"]
    for post in posts[:MAX_POSTS]:
        lines.append(f"- {post['pub_date']}, [{post['title']}]({post['link']})")
    return lines


def summarize_languages(language_bytes):
    if not language_bytes:
        return ""
    languages = sorted(language_bytes, key=language_bytes.get, reverse=True)[:TOP_LANGUAGES]
    suffix = "..." if len(language_bytes) > TOP_LANGUAGES else ""
    return ", ".join(languages) + suffix


def build_tag_section():
    repos = fetch_json(f"{GITHUB_API}/repos")
    if not repos:
        return []

    by_topic = {}
    for repo in repos:
        name = repo["name"]
        description = (repo.get("description") or "").strip()
        languages = summarize_languages(fetch_json(f"{REPOS_API}/{name}/languages"))
        row = (
            f"| [{name}](https://github.com/{GITHUB_USER}/{name}) "
            f"| {description} | {languages} |"
        )
        for topic in repo.get("topics", []):
            by_topic.setdefault(topic, []).append(row)

    if not by_topic:
        return []

    sections = []
    for topic in sorted(by_topic):
        sections.append(
            f"## {topic}\n"
            f"| Repository | Description | Languages |\n"
            f"|------------|-------------|-----------|\n"
            + "\n".join(by_topic[topic])
        )
    return sections


def load_profile():
    with open(PROFILE_PATH, encoding="utf-8") as handle:
        return handle.read().strip()


def main():
    sections = build_blog_section() + build_tag_section()
    readme = load_profile() + "\n\n" + "\n\n".join(sections) + "\n"
    with open(README_PATH, "w", encoding="utf-8") as handle:
        handle.write(readme)


if __name__ == "__main__":
    main()
