#!/usr/bin/env python3
"""
parse-redux-logs.py - Extract Redux state timeline from console logs

Usage:
    python3 parse-redux-logs.py <LOG_FILE> [--output OUTPUT_FILE]

Examples:
    python3 parse-redux-logs.py /tmp/register-test-console.log
    python3 parse-redux-logs.py /tmp/test-console.log -o /tmp/timeline.json
"""

import re
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# T053: Regex patterns for redux-logger format
REDUX_ACTION_PATTERN = r'action\s+(.+?)\s+@\s+(\d{2}:\d{2}:\d{2}\.\d{3})'
PREV_STATE_PATTERN = r'prev state\s+(.+?)(?=\n|$)'
NEXT_STATE_PATTERN = r'next state\s+(.+?)(?=\n|$)'

# T054: Safe JSON parsing with error handling
def parse_json_safe(json_str):
    """
    Attempt to parse JSON, return parsed object or original string if fails.
    Returns: (parsed_value, success_boolean)
    """
    # Remove "Object " prefix if present
    json_str = re.sub(r'^Object\s+', '', json_str.strip())

    try:
        return json.loads(json_str), True
    except json.JSONDecodeError:
        return json_str, False

# T055-T063: Main parsing loop
def parse_redux_logs(log_file_path):
    """
    Parse console log file and extract Redux state timeline.
    Returns: (timeline_list, warnings_list)
    """
    timeline = []
    current_event = {}
    warnings = []

    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # T056: Match action line
                action_match = re.search(REDUX_ACTION_PATTERN, line)
                if action_match:
                    # Save previous event if exists
                    if current_event:
                        timeline.append(current_event)

                    # T056: Create new event
                    current_event = {
                        'timestamp': action_match.group(2),
                        'actionType': action_match.group(1).strip(),
                        'prevState': None,
                        'nextState': None,
                        'parsedSuccessfully': True
                    }
                    continue

                # T057: Match prev state
                prev_match = re.search(PREV_STATE_PATTERN, line)
                if prev_match and current_event:
                    state_str = prev_match.group(1).strip()
                    state, success = parse_json_safe(state_str)
                    current_event['prevState'] = state
                    if not success:
                        warnings.append(f"Line {line_num}: Malformed prevState JSON")
                        current_event['parsedSuccessfully'] = False
                    continue

                # T058: Match next state
                next_match = re.search(NEXT_STATE_PATTERN, line)
                if next_match and current_event:
                    state_str = next_match.group(1).strip()
                    state, success = parse_json_safe(state_str)
                    current_event['nextState'] = state
                    if not success:
                        warnings.append(f"Line {line_num}: Malformed nextState JSON")
                        current_event['parsedSuccessfully'] = False
                    continue

            # T059: Save last event
            if current_event:
                timeline.append(current_event)

    except FileNotFoundError:
        print(f"L Error: Log file not found: {log_file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"L Error reading log file: {e}", file=sys.stderr)
        sys.exit(2)

    return timeline, warnings

# T052: Main entry point with argument parsing
def main():
    parser = argparse.ArgumentParser(
        description='Parse Redux state timeline from console logs',
        epilog='Example: python3 parse-redux-logs.py /tmp/test-console.log'
    )
    parser.add_argument('log_file', help='Path to console log file')
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: {log_file}-timeline.json)'
    )
    args = parser.parse_args()

    log_file = Path(args.log_file)

    # T061: Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        # Default: same name with -timeline.json suffix
        output_file = log_file.parent / f"{log_file.stem}-timeline.json"

    # T062: User-friendly output
    print(f"= Parsing Redux logs from {log_file}")

    # T055: Parse logs
    timeline, warnings = parse_redux_logs(log_file)

    # T060: Generate metadata
    successful_events = sum(1 for e in timeline if e.get('parsedSuccessfully', True))

    output = {
        'metadata': {
            'logFile': str(log_file),
            'parsedAt': datetime.now().isoformat(),
            'totalEvents': len(timeline),
            'successfulEvents': successful_events,
            'warnings': warnings
        },
        'timeline': timeline
    }

    # T061: Write output file
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    # T062: Final user output
    print(f" Extracted {len(timeline)} Redux events")

    if warnings:
        print(f"   {len(warnings)} warnings (see {output_file} for details)")

    # T063: Empty timeline suggestion
    if len(timeline) == 0:
        print("=¡ No redux-logger output found. Ensure redux-logger is enabled in the app.")

    print(f"=Â Timeline saved to: {output_file}")
    print("")

if __name__ == '__main__':
    main()
