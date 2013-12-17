pycocontainer
=============

A small, lightweight dependency injection (IoC) container with component and dependency lifecycle management features written in and designed for writing idiomatic python.

Inspired by the seminal PicoContainer project at The Codehaus, but not in _any way_ associated with PicoContainer.  Also not a 'port' of PicoContainer to python.


How it works
------------

Define your component classes and mark them up to use lifecycle management, like so:

```python
from pycocontainer import Lifecycle, Stage, Pycocontainer

class A(Lifecycle):
    def __init__(self, b):
        super(A, self).__init__()
        self.b = b

    @Lifecycle.startmethod
    def foo(self, *args):
        print "Called foo()"

    @Lifecycle.stopmethod
    def bar(self, *args):
        print "Called bar()"

    @Lifecycle.failmethod
    def baz(self, *args):
        print "Called baz()"

class B(Lifecycle):
    def __init__(self):
        super(B, self).__init__()

    @Lifecycle.startmethod
    def funk(self, *args):
        print "Called funk()"

    @Lifecycle.stopmethod
    def soul(self, *args):
        print "Called soul()"

    @Lifecycle.failmethod
    def boogie(self, *args):
        print "Called boogie()"
```

Now, create a container instance and register the component classes in the container:

```python
pyco = Pycocontainer('Woot')
pyco.register(A, 'a')
pyco.register(B, 'b')
```

Once the _class definitions_ of the components are registered in the container, we can use the container to assemble component _instances_ for us:

```python
a = pyco.instance_of(A, 'foo')
print a.b         # yields <test.B object at 0x9b59d0c>
print a.b.stage   # yields Stage.stopped
```

We can make as many as we like:

```python
In [9]: [pyco.instance_of(A, 'foo%s' % x) for x in list(range(10))]
Out[9]:
[<test.A at 0x9b5d1cc>,
 <test.A at 0x9b5d1ec>,
 <test.A at 0x9b5d22c>,
 <test.A at 0x9b5d26c>,
 <test.A at 0x9b487ac>,
 <test.A at 0x9aa074c>,
 <test.A at 0x9a4fdec>,
 <test.A at 0x9a4fe8c>,
 <test.A at 0x9a4feac>,
 <test.A at 0x9a2512c>]
```

But this is only the beginning!  Once we have our components instantiated and wired together, we can tell the container to start managing their lifecycle:

```python
In [10]: a.stage
Out[10]: <Stage.stopped: 3>

In [11]: a.b.stage
Out[11]: <Stage.stopped: 3>

In [12]: pyco.start(a)
Called funk()
Called funk()

In [13]: a.stage
Out[13]: <Stage.started: 1>
```

And, in the process of transitioning a component into its started state, pycocontainer also did so for _all of its dependencies_, in the topological order of the backing acyclic digraph:

```python
In [14]: a.b.stage
Out[14]: <Stage.started: 1>
```

Moreover, because the container knows which components depend on each other, we can have orderly shutdowns, allowing us to safely spin down a component and know that anything depending on it will be forced to properly handle the situation:

```python
In [15]: pyco.stop(a.b)
Called soul()
Called soul()

In [16]: a.b.stage
Out[16]: <Stage.stopped: 3>

In [17]: a.stage
Out[17]: <Stage.stopped: 3>
```

But, it's smart enough not to do more than we ask:

```python
In [18]: pyco.start(a.b)
Called funk()

In [19]: a.b.stage
Out[19]: <Stage.started: 1>

In [20]: a.stage
Out[20]: <Stage.stopped: 3>
```

And, if things go badly wrong, we can explicitly track and manage failure conditions:

```python
In [21]: pyco.fail(a.b)
Called boogie()
Called boogie()

In [22]: a.stage
Out[22]: <Stage.failed: 5>

In [23]: a.b.stage
Out[23]: <Stage.failed: 5>
```

Maybe we don't want to write adapter classes, and just want to rely on "duck" classes.  Not a problem.
```python
class E():
    from pycocontainer import Stage
    def __init__(self):
        self.stage = Stage.stopped

    def start(self):
        self.stage = Stage.starting
        print "Called E.start()"
        self.stage = Stage.started

    def stop(self):
        self.stage = Stage.stopping
        print 'Called E.stop()'
        self.stage = Stage.stopped

    def fail(self):
        self.stage = Stage.failing
        print 'Called E.fail()'
        self.stage = Stage.failed
...

In [35]: e = pyco.instance_of(E, 'metal')

In [36]: e.stage
Out[36]: <Stage.stopped: 3>

In [37]: pyco.start(e)
E.start()

In [38]: e.stage
Out[38]: <Stage.started: 1>
```

If you need to, you can give hints to the container about which specific component instances to use for which paramaters in a given instance.  Consider the following test case:

```python
    def test_attribute_hints(self):
        # Should be able to instantiate a class, and 'rename' its __init__ arguments
        # This should let us point a component at a specific instance of a dependency.
        # Register A and B
        # instantiate two named instances of B
        # instantiate one instance of A, pointing at first B instance.
        # instantiate one instance of A, pointing at second B instance.
        # The B instances should be distinct.
        pyco = self.pyco
        pyco.register(A, 'a')
        pyco.register(B, 'b')
        # Register A and B
        # instantiate two named instances of B
        # instantiate one instance of A, pointing at first B instance.
        # instantiate one instance of A, pointing at second B instance.
        # The B instances should be distinct.
        pyco = self.pyco
        pyco.register(A, 'a')
        pyco.register(B, 'b')
        funk = pyco.instance_of(B, 'funk')
        soul = pyco.instance_of(B, 'soul')
        # Can't settle for any old B, I need the funk.
        foo = pyco.instance_of(A, 'foo', {'b':'funk'})
        # Not enough funk to go around, I'm afraid. Gimme some soul.
        bar = pyco.instance_of(A, 'bar', {'b':'soul'})
        self.assertIsNot(foo, bar)
        self.assertIsNot(foo.b, bar.b)
        self.assertIs(foo.b, funk)
        self.assertIs(bar.b, soul)
```

What else?!
-----------
There's more.  The tests do a pretty good job illustrating how it all works.

It's fast. The backing DAG is _very_ good at knowing what depends on what.  It can detect complex cyclic dependencies when you register components, so you don't end up with infinite start/stop/fail loops.  Topological ordering executes in O(V+E) time, scaling linearly with the numbers of vertices (instances), plus edges (dependency relationships) in the container.

The python class and method decorators are clean and intuitive, letting you spend less time on boilerplate lifecycle code.

