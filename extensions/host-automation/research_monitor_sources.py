"""Read-only, bounded primary-source collection for research-monitor."""
import argparse
import concurrent.futures
import datetime as dt
import email.utils
import json
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
CATEGORIES = ('cs.AI', 'cs.CL', 'cs.LG')

def collect(url, start, end):
    result = {'url': url}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'HermesResearchMonitor/1.0'})
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(5000000)
        root = ET.fromstring(raw)
        if root.tag.endswith('rss'):
            channel = root.find('channel')
            result['channel_pubDate'] = channel.findtext('pubDate')
            result['lastBuildDate'] = channel.findtext('lastBuildDate')
            items = channel.findall('item')
            result['total_items'] = len(items)
            dated, missing, selected = [], 0, []
            for item in items:
                date = item.findtext('pubDate') or channel.findtext('pubDate')
                try:
                    stamp = email.utils.parsedate_to_datetime(date).astimezone(UTC)
                except (ValueError, TypeError, AttributeError):
                    missing += 1
                    continue
                dated.append(stamp.isoformat())
                if start <= stamp <= end:
                    selected.append({'title': item.findtext('title'), 'url': item.findtext('link'), 'announcement_time': stamp.isoformat(), 'description': item.findtext('description')})
            result.update(timestamp_range=[min(dated), max(dated)] if dated else [], undated_items=missing, in_window=selected)
        else:
            ns = {'a': 'http://www.w3.org/2005/Atom'}
            result['timestamp_semantics'] = 'API published is submission time, NOT announcement time'
            result['entries'] = [{'title': e.findtext('a:title', namespaces=ns), 'url': e.findtext('a:id', namespaces=ns), 'submitted': e.findtext('a:published', namespaces=ns), 'updated': e.findtext('a:updated', namespaces=ns)} for e in root.findall('a:entry', ns)]
        result['ok'] = True
    except Exception as exc:
        result.update(ok=False, error=f'{type(exc).__name__}: {exc}')
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--end', help='ISO UTC end; default now')
    parser.add_argument('--output', help='Optional local evidence JSON path')
    args = parser.parse_args()
    end = dt.datetime.fromisoformat(args.end.replace('Z', '+00:00')) if args.end else dt.datetime.now(UTC)
    if end.tzinfo is None:
        parser.error('--end requires an explicit timezone')
    start = end - dt.timedelta(hours=6)
    urls = [f'https://rss.arxiv.org/rss/{c}' for c in CATEGORIES]
    urls.append('https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&start=0&max_results=30')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(lambda url: collect(url, start, end), urls))
    report = {'window_start': start.isoformat(), 'window_end': end.isoformat(), 'sources': sources, 'warning': 'Failed/undated sources mean incomplete coverage, never no-news. Verify any RSS candidates against primary paper pages. Web/agent announcements require separate checks.'}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as file:
            file.write(text)
    print('PRECOLLECTED RESEARCH SOURCE EVIDENCE\n' + text)

if __name__ == '__main__':
    main()
