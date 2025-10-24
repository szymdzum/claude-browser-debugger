"""
Unit tests for CDPSession and Target classes.

Tests User Story 3: Unified CLI Interface - Target Discovery
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from scripts.cdp.session import CDPSession, Target
from scripts.cdp.exceptions import CDPError, CDPTargetNotFoundError


@pytest.fixture
def mock_targets_response():
    """Mock Chrome /json endpoint response."""
    return [
        {
            "id": "page-1",
            "type": "page",
            "title": "Example Domain",
            "url": "https://example.com",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/page-1",
            "description": "",
            "devtoolsFrontendUrl": "/devtools/inspector.html?ws=localhost:9222/devtools/page/page-1",
            "faviconUrl": "https://example.com/favicon.ico"
        },
        {
            "id": "page-2",
            "type": "page",
            "title": "GitHub",
            "url": "https://github.com",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/page-2",
            "description": "",
            "devtoolsFrontendUrl": "/devtools/inspector.html?ws=localhost:9222/devtools/page/page-2",
            "faviconUrl": "https://github.com/favicon.ico"
        },
        {
            "id": "worker-1",
            "type": "service_worker",
            "title": "Service Worker",
            "url": "https://example.com/sw.js",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/worker-1",
            "description": "",
            "devtoolsFrontendUrl": "",
            "faviconUrl": ""
        }
    ]


def test_target_initialization():
    """Test Target object initialization from raw data."""
    target_data = {
        "id": "test-id",
        "type": "page",
        "title": "Test Page",
        "url": "https://test.com",
        "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/test-id",
        "description": "Test description",
        "devtoolsFrontendUrl": "/devtools/inspector.html",
        "faviconUrl": "https://test.com/favicon.ico"
    }

    target = Target(target_data)

    assert target.id == "test-id"
    assert target.type == "page"
    assert target.title == "Test Page"
    assert target.url == "https://test.com"
    assert target.webSocketDebuggerUrl == "ws://localhost:9222/devtools/page/test-id"
    assert target.description == "Test description"
    assert target.devtoolsFrontendUrl == "/devtools/inspector.html"
    assert target.faviconUrl == "https://test.com/favicon.ico"


def test_target_to_dict():
    """Test Target to_dict conversion."""
    target_data = {
        "id": "test-id",
        "type": "page",
        "title": "Test Page",
        "url": "https://test.com",
        "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/test-id"
    }

    target = Target(target_data)
    result = target.to_dict()

    assert result["id"] == "test-id"
    assert result["type"] == "page"
    assert result["title"] == "Test Page"
    assert result["url"] == "https://test.com"
    assert result["webSocketDebuggerUrl"] == "ws://localhost:9222/devtools/page/test-id"


def test_cdp_session_initialization():
    """Test CDPSession initialization with defaults."""
    session = CDPSession()

    assert session.chrome_host == "localhost"
    assert session.chrome_port == 9222
    assert session.timeout == 5.0


def test_cdp_session_custom_port():
    """Test CDPSession with custom port."""
    session = CDPSession(chrome_host="127.0.0.1", chrome_port=9223, timeout=10.0)

    assert session.chrome_host == "127.0.0.1"
    assert session.chrome_port == 9223
    assert session.timeout == 10.0


def test_cdp_session_invalid_port():
    """Test CDPSession raises ValueError for invalid port."""
    with pytest.raises(ValueError, match="chrome_port must be 1-65535"):
        CDPSession(chrome_port=0)

    with pytest.raises(ValueError, match="chrome_port must be 1-65535"):
        CDPSession(chrome_port=65536)


def test_list_targets_success(mock_targets_response):
    """
    T046: Test successful target listing from HTTP endpoint.

    Verifies CDPSession.list_targets() fetches and parses targets correctly.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
        targets = session.list_targets()

        # Verify HTTP endpoint was called
        mock_urlopen.assert_called_once()
        args, kwargs = mock_urlopen.call_args
        assert args[0] == "http://localhost:9222/json"
        assert kwargs['timeout'] == 5.0

        # Verify targets were parsed
        assert len(targets) == 3
        assert all(isinstance(t, Target) for t in targets)
        assert targets[0].id == "page-1"
        assert targets[1].id == "page-2"
        assert targets[2].id == "worker-1"


