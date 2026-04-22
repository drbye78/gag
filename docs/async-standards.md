# Async/Sync Interface Standards

This document defines the standard patterns for handling async and sync code in the Engineering Intelligence System.

## Standard Patterns

### Pattern 1: Async-First with Sync Wrapper (Preferred)

When a function may be called from both async and sync contexts, provide async as primary:

```python
import asyncio
from typing import List, Dict, Any

async def fetch_data_async(query: str) -> List[Dict[str, Any]]:
    """Fetch data from source (async context)."""
    # Async implementation
    ...

def fetch_data(query: str) -> List[Dict[str, Any]]:
    """Sync wrapper for fetch_data_async.
    
    Use when calling from sync code or when async context is unavailable.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fetch_data_async(query))
    else:
        return loop.run_until_complete(fetch_data_async(query))
```

### Pattern 2: Async-Only (When Not Needed Sync)

For internal async code that is never called from sync context:

```python
async def process_stream(items: AsyncIterator[Item]) -> List[Result]:
    """Process async stream of items."""
    results = []
    async for item in items:
        results.append(await process_item(item))
    return results
```

### Pattern 3: Sync-Only (For Simple Functions)

For simple functions with no I/O or CPU-bound work:

```python
def calculate_score(features: Dict[str, float]) -> float:
    """Calculate relevance score (CPU-bound, no I/O)."""
    return sum(f * w for f, w in zip(features.values(), WEIGHTS))
```

## Anti-Patterns to Avoid

### ❌ Mixed Callback/Sync

```python
# BAD - unclear contract
def process(data, callback=None):
    if callback:
        asyncio.create_task(process_async(data, callback))
    else:
        return sync_process(data)
```

### ❌ asyncio.run() in Hot Path

```python
# BAD - creates new event loop each time
def handle_request(req):
    return asyncio.run(process_request(req))
```

## Migration Guide

For existing code using anti-patterns:

1. Identify the primary use case (async or sync)
2. Implement that version as primary
3. Add wrapper if other mode needed
4. Update callers gradually

## Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_data():
    result = await fetch_data_async("test query")
    assert len(result) > 0
```
