"""
HTML normalization for migration safety testing.

Normalizes HTML for comparison between Bash and Python implementations (T068).
Handles attribute sorting, whitespace normalization, and consistent formatting.
"""

import re
from html.parser import HTMLParser
from io import StringIO


def normalize_html(html: str) -> str:
    """
    Normalize HTML for consistent comparison.

    Performs:
    - Lowercase tag names
    - Sort attributes alphabetically
    - Strip insignificant whitespace
    - Remove comments
    - Consistent quote style (double quotes)
    - Normalize empty elements

    Args:
        html: Raw HTML string

    Returns:
        Normalized HTML string
    """
    normalizer = HTMLNormalizer()
    normalizer.feed(html)
    return normalizer.get_output()


def normalize_attributes(attrs_str: str) -> str:
    """
    Normalize HTML attribute string.

    Args:
        attrs_str: Attribute string (e.g., 'class="test" id="foo"')

    Returns:
        Sorted and normalized attribute string
    """
    # Parse attributes into list of (name, value) tuples
    attr_pattern = r'(\w+(?:-\w+)*)=(["\'])([^"\']*)\2'
    attrs = re.findall(attr_pattern, attrs_str)

    # Sort by attribute name
    attrs_sorted = sorted(attrs, key=lambda x: x[0])

    # Rebuild with consistent formatting (double quotes, single space)
    return " ".join(f'{name}="{value}"' for name, _, value in attrs_sorted)


def strip_insignificant_whitespace(html: str) -> str:
    """
    Strip insignificant whitespace from HTML.

    Preserves whitespace in <pre>, <script>, <style> tags.

    Args:
        html: HTML string

    Returns:
        HTML with insignificant whitespace removed
    """
    # Remove leading/trailing whitespace
    html = html.strip()

    # Collapse multiple spaces in text nodes (outside of <pre>)
    # This is a simplified implementation - full implementation would parse properly
    html = re.sub(r'>(\s+)<', '><', html)  # Remove whitespace between tags
    html = re.sub(r'\s+', ' ', html)  # Collapse multiple spaces to single

    return html


class HTMLNormalizer(HTMLParser):
    """HTML parser that normalizes HTML structure."""

    def __init__(self):
        super().__init__()
        self.output = StringIO()
        self.preserve_whitespace_stack = []  # Track tags that preserve whitespace

    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        # Convert to lowercase
        tag = tag.lower()

        # Check if this tag preserves whitespace
        if tag in ('pre', 'script', 'style', 'textarea'):
            self.preserve_whitespace_stack.append(tag)

        # Sort attributes and handle boolean attributes
        attrs_sorted = sorted(attrs, key=lambda x: x[0])

        # Build tag
        if attrs_sorted:
            # Handle boolean attributes (value is None) and regular attributes
            attrs_parts = []
            for name, value in attrs_sorted:
                if value is None or value == '' or value == name:
                    # Boolean attribute - output without value
                    attrs_parts.append(name)
                else:
                    attrs_parts.append(f'{name}="{value}"')
            attrs_str = " ".join(attrs_parts)
            self.output.write(f'<{tag} {attrs_str}>')
        else:
            self.output.write(f'<{tag}>')

    def handle_endtag(self, tag):
        """Handle closing tags."""
        tag = tag.lower()

        # Pop from preserve whitespace stack if needed
        if self.preserve_whitespace_stack and self.preserve_whitespace_stack[-1] == tag:
            self.preserve_whitespace_stack.pop()

        self.output.write(f'</{tag}>')

    def handle_data(self, data):
        """Handle text content."""
        # If we're in a whitespace-preserving tag, keep exact whitespace including newlines
        if self.preserve_whitespace_stack:
            # Preserve all whitespace including newlines in <pre>, <script>, etc.
            self.output.write(data)
        else:
            # Normalize whitespace (collapse to single space, strip leading/trailing)
            # This preserves the text content but removes extra whitespace
            normalized = re.sub(r'\s+', ' ', data).strip()
            if normalized:
                self.output.write(normalized)

    def handle_comment(self, data):
        """Handle comments - remove them."""
        pass  # Don't output comments

    def handle_startendtag(self, tag, attrs):
        """Handle self-closing tags - normalize to non-self-closing format."""
        tag = tag.lower()

        # For consistency, handle self-closing tags as regular tags
        # This makes <img src="x" /> equivalent to <img src="x">
        attrs_sorted = sorted(attrs, key=lambda x: x[0])

        # Build tag (non-self-closing format for consistency)
        if attrs_sorted:
            attrs_parts = []
            for name, value in attrs_sorted:
                if value is None or value == '' or value == name:
                    attrs_parts.append(name)
                else:
                    attrs_parts.append(f'{name}="{value}"')
            attrs_str = " ".join(attrs_parts)
            self.output.write(f'<{tag} {attrs_str}>')
        else:
            self.output.write(f'<{tag}>')

    def get_output(self) -> str:
        """Get normalized HTML output."""
        return self.output.getvalue()


if __name__ == "__main__":
    # CLI interface for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 normalize_html.py <input.html>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        html = f.read()

    print(normalize_html(html))
