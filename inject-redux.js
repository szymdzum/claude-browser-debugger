// inject-redux.js - Redux store injection script
// Purpose: Search for and expose Redux store at window.__EXPOSED_REDUX_STORE__
//
// Usage via websocat:
//   WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
//   cat inject-redux.js | websocat -n1 "$WS_URL"
//
// Or via CDP Runtime.evaluate - use minified version from bottom of this file

// T026-T035: Redux store search and exposure logic
(() => {
  // T027: Method 1 - Check common globals
  if (window.__REDUX_STORE__) {
    window.__EXPOSED_REDUX_STORE__ = window.__REDUX_STORE__;
    console.log(' Redux store exposed at window.__EXPOSED_REDUX_STORE__ (found at window.__REDUX_STORE__)');
    return;
  }
  if (window.store?.getState) {
    window.__EXPOSED_REDUX_STORE__ = window.store;
    console.log(' Redux store exposed at window.__EXPOSED_REDUX_STORE__ (found at window.store)');
    return;
  }

  // T028-T031: Method 2 - Walk React Fiber tree
  const rootSelectors = ['#app', '#root', '[data-reactroot]', 'body > div:first-child'];

  for (const selector of rootSelectors) {
    const root = document.querySelector(selector);
    if (!root) continue;

    // T030: Find React Fiber key
    const fiberKey = Object.keys(root).find(k =>
      k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
    );
    if (!fiberKey) continue;

    // T031: Walk up Fiber tree with depth limit
    let fiber = root[fiberKey];
    let depth = 0;
    const maxDepth = 50;  // Prevent infinite loops

    while (fiber && depth++ < maxDepth) {
      // Check for Redux Provider's store prop (memoizedProps)
      if (fiber.memoizedProps?.store?.getState) {
        // T032: Expose store and log success
        window.__EXPOSED_REDUX_STORE__ = fiber.memoizedProps.store;
        console.log(` Redux store exposed at window.__EXPOSED_REDUX_STORE__ (found in Fiber tree at ${selector})`);
        return;
      }

      // Check stateNode (class components)
      if (fiber.stateNode?.store?.getState) {
        window.__EXPOSED_REDUX_STORE__ = fiber.stateNode.store;
        console.log(` Redux store exposed at window.__EXPOSED_REDUX_STORE__ (found in stateNode at ${selector})`);
        return;
      }

      fiber = fiber.return;
    }
  }

  // T033: Graceful failure with fallback suggestion
  console.warn('L Could not find Redux store');
  console.info('=¡ Fallback: Use parse-redux-logs.py to extract state from console logs');
})();

/*
T034: Minified version for CDP command usage

For use with echo + websocat or direct CDP commands, copy the line below:

(()=>{if(window.__REDUX_STORE__){window.__EXPOSED_REDUX_STORE__=window.__REDUX_STORE__;console.log(" Redux store exposed");return}if(window.store?.getState){window.__EXPOSED_REDUX_STORE__=window.store;console.log(" Redux store exposed");return}const s=["#app","#root","[data-reactroot]","body > div:first-child"];for(const e of s){const r=document.querySelector(e);if(!r)continue;const o=Object.keys(r).find(t=>t.startsWith("__reactFiber")||t.startsWith("__reactInternalInstance"));if(!o)continue;let t=r[o],n=0;while(t&&n++<50){if(t.memoizedProps?.store?.getState){window.__EXPOSED_REDUX_STORE__=t.memoizedProps.store;console.log(" Redux store exposed");return}if(t.stateNode?.store?.getState){window.__EXPOSED_REDUX_STORE__=t.stateNode.store;console.log(" Redux store exposed");return}t=t.return}}console.warn("L Could not find Redux store");console.info("=¡ Fallback: Use parse-redux-logs.py")})();

Usage example:
  echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"<PASTE_MINIFIED_LINE_HERE>","returnByValue":false}}' | websocat -n1 "$WS_URL"
*/
