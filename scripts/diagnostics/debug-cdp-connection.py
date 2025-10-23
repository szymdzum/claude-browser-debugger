#!/usr/bin/env python3
"""
Debug script to isolate where websockets hangs
Run with: PYTHONASYNCIODEBUG=1 python3 debug-cdp-connection.py PAGE_ID PORT
"""
import asyncio
import websockets
import json
import sys
import logging

# Enable all async debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_connection(page_id, port=9222):
    ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'

    print(f'[1] Starting connection to: {ws_url}')

    try:
        print(f'[2] Calling websockets.connect()...')
        async with websockets.connect(ws_url) as ws:
            print(f'[3] ✅ Connected successfully!')

            print(f'[4] Sending Runtime.evaluate command...')
            await ws.send(json.dumps({
                'id': 1,
                'method': 'Runtime.evaluate',
                'params': {
                    'expression': '2 + 2',
                    'returnByValue': True
                }
            }))
            print(f'[5] Command sent, waiting for response...')

            print(f'[6] Calling ws.recv()...')
            response = await ws.recv()
            print(f'[7] ✅ Received response!')

            result = json.loads(response)
            print(f'[8] Result: {result}')

            return result

    except Exception as e:
        print(f'[ERROR] Exception: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: debug-cdp-connection.py <page_id> [port]")
        sys.exit(1)

    page_id = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9222

    print(f'=== CDP Connection Debug ===')
    print(f'Page ID: {page_id}')
    print(f'Port: {port}')
    print(f'Python: {sys.version}')
    print(f'Async Debug: {asyncio.get_event_loop().get_debug()}')
    print(f'===========================\n')

    result = asyncio.run(test_connection(page_id, port))

    if result:
        print(f'\n✅ SUCCESS: Connection worked!')
        sys.exit(0)
    else:
        print(f'\n❌ FAILED: Connection did not complete')
        sys.exit(1)
