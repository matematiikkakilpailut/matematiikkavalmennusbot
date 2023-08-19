import os

import feedparser
import tomlkit
from filelock import FileLock


def get_unseen_entries(feed_url, state_file="state.toml"):
    """Get unseen entries from a feed."""

    create_state_file(state_file)
    etag, modified = get_feed_headers(state_file)
    latest_feed, new_etag, new_modified = fetch_feed(feed_url, etag, modified)
    save_feed_headers(new_etag, new_modified, state_file)
    seen_ids = get_seen_entry_ids(state_file)
    new = [entry for entry in latest_feed.entries if entry.id not in seen_ids]
    save_entry_ids([entry.id for entry in new], state_file)
    return new


def create_state_file(file_path):
    """Create a TOML file if it doesn't exist."""
    with FileLock(file_path + ".lock"):
        with open(file_path, "a") as f:
            f.write("")


def fetch_feed(feed_url, etag=None, modified=None):
    """Fetch the feed and return parsed feed along with ETag and Last-Modified values."""
    feed = feedparser.parse(feed_url, etag=etag, modified=modified)
    return feed, feed.get("etag"), feed.get("modified")


def save_feed_headers(etag, modified, file_path):
    """Save the ETag and Last-Modified values to a TOML file."""
    with FileLock(file_path + ".lock"):
        with open(file_path, "r+t") as f:
            data = tomlkit.load(f)
            os.ftruncate(f.fileno(), 0)
            os.lseek(f.fileno(), 0, os.SEEK_SET)
            if "feed" not in data:
                feed = tomlkit.table()
                data["feed"] = feed
            else:
                feed = data["feed"]
            if etag:
                feed["etag"] = etag
            if modified:
                feed["modified"] = modified
            tomlkit.dump(data, f)


def get_feed_headers(file_path):
    try:
        with FileLock(file_path + ".lock"):
            with open(file_path, "r") as f:
                data = tomlkit.load(f)
        feed = data["feed"]
        etag = feed["etag"] if "etag" in feed else None
        modified = feed["modified"] if "modified" in feed else None
        return etag, modified
    except (FileNotFoundError, KeyError):
        print("No state file found, fetching feed from scratch.")
        return None, None


def save_entry_ids(entry_ids, file_path):
    """Save the seen entry IDs."""
    with FileLock(file_path + ".lock"):
        with open(file_path, "r+t") as f:
            data = tomlkit.load(f)
            os.ftruncate(f.fileno(), 0)
            os.lseek(f.fileno(), 0, os.SEEK_SET)
            if "entries_seen" not in data:
                seen = tomlkit.array()
                seen.multiline(True)
                data["entries_seen"] = seen
            else:
                seen = data["entries_seen"]
            seen.extend(entry_ids)
            tomlkit.dump(data, f)


def get_seen_entry_ids(file_path):
    try:
        with FileLock(file_path + ".lock"):
            with open(file_path, "r") as f:
                data = tomlkit.load(f)
        return set(data.get("entries_seen", []))
    except FileNotFoundError:
        return set()
