"""
This module contains everything to display a Canvas on a screen.
"""

__version__ = "$Revision: 2173 $"
# $HeadURL: http://svn.devjavu.com/gaphor/gaphas/tags/gaphas-0.3.6/gaphas/view.py $

import gobject
import gtk
from cairo import Matrix
from canvas import Context
from geometry import Rectangle
from quadtree import Quadtree
from tool import ToolContext, DefaultTool
from painter import DefaultPainter, BoundingBoxPainter
from decorators import async, PRIORITY_HIGH_IDLE
from decorators import nonrecursive
from gaphas.sorter import Sorted

# Handy debug flag for drawing bounding boxes around the items.
DEBUG_DRAW_BOUNDING_BOX = False
DEBUG_DRAW_QUADTREE = False

# The default cursor (in case of a cursor reset)
DEFAULT_CURSOR = gtk.gdk.LEFT_PTR


class View(object):
    """
    View class for gaphas.Canvas objects. 
    """

    def __init__(self, canvas=None):
        self._matrix = Matrix()
        self._painter = DefaultPainter()

        # Handling selections.
        self._selected_items = Sorted(canvas)
        self._focused_item = None
        self._hovered_item = None
        self._dropzone_item = None

        self._qtree = Quadtree()

        self._canvas = None
        if canvas:
            self._set_canvas(canvas)


    matrix = property(lambda s: s._matrix,
                      doc="Canvas to view transformation matrix")


    def _set_canvas(self, canvas):
        """
        Use view.canvas = my_canvas to set the canvas to be rendered
        in the view.
        """
        if self._canvas:
            self._qtree = Quadtree()

        self._canvas = canvas
        self._selected_items.canvas = canvas
        

    canvas = property(lambda s: s._canvas, _set_canvas)


    def emit(self, args, **kwargs):
        """
        Placeholder method for signal emission functionality.
        """
        pass


    def select_item(self, item):
        """
        Select an item. This adds @item to the set of selected items. Do::

            del view.selected_items

        to clear the selected items list.
        """
        self.queue_draw_item(item)
        if item not in self._selected_items:
            self._selected_items.add(item)
            self.emit('selection-changed', self._selected_items)


    def unselect_item(self, item):
        """
        Unselect an item.
        """
        self.queue_draw_item(item)
        if item in self._selected_items:
            self._selected_items.discard(item)
            self.emit('selection-changed', self._selected_items)


    def select_all(self):
        for item in self.canvas.get_all_items():
            self.select_item(item)


    def unselect_all(self):
        """
        Clearing the selected_item also clears the focused_item.
        """
        self.queue_draw_item(*self._selected_items)
        self._selected_items.clear()
        self.focused_item = None
        self.emit('selection-changed', self._selected_items)


    selected_items = property(lambda s: s._selected_items,
                              select_item, unselect_all,
                              "Items selected by the view")


    def _set_focused_item(self, item):
        """
        Set the focused item, this item is also added to the selected_items
        set.
        """
        if not item is self._focused_item:
            self.queue_draw_item(self._focused_item, item)

        if item:
            self.selected_items = item #.add(item)
        if item is not self._focused_item:
            self._focused_item = item
            self.emit('focus-changed', item)


    def _del_focused_item(self):
        """
        Items that loose focus remain selected.
        """
        self.focused_item = None
        

    focused_item = property(lambda s: s._focused_item,
                            _set_focused_item, _del_focused_item,
                            "The item with focus (receives key events a.o.)")


    def _set_hovered_item(self, item):
        """
        Set the hovered item.
        """
        if not item is self._hovered_item:
            self.queue_draw_item(self._hovered_item, item)
        if item is not self._hovered_item:
            self._hovered_item = item
            self.emit('hover-changed', item)


    def _del_hovered_item(self):
        """
        Unset the hovered item.
        """
        self.hovered_item = None
        

    hovered_item = property(lambda s: s._hovered_item,
                            _set_hovered_item, _del_hovered_item,
                            "The item directly under the mouse pointer")


    def _set_dropzone_item(self, item):
        """
        Set dropzone item.
        """
        if item is not self._dropzone_item:
            self.queue_draw_item(self._dropzone_item, item)
            self._dropzone_item = item
            self.emit('dropzone-changed', item)


    def _del_dropzone_item(self):
        """
        Unset dropzone item.
        """
        self._dropzone_item = None


    dropzone_item = property(lambda s: s._dropzone_item,
            _set_dropzone_item, _del_dropzone_item,
            'The item which can group other items')


    def _set_painter(self, painter):
        """
        Set the painter to use. Painters should implement painter.Painter.
        """
        self._painter = painter
        self.emit('painter-changed')


    painter = property(lambda s: s._painter, _set_painter)


    def get_item_at_point(self, x, y, selected=True):
        """
        Return the topmost item located at (x, y).

        Parameters:
         - selected: if False returns first non-selected item
        """
        point = (x, y)
        items = self._qtree.find_intersect((x, y, 1, 1))
        for item in self._canvas.sorter.sort(items, reverse=True):
            if not selected and item in self.selected_items:
                continue  # skip selected items

            v2i = self.get_matrix_v2i(item)
            ix, iy = v2i.transform_point(x, y)
            if item.point(ix, iy) < 0.5:
                return item
        return None


    def get_items_in_rectangle(self, rect, intersect=True, reverse=False):
        """
        Return the items in the rectangle 'rect'.
        Items are automatically sorted in canvas' processing order.
        """
        if intersect:
            items = self._qtree.find_intersect(rect)
        else:
            items = self._qtree.find_inside(rect)
        return self._canvas.sorter.sort(items, reverse=reverse)


    def select_in_rectangle(self, rect):
        """
        Select all items who have their bounding box within the
        rectangle @rect.
        """
        items = self._qtree.find_inside(rect)
        map(self.select_item, items)


    def zoom(self, factor):
        """
        Zoom in/out by factor @factor.
        """
        self._matrix.scale(factor, factor)

        # Make sure everything's updated
        map(self.update_matrix, self._canvas.get_all_items())
        self.request_update(self._canvas.get_all_items())


    def set_item_bounding_box(self, item, bounds):
        """
        Update the bounding box of the item (in canvas coordinates).

        Coordinates are calculated back to item coordinates, so matrix-only
        updates can occur.
        """
        v2i = self.get_matrix_v2i(item).transform_point
        ix0, iy0 = v2i(bounds.x, bounds.y)
        ix1, iy1 = v2i(bounds.x1, bounds.y1)
        self._qtree.add(item=item, bounds=bounds, data=Rectangle(ix0, iy0, x1=ix1, y1=iy1))


    def get_item_bounding_box(self, item):
        """
        Get the bounding box for the item, in canvas coordinates.
        """
        return self._qtree.get_bounds(item)


    bounding_box = property(lambda s: Rectangle(*s._qtree.soft_bounds))


    def update_bounding_box(self, cr, items=None):
        """
        Update the bounding boxes of the canvas items for this view, in 
        canvas coordinates.
        """
        painter = BoundingBoxPainter()
        if items is None:
            items = self.canvas.get_all_items()

        # The painter calls set_item_bounding_box() for each rendered item.
        painter.paint(Context(view=self,
                              cairo=cr,
                              items=items))

        # Update the view's bounding box with the rest of the items
        self._bounds = Rectangle(*self._qtree.soft_bounds)


    def paint(self, cr):
        self._painter.paint(Context(view=self,
                                    cairo=cr,
                                    items=self.canvas.get_all_items(),
                                    area=None))


    def get_matrix_i2v(self, item):
        """
        Get Item to View matrix for ``item``.
        """
        if self not in item._matrix_i2v:
            self.update_matrix(item)
        return item._matrix_i2v[self]


    def get_matrix_v2i(self, item):
        """
        Get View to Item matrix for ``item``.
        """
        if self not in item._matrix_v2i:
            self.update_matrix(item)
        return item._matrix_v2i[self]


    def update_matrix(self, item):
        """
        Update item matrices related to view.
        """
        i2v = item._matrix_i2c * self._matrix
        item._matrix_i2v[self] = i2v

        v2i = Matrix(*i2v)
        v2i.invert()
        item._matrix_v2i[self] = v2i

    def _clear_matrices(self):
        """
        Clear registered data in Item's _matrix{i2c|v2i} attributes.
        """
        for item in self.canvas.get_all_items():
            try:
                del item._matrix_i2v[self]
                del item._matrix_v2i[self]
            except KeyError:
                pass


