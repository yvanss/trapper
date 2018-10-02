# -*- coding: utf-8 -*-

from trapper.apps.common.utils.test_tools import ExtendedTestCase
from trapper.apps.common.tools import parse_pks, clean_html


class ParsePksTestCase(ExtendedTestCase):
    """Test case for method that is used to convert in most cases
    request.POST param `pks` that is used later to retrieve values
    from database"""

    def test_invalid_type(self):
        """`parse_pks` can handle invalid types by returning empty list"""
        self.assertEqual(parse_pks(None), [])
        self.assertEqual(parse_pks([]), [])
        self.assertEqual(parse_pks(()), [])
        self.assertEqual(parse_pks(b'test'), [])

    def test_empty(self):
        """`parse_pks` can handle empty string by returning empty list"""
        self.assertEqual(parse_pks(''), [])
        self.assertEqual(parse_pks(u''), [])

    def test_invalid_separator(self):
        """`parse_pks` can handle invalid separator by returning empty list"""
        self.assertEqual(parse_pks('1:2'), [])
        self.assertEqual(parse_pks('1;2'), [])

    def test_invalid_items(self):
        """`parse_pks` strip non-int values"""
        self.assertItemsEqual(parse_pks('1,2,a,b'), [1, 2])
        self.assertItemsEqual(parse_pks('a,b,1,2'), [1, 2])
        self.assertItemsEqual(parse_pks('1,a,b,2'), [1, 2])
        self.assertItemsEqual(parse_pks('a,1,b,2'), [1, 2])
        self.assertEqual(parse_pks('a,b'), [])

    def test_items(self):
        """`parse_pks` will retrun in list all values that are integers.
        Extra spaces are allowed
        """
        self.assertItemsEqual(parse_pks('1'), [1])
        self.assertItemsEqual(parse_pks('1,2'), [1, 2])
        self.assertItemsEqual(parse_pks('1, 2, 3,'), [1, 2, 3])
        self.assertItemsEqual(parse_pks('-1, 1'), [-1, 1])
        self.assertItemsEqual(parse_pks('1, 1'), [1, 1])


class CleanHtmlTestCase(ExtendedTestCase):
    """Tests related to function that is used in `SafeTextField` to
    ensure safety of data stored in field"""

    def test_clean(self):
        """Potentialy dangerous code is stripped off"""
        self.assertEqual(clean_html(''), '')
        self.assertEqual(clean_html('<p></p>'), '')
        self.assertEqual(clean_html('<p>text</p>'), 'text')
        self.assertEqual(clean_html('<p style="text-align: right;"></p>'), '')
        self.assertEqual(
            clean_html('<p style="text-align: right;">text</p>'), 'text'
        )
        self.assertEqual(
            clean_html('<script type="text/javascript">alert("a";);</script>'),
            '<div></div>'
        )
        self.assertEqual(
            clean_html('<p><strong>text</strong></p>'), '<strong>text</strong>'
        )
        self.assertEqual(
            clean_html('<p><strong style="color: red;">text</strong></p>'),
            '<strong>text</strong>'
        )
