"""
Custom decorators.
"""

__version__ = "$Revision: 2292 $"
# $HeadURL: http://svn.devjavu.com/gaphor/gaphas/tags/gaphas-0.3.6/gaphas/decorators.py $

import gobject
from gobject import PRIORITY_HIGH, PRIORITY_HIGH_IDLE, PRIORITY_DEFAULT, \
        PRIORITY_DEFAULT_IDLE, PRIORITY_LOW
import operator


DEBUG_ASYNC = False


class async(object):
    """
    Instead of calling the function, schedule an idle handler at a given
    priority. This requires the async'ed method to be called from within
    the GTK main loop. Otherwise the method is executed directly.

    Note:
        the current implementation of async single mode only works for
        methods, not functions.

    Calling the async function from outside the gtk main loop will yield
    imediate execution:

    async just works on functions (as long as ``single=False``):

    >>> a = async()(lambda: 'Hi')
    >>> a()
    'Hi'

    Simple method:
    
    >>> class A(object):
    ...     @async(single=False, priority=gobject.PRIORITY_HIGH)
    ...     def a(self):
    ...         print 'idle-a', gobject.main_depth()
    
    Methods can also set sinle mode to True (the method is only scheduled one).

    >>> class B(object):
    ...     @async(single=True)
    ...     def b(self):
    ...         print 'idle-b', gobject.main_depth()

    This is a helper function used to test classes A and B from within the GTK+
    main loop:

    >>> def delayed():
    ...     print 'before'
    ...     a = A()
    ...     b = B()
    ...     a.a()
    ...     b.b()
    ...     a.a()
    ...     b.b()
    ...     a.a()
    ...     b.b()
    ...     print 'after'
    ...     gobject.timeout_add(100, gtk.main_quit)
    >>> gobject.timeout_add(1, delayed) > 0 # timeout id may vary
    True
    >>> import gtk
    >>> gtk.main()
    before
    after
    idle-a 1
    idle-a 1
    idle-a 1
    idle-b 1

    As you can see, although ``b.b()`` has been called three times, it's only
    executed once.
    """

    def __init__(self, single=False, priority=gobject.PRIORITY_DEFAULT):
        self.single = single
        self.priority = priority

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # execute directly if we're not in the main loop.
            if gobject.main_depth() == 0:
                return func(*args, **kwargs)
            elif not self.single:
                def async_wrapper():
                    if DEBUG_ASYNC: print 'async:', func, args, kwargs
                    func(*args, **kwargs)
                gobject.idle_add(async_wrapper, priority=self.priority)
            else:
                holder = args[0]
                try:
                    f = operator.attrgetter('_async_id_%s' % func.__name__)
                    if f(holder):
                        return
                except AttributeError, e:
                    def async_wrapper():
                        if DEBUG_ASYNC: print 'async:', func, args, kwargs
                        try:
                            func(*args, **kwargs)
                        finally:
                            holder.__delattr__('_async_id_%s' % func.__name__)
                        return False

                    holder.__setattr__('_async_id_%s' % func.__name__,
                        gobject.idle_add(async_wrapper, priority=self.priority))
        return wrapper


def nonrecursive(func):
    """
    Enforce a function or method is not executed recursively:

    >>> class A(object):
    ...     @nonrecursive
    ...     def a(self, x=1):
    ...         print x
    ...         self.a(x+1)
    >>> A().a()
    1
    >>> A().a()
    1
    """
    def wrapper(*args, **kwargs):
        """
        Decorate function with a mutex that prohibits recursice execution.
        """
        try:
            if func._executing:
                return
        except AttributeError:
            # _executed not present
            pass
        try:
            func._executing = True
            return func(*args, **kwargs)
        finally:
            del func._executing
    return wrapper


class recursive(object):
    """
    This decorator limits the recursion for a specific function

    >>> class A(object):
    ...    def __init__(self): self.r = 0
    ...    @recursive(10)
    ...    def a(self, x=0):
    ...        self.r += 1
    ...        self.a()
    >>> a = A()
    >>> a.a()
    >>> a.r
    10
    """

    def __init__(self, limit=10000):
        self.limit = limit

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            try:
                func._recursion_level += 1
            except AttributeError:
                # _recursion_level not present
                func._recursion_level = 0
            if func._recursion_level < self.limit:
                try:
                    return func(*args, **kwargs)
                finally:
                    func._recursion_level -= 1
        return wrapper


if __name__ == '__main__':
    import doctest
    doctest.testmod()

# vim:sw=4:et
