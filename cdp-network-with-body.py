#!/usr/bin/env python3
# cdp-network-with-body.py - Network monitoring with response body capture
import sys
import json
import asyncio
import websockets

if len(sys.argv) < 2:
    print('Usage: cdp-network-with-body.py <page-id> [url] [--port=9222] [--filter=pattern]', file=sys.stderr)
    sys.exit(1)

# Parse arguments
page_id = sys.argv[1]
url = None
port = 9222
url_filter = None

for arg in sys.argv[2:]:
    if arg.startswith('--port='):
        port = int(arg.split('=')[1])
    elif arg.startswith('--filter='):
        url_filter = arg.split('=')[1]
    elif not arg.startswith('--'):
        url = arg

ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'

async def monitor_network():
    msg_id = 1
    response_bodies = {}  # Store request IDs for responses we want to capture

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
        async for message in ws:
            msg = json.loads(message)

            # Track requests that match our filter
            if msg.get('method') == 'Network.responseReceived':
                response = msg['params']['response']
                request_id = msg['params']['requestId']
                response_url = response['url']

                # If we have a filter and this URL matches, request the body
                if url_filter and url_filter in response_url:
                    response_bodies[request_id] = response_url

                    # Request the response body
                    await ws.send(json.dumps({
                        'id': msg_id,
                        'method': 'Network.getResponseBody',
                        'params': {'requestId': request_id}
                    }))
                    msg_id += 1

                    print(json.dumps({
                        'event': 'response',
                        'url': response_url,
                        'status': response['status'],
                        'statusText': response['statusText'],
                        'mimeType': response['mimeType'],
                        'requestId': request_id
                    }), flush=True)

            # Handle response body
            elif msg.get('result') and 'body' in msg.get('result', {}):
                body = msg['result']['body']
                base64_encoded = msg['result'].get('base64Encoded', False)

                if base64_encoded:
                    import base64
                    body = base64.b64decode(body).decode('utf-8', errors='ignore')

                print(json.dumps({
                    'event': 'response_body',
                    'body': body
                }), flush=True)

            # Also output regular network events if no filter
            elif not url_filter:
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
