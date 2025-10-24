"""
Unit tests for HTML normalization (T073).

Tests User Story 5: Migration Safety - HTML Normalization for comparison.
"""

import pytest
from tests.ci.normalize_html import normalize_html, normalize_attributes, strip_insignificant_whitespace


class TestHTMLNormalization:
    """T073: Test HTML normalization for migration safety."""

    def test_normalize_attributes_sorting(self):
        """Verify attributes are sorted alphabetically."""
        html = '<div class="foo" id="bar" data-test="baz"></div>'
        expected = '<div class="foo" data-test="baz" id="bar"></div>'

        result = normalize_html(html)
        assert result == expected

    def test_strip_whitespace_between_tags(self):
        """Verify insignificant whitespace between tags is removed."""
        html = """
        <html>
            <body>
                <div>  Content  </div>
            </body>
        </html>
        """
        result = normalize_html(html)

        # Should remove whitespace between tags but preserve content
        assert "  Content  " not in result  # Internal whitespace should be normalized
        assert "<html><body><div>Content</div></body></html>" == result

    def test_normalize_empty_elements(self):
        """Verify empty elements are consistently formatted."""
        html1 = '<img src="test.png" />'
        html2 = '<img src="test.png">'

        result1 = normalize_html(html1)
        result2 = normalize_html(html2)

        # Both should normalize to same format
        assert result1 == result2

    def test_normalize_case_insensitive_tags(self):
        """Verify HTML tags are normalized to lowercase."""
        html = '<DIV CLASS="test"><P>Content</P></DIV>'
        expected = '<div class="test"><p>Content</p></div>'

        result = normalize_html(html)
        assert result == expected

    def test_normalize_attribute_value_quotes(self):
        """Verify attribute values use consistent quoting."""
        html1 = '<div class="test" id=\'foo\'></div>'
        html2 = '<div class="test" id="foo"></div>'

        result1 = normalize_html(html1)
        result2 = normalize_html(html2)

        # Both should use double quotes
        assert result1 == result2
        assert 'id="foo"' in result1

    def test_preserve_significant_whitespace(self):
        """Verify significant whitespace in text nodes is preserved."""
        html = '<pre>  Preserve   spacing  </pre>'
        result = normalize_html(html)

        # Whitespace in <pre> should be preserved
        assert "  Preserve   spacing  " in result

    def test_normalize_boolean_attributes(self):
        """Verify boolean attributes are consistently formatted."""
        html1 = '<input disabled />'
        html2 = '<input disabled="" />'
        html3 = '<input disabled="disabled" />'

        result1 = normalize_html(html1)
        result2 = normalize_html(html2)
        result3 = normalize_html(html3)

        # All should normalize to same format (disabled without value)
        assert result1 == result2 == result3

    def test_remove_comments(self):
        """Verify HTML comments are removed."""
        html = '<div><!-- Comment --><p>Content</p></div>'
        expected = '<div><p>Content</p></div>'

        result = normalize_html(html)
        assert result == expected
        assert "<!--" not in result

    def test_normalize_complex_document(self):
        """Verify normalization of complex HTML document."""
        html = """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <title>Test Page</title>
            </head>
            <body class="main" id="body">
                <div data-test="foo" class="container">
                    <h1>Title</h1>
                    <p>Paragraph</p>
                </div>
            </body>
        </html>
        """

        result = normalize_html(html)

        # Should have sorted attributes
        assert 'class="main" id="body"' in result
        assert 'class="container" data-test="foo"' in result

        # Should remove whitespace between tags
        assert "    " not in result

        # Should preserve structure
        assert "<h1>Title</h1>" in result
        assert "<p>Paragraph</p>" in result


class TestAttributeNormalization:
    """Test attribute-specific normalization."""

    def test_sort_attributes_alphabetically(self):
        """Verify attributes are sorted in alphabetical order."""
        attrs = 'z="last" a="first" m="middle"'
        result = normalize_attributes(attrs)

        # Should be in alphabetical order
        assert result.index('a="first"') < result.index('m="middle"')
        assert result.index('m="middle"') < result.index('z="last"')

    def test_normalize_attribute_spacing(self):
        """Verify consistent spacing between attributes."""
        attrs = 'class="test"   id="foo"    data-val="bar"'
        result = normalize_attributes(attrs)

        # Should have single space between attributes
        assert "   " not in result
        assert result == 'class="test" data-val="bar" id="foo"'


class TestWhitespaceNormalization:
    """Test whitespace-specific normalization."""

    def test_strip_leading_trailing_whitespace(self):
        """Verify leading/trailing whitespace is removed."""
        html = "   <div>Content</div>   "
        result = strip_insignificant_whitespace(html)

        assert result == "<div>Content</div>"

    def test_collapse_multiple_spaces(self):
        """Verify multiple spaces collapse to single space."""
        html = "<div>Multiple    spaces    here</div>"
        result = strip_insignificant_whitespace(html)

        assert result == "<div>Multiple spaces here</div>"

    def test_preserve_whitespace_in_pre_tags(self):
        """Verify whitespace is preserved in <pre> tags."""
        html = "<pre>  Line 1\n  Line 2\n</pre>"
        result = normalize_html(html)  # Use normalize_html, not strip_insignificant_whitespace

        # Should preserve exact whitespace in <pre>
        assert "  Line 1\n  Line 2\n" in result
