# -*- coding: utf-8 -*-
"""
test.py

Unit tests for pycocontainer

Copyright 2013 Alexander R. Saint Croix (saintx.opensource@gmail.com)
Published under the terms of the Apache Software License v2.0
"""

from pycocontainer import *
import unittest

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

class C(object):
    def __init__(self, d):
        self.d = d

class D(object):
    def __init__(self, c):
        self.c = c


class TestPycocontainer(unittest.TestCase):

    def setUp(self):
        print '-------------------'
        self.pyco = Pycocontainer('Test container')

    def test_register_components(self):
        # register two components
        self.pyco.register(A, 'a')
        self.pyco.register(B, 'b')

    def test_disallow_duplicate_registration(self):
        # cannot register a component twice.
        self.pyco.register(A, 'a')
        self.assertRaises(DuplicateComponentClass, self.pyco.register, A, 'a2')

        # cannot reuse a component name.
        class Reuse(object): pass
        self.assertRaises(DuplicateComponentName, self.pyco.register, Reuse, 'a')

    def test_instantiation(self):
        self.pyco = Pycocontainer('Test container')
        self.pyco.register(A, 'a')
        self.pyco.register(B, 'b')

        # Get an instance of component A from container.
        a = self.pyco.instance_of(A, 'a')
        self.assertIsNotNone(a)

        # Get a again, it should be the same as before.
        a2 = self.pyco.instance_of(A, 'a')

        # Get an instance of component B from container.
        b = self.pyco.instance_of(B, 'b')
        self.assertIsNotNone(b)

        # B should the the same component as is assigned to a.
        a.b is b

    def test_cyclic_dependency_fails(self):
        # C should create a circular dependency exception
        self.pyco.register(C, 'c')
        self.pyco.register(D, 'd')
        self.assertRaises(CircularDependency, self.pyco.instance_of, C, 'c')

    def test_component_lifecycle_management(self):
        self.pyco.register(A, 'a')
        self.pyco.register(B, 'b')
        a = self.pyco.instance_of(A, 'foo')
        # Component A is "stopped" upon initialization
        self.assertEqual(a.stage, Stage.stopped)
        # Component A has an instance of Component B
        self.assertIsNotNone(a.b)
        # Component B is also stopped.
        self.assertEqual(a.b.stage, Stage.stopped)

        # Transitions between lifecycle phases
        a.starting()
        self.assertEqual(a.stage, Stage.starting)
        a.started()
        self.assertEqual(a.stage, Stage.started)

        a.stopping()
        self.assertEqual(a.stage, Stage.stopping)
        a.stopped()
        self.assertEqual(a.stage, Stage.stopped)

        a.starting()
        self.assertEqual(a.stage, Stage.starting)
        a.started()
        self.assertEqual(a.stage, Stage.started)

        a.failing()
        self.assertEqual(a.stage, Stage.failing)
        a.failed()
        self.assertEqual(a.stage, Stage.failed)

        # Let's try the decorated start functions.
        a.foo()
        self.assertEqual(a.stage, Stage.started)
        a.bar()
        self.assertEqual(a.stage, Stage.stopped)
        a.baz()
        self.assertEqual(a.stage, Stage.failed)

        # Alrighty, try that on a separate class.
        b = self.pyco.instance_of(B, 'funk')
        # For the record, this isn't the same one.
        self.assert_(b is not a.b)
        self.assertEqual(b.stage, Stage.stopped)
        b.started()
        self.assertEqual(b.stage, Stage.started)

        b.stopping()
        self.assertEqual(b.stage, Stage.stopping)
        b.stopped()
        self.assertEqual(b.stage, Stage.stopped)

        b.failing()
        self.assertEqual(b.stage, Stage.failing)
        b.failed()
        self.assertEqual(b.stage, Stage.failed)

        # More decorated functions
        b.funk()
        self.assertEqual(b.stage, Stage.started)
        b.soul()
        self.assertEqual(b.stage, Stage.stopped)
        b.boogie()
        self.assertEqual(b.stage, Stage.failed)

        # Or, use the (now bound) API methods
        b.start() # calls b.funk()
        self.assertEqual(b.stage, Stage.started)
        b.stop() # calls b.soul()
        self.assertEqual(b.stage, Stage.stopped)
        b.fail() # calls b.boogie()
        self.assertEqual(b.stage, Stage.failed)


    def test_duck_types(self):
        # Also works with "duck" classes.
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

        print 'trying to get instance of "jazz" component'
        e = self.pyco.instance_of(E, 'jazz')
        self.assertEqual(e.stage, Stage.stopped)
        self.pyco.start()
        self.assertEqual(e.stage, Stage.started)
        self.pyco.stop()
        self.assertEqual(e.stage, Stage.stopped)
        self.pyco.fail()
        self.assertEqual(e.stage, Stage.failed)

        
    def test_multiple_instantiation(self):
        # Should be able to create multiple, distinct instances of A
        # These should, by default, both depend on the same B
        pyco = self.pyco
        pyco.register(A, 'a')
        pyco.register(B, 'b')
        foo = pyco.instance_of(A, 'foo')
        bar = pyco.instance_of(A, 'bar')
        self.assertIsNot(foo, bar)
        self.assertIs(foo.b, bar.b)


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


    def test_lifecycle_implications(self):
        # Components are started in order
        # All dependencies must be started for a component to start.
        # If a component's dependency component stops or fails, so will the component.
        pyco = self.pyco
        pyco.register(A, 'a')
        pyco.register(B, 'b')
        a = pyco.instance_of(A, 'foo')
        # a has bound lifecycle methods! Because Python magic!
        self.assertIsNotNone(a.start.im_self)
        self.assertIsNotNone(a.stop.im_self)
        self.assertIsNotNone(a.fail.im_self)
        a.start()
        self.assertEquals(a.stage, Stage.started)

        b = a.b
        # like a, b has BOUND lifecycle methods now!
        self.assertIsNotNone(b.start.im_self)
        self.assertIsNotNone(b.stop.im_self)
        self.assertIsNotNone(b.fail.im_self)
        # start the container
        pyco.start()
        self.assertEqual(b.stage, Stage.started)
        self.assertEqual(a.stage, Stage.started)
    
        # stop a component. Anything depending on it should stop, too.
        pyco.stop(b)
        self.assertEqual(a.stage, Stage.stopped)

        # restart them both
        pyco.start()
        self.assertEqual(a.stage, Stage.started)
        self.assertEqual(b.stage, Stage.started)

        # Stopping component won't stop its dependencies.
        pyco.stop(a)
        self.assertEqual(a.stage, Stage.stopped)
        self.assertEqual(b.stage, Stage.started)

        # Start the component again, and we'll fail its dependency.
        pyco.start(a)
        self.assertEqual(a.stage, Stage.started) 
        pyco.fail(b)
        self.assertEqual(b.stage, Stage.failed)
        self.assertEqual(a.stage, Stage.failed)
        self.assertEqual(pyco.stage, Stage.failed)
        
        # Call the lifecycle methods via the container. Container manages the LC
        # Components restart (stop+start) when their dependencies do.
        
if __name__ == '__main__':
    unittest.main()