# Map GDK events to tool methods
EVENT_HANDLERS = {
    gtk.gdk.BUTTON_PRESS: 'on_button_press',
    gtk.gdk.BUTTON_RELEASE: 'on_button_release',
    gtk.gdk._2BUTTON_PRESS: 'on_double_click',
    gtk.gdk._3BUTTON_PRESS: 'on_triple_click',
    gtk.gdk.MOTION_NOTIFY: 'on_motion_notify',
    gtk.gdk.KEY_PRESS: 'on_key_press',
    gtk.gdk.KEY_RELEASE: 'on_key_release'
}



class GtkView(gtk.DrawingArea, View):
    # NOTE: Inherit from GTK+ class first, otherwise BusErrors may occur!
    """
    GTK+ widget for rendering a canvas.Canvas to a screen.
    The view uses Tools from `tool.py` to handle events and Painters
    from `painter.py` to draw. Both are configurable.

    The widget already contains adjustment objects (`hadjustment`,
    `vadjustment`) to be used for scrollbars.

    This view registers itself on the canvas, so it will receive update events.
    """

    # Just defined a name to make GTK register this class.
    __gtype_name__ = 'GaphasView'
    
    # Signals: emited after the change takes effect.
    __gsignals__ = {
        'dropzone-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,)),
        'hover-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,)),
        'focus-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,)),
        'selection-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,)),
        'tool-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      ()),
        'painter-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      ())
    }


    def __init__(self, canvas=None):
        gtk.DrawingArea.__init__(self)

        self._dirty_items = set()
        self._dirty_matrix_items = set()

        View.__init__(self, canvas)

        self.set_flags(gtk.CAN_FOCUS)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK
                        | gtk.gdk.POINTER_MOTION_MASK
                        | gtk.gdk.KEY_PRESS_MASK
                        | gtk.gdk.KEY_RELEASE_MASK)

        self._hadjustment = gtk.Adjustment()
        self._vadjustment = gtk.Adjustment()
        self._hadjustment.connect('value-changed', self.on_adjustment_changed)
        self._vadjustment.connect('value-changed', self.on_adjustment_changed)

        self._tool = DefaultTool()
        
        # TODO: add some "tool" to do some low priority event post-processing
        #    This way we can add features like element alignment in a fairly
        #    non-intrusive way. Add a few methods that allow tools to mark
        #    item/handle pairs for post-processing.
        #    maybe adding it to the tool context would be enough (?).

        # Set background to white.
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFF'))


    def emit(self, *args, **kwargs):
        """
        Delegate signal emissions to the DrawingArea (=GTK+)
        """
        gtk.DrawingArea.emit(self, *args, **kwargs)


    def _set_canvas(self, canvas):
        """
        Use view.canvas = my_canvas to set the canvas to be rendered
        in the view.
        This extends the behaviour of View.canvas.
        The view is also registered.
        """
        if self._canvas:
            self._clear_matrices()
            self._canvas.unregister_view(self)

        super(GtkView, self)._set_canvas(canvas)
        
        if self._canvas:
            self._canvas.register_view(self)
            self.request_update(self._canvas.get_all_items())


    canvas = property(lambda s: s._canvas, _set_canvas)


    def _set_tool(self, tool):
        """
        Set the tool to use. Tools should implement tool.Tool.
        """
        self._tool = tool
        self.emit('tool-changed')


    tool = property(lambda s: s._tool, _set_tool)


    hadjustment = property(lambda s: s._hadjustment)


    vadjustment = property(lambda s: s._vadjustment)


    def zoom(self, factor):
        """
        Zoom in/out by factor ``factor``.
        """
        super(GtkView, self).zoom(factor)
        self.queue_draw_refresh()


    def _update_adjustment(self, adjustment, value, canvas_size, canvas_offset, viewport_size):
        """
        >>> v = GtkView()
        >>> a = gtk.Adjustment()
        >>> v._hadjustment = a
        >>> v._update_adjustment(a, 10, 100, 0, 20)
        >>> a.page_size, a.page_increment, a.value
        (20.0, 20.0, 0.0)
        """
        #canvas_size += viewport_size
        #canvas_offset -= viewport_size
        if viewport_size != adjustment.page_size or canvas_size != adjustment.upper:
            adjustment.page_size = viewport_size
            adjustment.page_increment = viewport_size
            adjustment.step_increment = viewport_size/10
            adjustment.upper = adjustment.value + canvas_offset + canvas_size
            adjustment.lower = adjustment.value + canvas_offset
        
        if adjustment.value > adjustment.upper - viewport_size:
            adjustment.value = adjustment.upper - viewport_size

    @async(single=True)
    def update_adjustments(self, allocation=None):
        """
        Update the allocation objects (for scrollbars).
        """
        if not allocation:
            allocation = self.allocation

        # Define a minimal view size:
        aw, ah = allocation.width, allocation.height 
        x, y, w, h = self.bounding_box + (self.matrix.transform_point(0, 0) + (aw * 2, ah * 2))
        self._update_adjustment(self._hadjustment,
                                value = self._hadjustment.value,
                                canvas_size=w,
                                canvas_offset=x,
                                viewport_size=allocation.width)
        self._update_adjustment(self._vadjustment,
                                value = self._vadjustment.value,
                                canvas_size=h,
                                canvas_offset=y,
                                viewport_size=allocation.height)

        x, y, w, h = self._qtree.bounds
        if w != aw or h != ah:
            self._qtree.resize((0, 0, aw, ah))
        

    def queue_draw_item(self, *items):
        """
        Like ``DrawingArea.queue_draw_area``, but use the bounds of the
        item as update areas. Of course with a pythonic flavor: update
        any number of items at once.
        """
        queue_draw_area = self.queue_draw_area
        get_bounds = self._qtree.get_bounds
        for item in items:
            try:
                queue_draw_area(*get_bounds(item))
            except KeyError:
                pass # No bounds calculated yet? bummer.


    def queue_draw_area(self, x, y, w, h):
        """
        Wrap draw_area to convert all values to ints.
        """
        super(GtkView, self).queue_draw_area(int(x), int(y), int(w+1), int(h+1))


    def queue_draw_refresh(self):
        """
        Redraw the entire view.
        """
        a = self.allocation
        super(GtkView, self).queue_draw_area(0, 0, a.width, a.height)

    def request_update(self, items, matrix_only_items=(), removed_items=()):
        """
        Request update for items. Items will get a full update treatment, while
        ``matrix_only_items`` will only have their bounding box recalculated.
        """
        if items:
            self._dirty_items.update(items)
        if matrix_only_items:
            self._dirty_matrix_items.update(matrix_only_items)

        # Remove removed items:
        if removed_items:
            self._dirty_items.difference_update(removed_items)
            self.queue_draw_item(*removed_items)

            for item in removed_items:
                self._qtree.remove(item)
                self.selected_items.discard(item)

            if self.focused_item in removed_items:
                self.focused_item = None
            if self.hovered_item in removed_items:
                self.hovered_item = None
            if self.dropzone_item in removed_items:
                self.dropzone_item = None

        self.update()


    @async(single=True, priority=PRIORITY_HIGH_IDLE)
    def update(self):
        """
        Update view status according to the items updated by the canvas.
        """
        if not self.window: return

        dirty_items = self._dirty_items
        dirty_matrix_items = self._dirty_matrix_items

        try:
            for i in dirty_items:
                self.queue_draw_item(i)

            for i in dirty_matrix_items:
                if i not in self._qtree:
                    dirty_items.add(i)
                    self.update_matrix(i)
                    continue

                # Mark old bb section for update
                self.queue_draw_item(i)

                self.update_matrix(i)

                if i not in dirty_items:
                    # Only matrix has changed, so calculate new bb based
                    # on quadtree data (= bb in item coordinates).
                    bounds = self._qtree.get_data(i)
                    i2v = self.get_matrix_i2v(i).transform_point
                    x0, y0 = i2v(bounds.x, bounds.y)
                    x1, y1 = i2v(bounds.x1, bounds.y1)
                    vbounds = Rectangle(x0, y0, x1=x1, y1=y1)
                    self._qtree.add(i, vbounds, bounds)

                self.queue_draw_item(i)

            # Request bb recalculation for all 'really' dirty items
            self.update_bounding_box(set(dirty_items))
        finally:
            self._dirty_items.clear()
            self._dirty_matrix_items.clear()


    @async(single=False)
    def update_bounding_box(self, items):
        """
        Update bounding box is not necessary.
        """
        cr = self.window.cairo_create()

        cr.save()
        cr.rectangle(0, 0, 0, 0)
        cr.clip()
        try:
            super(GtkView, self).update_bounding_box(cr, items)
        finally:
            cr.restore()
        self.queue_draw_item(*items)
        self.update_adjustments()


    @nonrecursive
    def do_size_allocate(self, allocation):
        """
        Allocate the widget size ``(x, y, width, height)``.
        """
        gtk.DrawingArea.do_size_allocate(self, allocation)
        self.update_adjustments(allocation)
        self._qtree.resize((0, 0, allocation.width, allocation.height))
       

    def do_realize(self):
        gtk.DrawingArea.do_realize(self)
        allocation = self.allocation

        if self._canvas:
            self.request_update(self._canvas.get_all_items())

    def do_unrealize(self):
        if self.canvas:
            # Although Item._matrix_{i2v|v2i} keys are automatically removed
            # (weak refs), better do it explicitly to be sure.
            self._clear_matrices()
            self.canvas = None
        self._qtree = None

        self._dirty_items = None
        self._dirty_matrix_items = None

        gtk.DrawingArea.do_unrealize(self)

    def do_expose_event(self, event):
        """
        Render canvas to the screen.
        """
        if not self._canvas:
            return

        area = event.area
        x, y, w, h = area.x, area.y, area.width, area.height
        cr = self.window.cairo_create()

        # Draw no more than nessesary.
        cr.rectangle(x, y, w, h)
        cr.clip()

        area = Rectangle(x, y, width=w, height=h)
        self._painter.paint(Context(view=self,
                                    cairo=cr,
                                    items=self.get_items_in_rectangle(area),
                                    area=area))

        if DEBUG_DRAW_BOUNDING_BOX:
            cr.save()
            cr.identity_matrix()
            cr.set_source_rgb(0, .8, 0)
            cr.set_line_width(1.0)
            b = self._bounds
            cr.rectangle(b[0], b[1], b[2], b[3])
            cr.stroke()
            cr.restore()

        # Draw Quadtree structure
        if DEBUG_DRAW_QUADTREE:
            def draw_qtree_bucket(bucket):
                cr.rectangle(*bucket.bounds)
                cr.stroke()
                for b in bucket._buckets:
                    draw_qtree_bucket(b)
            cr.set_source_rgb(0, 0, .8)
            cr.set_line_width(1.0)
            draw_qtree_bucket(self._qtree._bucket)

        return False


    def do_event(self, event):
        """
        Handle GDK events. Events are delegated to a `tool.Tool`.
        """
        handler = EVENT_HANDLERS.get(event.type)
        if self._tool and handler:
            return getattr(self._tool, handler)(ToolContext(view=self), event) and True or False
        return False


    def on_adjustment_changed(self, adj):
        """
        Change the transformation matrix of the view to reflect the
        value of the x/y adjustment (scrollbar).
        """
        if adj is self._hadjustment:
            self._matrix.translate(- self._matrix[4] / self._matrix[0] - adj.value , 0)
        elif adj is self._vadjustment:
            self._matrix.translate(0, - self._matrix[5] / self._matrix[3] - adj.value)

        # Force recalculation of the bounding boxes:
        map(self.update_matrix, self._canvas.get_all_items())
        self.request_update((), self._canvas.get_all_items())

        self.queue_draw_refresh()


if __name__ == '__main__':
    import doctest
    doctest.testmod()

# vim: sw=4:et:
