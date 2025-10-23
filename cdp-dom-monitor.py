#!/usr/bin/env python3
# cdp-dom-monitor.py - Monitor DOM changes and extract form field values in real-time
# Uses DOM mutation observers to detect changes without polling

import sys
import json
import asyncio
import websockets
import argparse

async def monitor_dom(page_id, url=None, port=9222, selector=None, poll_interval=1.0, duration=None):
    """
    Monitor DOM for form field changes using mutation observers.

    Args:
        page_id: CDP page ID
        url: Optional URL to navigate to first
        port: CDP debugging port
        selector: CSS selector to monitor (e.g., "input[name='email']")
        poll_interval: How often to poll for values (seconds)
        duration: Maximum duration to monitor (seconds)
    """
    ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        print(f'Connected to CDP (port {port})', file=sys.stderr)

        # Enable DOM domain
        await ws.send(json.dumps({'id': msg_id, 'method': 'DOM.enable'}))
        msg_id += 1

        # Enable Runtime for JavaScript execution
        await ws.send(json.dumps({'id': msg_id, 'method': 'Runtime.enable'}))
        msg_id += 1

        # Navigate if URL provided
        if url:
            print(f'Navigating to: {url}', file=sys.stderr)
            await ws.send(json.dumps({
                'id': msg_id,
                'method': 'Page.navigate',
                'params': {'url': url}
            }))
            msg_id += 1
            await asyncio.sleep(2)  # Wait for page load

        print(f'Monitoring DOM changes...', file=sys.stderr)
        if selector:
            print(f'Selector: {selector}', file=sys.stderr)
        print(f'Poll interval: {poll_interval}s', file=sys.stderr)
        if duration:
            print(f'Duration: {duration}s', file=sys.stderr)
        print('', file=sys.stderr)

        # JavaScript to extract form field values
        extract_js = """
        (function() {
            const selector = arguments[0];
            let elements;

            if (selector) {
                elements = document.querySelectorAll(selector);
            } else {
                // Default: all input, textarea, select elements
                elements = document.querySelectorAll('input, textarea, select');
            }

            const results = [];

            elements.forEach(el => {
                const data = {
                    tag: el.tagName.toLowerCase(),
                    type: el.type || null,
                    name: el.name || null,
                    id: el.id || null,
                    value: el.value || '',
                    placeholder: el.placeholder || null,
                    required: el.required || false,
                    disabled: el.disabled || false,
                    readonly: el.readOnly || false
                };

                // For checkboxes and radios, add checked state
                if (el.type === 'checkbox' || el.type === 'radio') {
                    data.checked = el.checked;
                }

                // For select elements, add selected option
                if (el.tagName.toLowerCase() === 'select') {
                    data.selectedIndex = el.selectedIndex;
                    data.selectedText = el.options[el.selectedIndex]?.text || null;
                }

                results.push(data);
            });

            return {
                timestamp: Date.now(),
                count: results.length,
                fields: results
            };
        })
        """

        # Track previous values to detect changes
        previous_state = {}
        is_first_run = True
        start_time = asyncio.get_event_loop().time()

        async def poll_values():
            nonlocal msg_id, previous_state, is_first_run

            while True:
                # Check duration
                if duration:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= duration:
                        print(f'Duration limit reached ({duration}s)', file=sys.stderr)
                        break

                # Evaluate JavaScript to get current form state
                await ws.send(json.dumps({
                    'id': msg_id,
                    'method': 'Runtime.evaluate',
                    'params': {
                        'expression': f'({extract_js})({json.dumps(selector)})',
                        'returnByValue': True
                    }
                }))
                eval_msg_id = msg_id
                msg_id += 1

                # Wait for response
                while True:
                    response = await ws.recv()
                    result = json.loads(response)

                    # Check if this is our eval response
                    if result.get('id') == eval_msg_id:
                        if 'result' in result and 'result' in result['result']:
                            data = result['result']['result']['value']

                            # Check for changes
                            current_state = {}
                            changes_detected = False

                            # First run - output initial state before processing
                            if is_first_run:
                                print(json.dumps({
                                    'event': 'initial_state',
                                    'timestamp': data['timestamp'],
                                    'count': data['count'],
                                    'fields': data['fields']
                                }), flush=True)
                                is_first_run = False

                            for field in data['fields']:
                                # Create a unique key for this field
                                key = f"{field.get('name', '')}:{field.get('id', '')}:{field.get('type', '')}"
                                current_value = field.get('value', '')

                                current_state[key] = current_value

                                # Detect changes (skip on first run since we already reported initial state)
                                if key in previous_state:
                                    if previous_state[key] != current_value:
                                        changes_detected = True
                                        print(json.dumps({
                                            'event': 'field_changed',
                                            'timestamp': data['timestamp'],
                                            'field': field,
                                            'old_value': previous_state[key],
                                            'new_value': current_value
                                        }), flush=True)
                                else:
                                    # New field detected (only if not first run)
                                    if current_value and previous_state:  # Only report if it has a value and not first run
                                        changes_detected = True
                                        print(json.dumps({
                                            'event': 'field_detected',
                                            'timestamp': data['timestamp'],
                                            'field': field
                                        }), flush=True)

                            # Update state
                            previous_state = current_state

                        break

                    # Handle other messages (mutations, etc.)
                    if result.get('method') == 'DOM.attributeModified':
                        # DOM attribute changed
                        pass  # We're polling instead of using these events

                # Wait before next poll
                await asyncio.sleep(poll_interval)

        # Start polling
        await poll_values()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Monitor DOM for form field changes')
    parser.add_argument('page_id', help='CDP page ID')
    parser.add_argument('url', nargs='?', help='URL to navigate to (optional)')
    parser.add_argument('--port', type=int, default=9222, help='CDP debugging port (default: 9222)')
    parser.add_argument('--selector', help='CSS selector to monitor (e.g., "input[name=\'email\']")')
    parser.add_argument('--poll-interval', type=float, default=1.0, help='Poll interval in seconds (default: 1.0)')
    parser.add_argument('--duration', type=float, help='Maximum monitoring duration in seconds')

    args = parser.parse_args()

    try:
        asyncio.run(monitor_dom(
            args.page_id,
            args.url,
            args.port,
            args.selector,
            args.poll_interval,
            args.duration
        ))
    except KeyboardInterrupt:
        print('\nMonitoring stopped', file=sys.stderr)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