def test_list_targets_with_type_filter(mock_targets_response):
    """
    T046: Test target type filtering.

    Verifies CDPSession.list_targets(target_type="page") filters correctly.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        # Filter by page type
        page_targets = session.list_targets(target_type="page")
        assert len(page_targets) == 2
        assert all(t.type == "page" for t in page_targets)

        # Filter by service_worker type
        worker_targets = session.list_targets(target_type="service_worker")
        assert len(worker_targets) == 1
        assert worker_targets[0].type == "service_worker"


def test_list_targets_with_url_filter(mock_targets_response):
    """
    T046: Test URL pattern filtering.

    Verifies CDPSession.list_targets(url_pattern="github") filters correctly.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        # Filter by URL substring (case-insensitive)
        github_targets = session.list_targets(url_pattern="github")
        assert len(github_targets) == 1
        assert "github" in github_targets[0].url.lower()

        # Filter by URL substring (multiple matches)
        example_targets = session.list_targets(url_pattern="example")
        assert len(example_targets) == 2
        assert all("example" in t.url.lower() for t in example_targets)


def test_list_targets_combined_filters(mock_targets_response):
    """
    T046: Test combined type and URL filtering.

    Verifies both filters work together correctly.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        # Filter by type and URL
        targets = session.list_targets(target_type="page", url_pattern="example")
        assert len(targets) == 1
        assert targets[0].type == "page"
        assert "example" in targets[0].url.lower()


def test_list_targets_connection_error():
    """
    T046: Test error handling for unreachable Chrome endpoint.

    Verifies CDPSession.list_targets() raises CDPError on connection failure.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen to raise URLError
    import urllib.error
    with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(CDPError, match="Failed to connect to Chrome"):
            session.list_targets()


def test_list_targets_invalid_json():
    """
    T046: Test error handling for invalid JSON response.

    Verifies CDPSession.list_targets() raises CDPError on malformed response.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen to return invalid JSON
    mock_response = Mock()
    mock_response.read.return_value = b"NOT VALID JSON"
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        with pytest.raises(CDPError, match="Invalid JSON response"):
            session.list_targets()


def test_get_target_by_id(mock_targets_response):
    """
    T046: Test get_target_by_id() method.

    Verifies CDPSession.get_target_by_id() finds correct target.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        # Find existing target
        target = session.get_target_by_id("page-1")
        assert target is not None
        assert target.id == "page-1"
        assert target.url == "https://example.com"

        # Find non-existent target
        target = session.get_target_by_id("nonexistent")
        assert target is None


@pytest.mark.asyncio
async def test_connect_to_target():
    """
    T046: Test connect_to_target() method.

    Verifies CDPSession.connect_to_target() creates CDPConnection.
    """
    session = CDPSession()

    target_data = {
        "id": "test-id",
        "type": "page",
        "title": "Test",
        "url": "https://test.com",
        "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/test-id"
    }
    target = Target(target_data)

    # Connect to target
    conn = await session.connect_to_target(target)

    # Verify CDPConnection was created with correct WebSocket URL
    assert conn.ws_url == "ws://localhost:9222/devtools/page/test-id"


@pytest.mark.asyncio
async def test_connect_to_target_no_ws_url():
    """
    T046: Test connect_to_target() raises error for target without WebSocket URL.

    Verifies CDPSession.connect_to_target() validates WebSocket URL.
    """
    session = CDPSession()

    target_data = {
        "id": "test-id",
        "type": "page",
        "title": "Test",
        "url": "https://test.com",
        "webSocketDebuggerUrl": ""  # Empty WebSocket URL
    }
    target = Target(target_data)

    # Should raise CDPError
    with pytest.raises(CDPError, match="no WebSocket debugger URL"):
        await session.connect_to_target(target)


@pytest.mark.asyncio
async def test_connect_to_first_page(mock_targets_response):
    """
    T046: Test connect_to_first_page() convenience method.

    Verifies CDPSession.connect_to_first_page() finds and connects to first page.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen
    mock_response = Mock()
    mock_response.read.return_value = json.dumps(mock_targets_response).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        conn = await session.connect_to_first_page()

        # Verify connected to first page target
        assert conn.ws_url == "ws://localhost:9222/devtools/page/page-1"


@pytest.mark.asyncio
async def test_connect_to_first_page_no_pages():
    """
    T046: Test connect_to_first_page() raises error when no pages found.

    Verifies CDPSession.connect_to_first_page() raises CDPTargetNotFoundError.
    """
    session = CDPSession()

    # Mock urllib.request.urlopen with no page targets
    mock_response = Mock()
    mock_response.read.return_value = json.dumps([]).encode()
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch('urllib.request.urlopen', return_value=mock_response):
        with pytest.raises(CDPTargetNotFoundError, match="No page targets found"):
            await session.connect_to_first_page()
