#!/usr/bin/env python3
# cdp-console.py - Console monitoring using Python with configurable port

import sys
import json
import asyncio
import websockets

if len(sys.argv) < 2:
    print('Usage: cdp-console.py <page-id> [url] [--port=9222]', file=sys.stderr)
    sys.exit(1)

# Parse arguments
page_id = sys.argv[1]
url = None
port = 9222

for arg in sys.argv[2:]:
    if arg.startswith('--port='):
        port = int(arg.split('=')[1])
    elif not arg.startswith('--'):
        url = arg

ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'

async def monitor_console():
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        print(f'Connected to CDP (port {port})', file=sys.stderr)

        # Enable domains
        await ws.send(json.dumps({'id': msg_id, 'method': 'Runtime.enable'}))
        msg_id += 1
        await ws.send(json.dumps({'id': msg_id, 'method': 'Log.enable'}))
        msg_id += 1
        await ws.send(json.dumps({'id': msg_id, 'method': 'Console.enable'}))
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

        # Listen for messages
        async for message in ws:
            msg = json.loads(message)

            # Output console messages
            if msg.get('method') == 'Runtime.consoleAPICalled':
                args = []
                for arg in msg['params']['args']:
                    if arg.get('type') == 'string':
                        args.append(arg['value'])
                    elif 'value' in arg:
                        args.append(arg['value'])
                    else:
                        args.append(arg.get('description', str(arg)))

                print(json.dumps({
                    'type': msg['params']['type'],
                    'timestamp': msg['params']['timestamp'],
                    'message': ' '.join(str(a) for a in args),
                    'stackTrace': msg['params'].get('stackTrace')
                }))

            # Output log entries
            elif msg.get('method') == 'Log.entryAdded':
                entry = msg['params']['entry']
                print(json.dumps({
                    'type': entry['level'],
                    'timestamp': entry['timestamp'],
                    'message': entry['text'],
                    'source': entry.get('source'),
                    'url': entry.get('url'),
                    'lineNumber': entry.get('lineNumber')
                }))

            # Output exceptions
            elif msg.get('method') == 'Runtime.exceptionThrown':
                details = msg['params']['exceptionDetails']
                print(json.dumps({
                    'type': 'exception',
                    'timestamp': msg['params']['timestamp'],
                    'message': details['text'],
                    'exception': details.get('exception'),
                    'stackTrace': details.get('stackTrace')
                }))

if __name__ == '__main__':
    try:
        asyncio.run(monitor_console())
    except KeyboardInterrupt:
        print('\nConnection closed', file=sys.stderr)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
