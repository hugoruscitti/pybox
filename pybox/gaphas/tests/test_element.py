from os import getenv

import unittest

from gaphas.canvas import Canvas
from gaphas.examples import Box

from gaphas.item import NW, NE, SE, SW

class ElementTestCase(unittest.TestCase):

    def test_resize_se(self):
        """
        Test resizing of element by dragging it SE handle.
        """
        canvas = Canvas()
        box = Box()
        handles = box.handles()

        canvas.add(box)

        h_nw, h_ne, h_se, h_sw = handles
        assert h_nw is handles[NW]
        assert h_ne is handles[NE]
        assert h_sw is handles[SW]
        assert h_se is handles[SE]

        # to see how many solver was called:
        # GAPHAS_TEST_COUNT=3 nosetests -s --with-prof --profile-restrict=gaphas gaphas/tests/test_element.py | grep -e '\<solve\>' -e dirty

        count = getenv('GAPHAS_TEST_COUNT')
        if count:
            count = int(count)
        else:
            count = 1

        for i in range(count):
            h_se.x += 100      # h.se.{x,y} = 10, now
            h_se.y += 100
            box.request_update()
            canvas.update()

        self.assertEquals(110 * count, h_se.x) # h_se changed above, should remain the same
        self.assertEquals(110 * count, float(h_se.y))

        self.assertEquals(110 * count, float(h_ne.x))
        self.assertEquals(110 * count, float(h_sw.y))


    def test_minimal_se(self):
        """
        Test resizing of element by dragging it SE handle.
        """
        canvas = Canvas()
        box = Box()
        handles = box.handles()

        canvas.add(box)

        h_nw, h_ne, h_se, h_sw = handles
        assert h_nw is handles[NW]
        assert h_ne is handles[NE]
        assert h_sw is handles[SW]
        assert h_se is handles[SE]

        h_se.x -= 20      # h.se.{x,y} == -10
        h_se.y -= 20
        assert h_se.x == h_se.y == -10

        box.request_update()
        canvas.update()

        self.assertEquals(10, h_se.x) # h_se changed above, should be 10
        self.assertEquals(10, h_se.y)

        self.assertEquals(10, h_ne.x)
        self.assertEquals(10, h_sw.y)
