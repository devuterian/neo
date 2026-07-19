#!/usr/bin/env python3
"""Build calendar index and output to JSON. Used by `neoctl calendar refresh`."""
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes/skills/productivity/google-workspace/scripts'))
from google_api import get_credentials
from googleapiclient.discovery import build


def build_index(config_path: Path, range_weeks: int = 6, output_path: Path | None = None) -> dict:
    config = json.loads(config_path.read_text())
    cal_cfg = config.get('calendar', {})
    read_only_ids = cal_cfg.get('read_only_calendar_ids', [])
    managed_id = cal_cfg.get('managed_calendar_id')

    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    range_start = now.isoformat()
    range_end = (now + timedelta(weeks=range_weeks)).isoformat()

    all_cal_ids = list(read_only_ids) + ([managed_id] if managed_id else [])
    all_events = {}

    for cal_id in all_cal_ids:
        page_token = None
        while True:
            events_result = service.events().list(
                calendarId=cal_id,
                timeMin=range_start,
                timeMax=range_end,
                singleEvents=True,
                orderBy='startTime',
                maxResults=100,
                pageToken=page_token,
            ).execute()
            for event in events_result.get('items', []):
                event_id = event['id']
                start = event.get('start', {})
                end = event.get('end', {})
                is_all_day = 'date' in start
                all_events[f"{cal_id}::{event_id}"] = {
                    "event_id": event_id,
                    "calendar_id": cal_id,
                    "title": event.get('summary', '(제목 없음)'),
                    "starts_at": start.get('dateTime') or (start.get('date') + "T00:00:00+09:00"),
                    "ends_at": end.get('dateTime') or (end.get('date') + "T00:00:00+09:00"),
                    "all_day": is_all_day,
                    "color_id": event.get('colorId'),
                    "links": {
                        "event_type": "external" if cal_id in read_only_ids else "unknown",
                        "project_id": None,
                        "milestone_id": None,
                        "task_id": None,
                        "day_id": None,
                    },
                }
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break

    index = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "source": {
            "status": "available",
            "fetched_at": now.isoformat(),
            "range_start": range_start,
            "range_end": range_end,
            "error": None,
        },
        "events": all_events,
    }

    if output_path:
        output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
        print(f"Written {len(all_events)} events to {output_path}", file=sys.stderr)

    return index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--range-weeks", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_path = Path("config/app.json")
    build_index(config_path, args.range_weeks, args.output)


if __name__ == "__main__":
    main()
