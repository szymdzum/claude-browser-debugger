#!/usr/bin/env python3
# cdp-network.py - Network monitoring using Python with configurable port

import sys
import json
import asyncio
import websockets

idle_timeout = None

if len(sys.argv) < 2:
    print('Usage: cdp-network.py <page-id> [url] [--port=9222] [--idle-timeout=seconds]', file=sys.stderr)
    sys.exit(1)

# Parse arguments
page_id = sys.argv[1]
url = None
port = 9222

for arg in sys.argv[2:]:
    if arg.startswith('--port='):
        port = int(arg.split('=')[1])
    elif arg.startswith('--idle-timeout='):
        try:
            idle_timeout = float(arg.split('=')[1])
        except ValueError:
            print('Invalid idle-timeout value', file=sys.stderr)
            sys.exit(1)
    elif not arg.startswith('--'):
        url = arg

ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'

async def monitor_network():
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        print(f'Connected to CDP (port {port})', file=sys.stderr)

        # Enable network domain
        await ws.send(json.dumps({'id': msg_id, 'method': 'Network.enable'}))
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
        while True:
            try:
                if idle_timeout:
                    message = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
                else:
                    message = await ws.recv()
            except asyncio.TimeoutError:
                print(f'Idle timeout reached after {idle_timeout} seconds', file=sys.stderr)
                break

            msg = json.loads(message)

            # Output key network events
            if msg.get('method') == 'Network.requestWillBeSent':
                print(json.dumps({
                    'event': 'request',
                    'url': msg['params']['request']['url'],
                    'method': msg['params']['request']['method'],
                    'requestId': msg['params']['requestId']
                }), flush=True)

            elif msg.get('method') == 'Network.responseReceived':
                response = msg['params']['response']
                print(json.dumps({
                    'event': 'response',
                    'url': response['url'],
                    'status': response['status'],
                    'statusText': response['statusText'],
                    'mimeType': response['mimeType'],
                    'requestId': msg['params']['requestId']
                }), flush=True)

            elif msg.get('method') == 'Network.loadingFailed':
                print(json.dumps({
                    'event': 'failed',
                    'errorText': msg['params']['errorText'],
                    'requestId': msg['params']['requestId']
                }), flush=True)

if __name__ == '__main__':
    try:
        asyncio.run(monitor_network())
    except KeyboardInterrupt:
        print('\nConnection closed', file=sys.stderr)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
