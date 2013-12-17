# -*- coding: utf-8 -*-
"""
pycocontainer.py

A lightweight dependency injection container for idiomatic python.

Copyright 2013 Alexander R. Saint Croix (saintx.opensource@gmail.com)
Published under the terms of the Apache Software License v2.0
"""
from enum import Enum

class DuplicateComponentClass(Exception):
    def __init__(self, msg):
        super(DuplicateComponentClass, self).__init__(msg)

class DuplicateComponentName(Exception):
    def __init__(self, msg):
        super(DuplicateComponentName, self).__init__(msg)

class DuplicateInstanceName(Exception):
    def __init__(self, msg):
        super(DuplicateInstanceName, self).__init__(msg)

class UnsatisfiableDependency(Exception):
    def __init__(self, msg):
        super(UnsatisfiableDependency, self).__init__(msg)

class CircularDependency(Exception): pass

class NotImplemented(Exception):
    def __init__(self, msg):
        super(NotImplemented, self).__init__(msg)

class LifecycleException(Exception):
    def __init__(self, msg):
        super(LifecycleException, self).__init__(msg)


class Stage(Enum):
    starting = 0
    started = 1
    stopping = 2
    stopped = 3
    failing = 4
    failed = 5


class Lifecycle(object):
    def __init__(self):
        super(Lifecycle, self).__init__()
        self.stage = Stage.stopped

    def starting(self): self.stage = Stage.starting
    def started(self): self.stage = Stage.started
    def stopping(self): self.stage = Stage.stopping
    def stopped(self): self.stage = Stage.stopped
    def failing(self): self.stage = Stage.failing
    def failed(self): self.stage = Stage.failed

    @classmethod
    def startmethod(cls, f):
        def _wrapper(self, *args, **kwargs):
            self.starting()
            f(self, *args, **kwargs)
            self.started()
        cls.start = _wrapper
        return _wrapper

    @classmethod
    def stopmethod(cls, f):
        def _wrapper(self, *args, **kwargs):
            self.stopping()
            f(self, *args, **kwargs)
            self.stopped()
        cls.stop = _wrapper
        return _wrapper

    @classmethod
    def failmethod(cls, f):
        def _wrapper(self, *args, **kwargs):
            self.failing()
            f(self, *args, **kwargs)
            self.failed()
        cls.fail = _wrapper
        return _wrapper


class LifecycleContainer(Lifecycle):
    def __init__(self):
        from dag import Graph
        super(LifecycleContainer, self).__init__()
        self._instance_graph = Graph()

    def start(self, instance=None):
        """
        Starts the instance, and its dependencies, in order.
        If instance is None, starts every instance in the backing DAG.
        If any of the instances are not startable, raises exceptions.
        """
        def _start_node(node):
            if node.stage not in [Stage.started, Stage.starting]:
                node.start()
            if node.stage is not Stage.started:
                raise LifecycleException('Could not properly start node %s' % node)

        dag = self._instance_graph
        self.starting()
        if instance is None:
            # Start every startable component in the container in ascending order.
            for node in dag.toporder:
                _start_node(node)
        else:
            # Start this component's precursors, in ascending order
            precursors = dag.precursors(instance)
            for prec in precursors:
                _start_node(prec)

            # Start this component.
            _start_node(instance)

        self.started()


    def stop(self, instance=None):
        def _stop_node(node):
            if node.stage not in [Stage.stopped, Stage.stopping]:
                node.stop()
            if node.stage is not Stage.stopped:
                raise LifecycleException('Could not properly stop node %s' % node)

        dag = self._instance_graph
        if instance is None:
            self.stopping() # Down with the ship.
            # Stop every startable component in the container in descending order.
            for node in list(reversed(dag.toporder)):
                _stop_node(node)
            self.stopped()
        else:
            descendants = dag.successors(instance)
            covered = len(descendants) == (len(dag.toporder) - 1)
            if covered:
                self.stopping()
            # Stop every startable component that depends on this component, in descending order.
            for descendant in list(reversed(descendants)):
                _stop_node(descendant)

            # Stop this component.
            _stop_node(instance)
            if covered:
                self.stopped()

    def restart(self, instance=None):
        """
        Restart components descending from given instance.
        If instance is None, restart them all.
        """
        dag = self._instance_graph
        self.stop(instance)

        # Now, restart the object and its descendants, in ascending order.
        # TODO: Should this be eager, or lazy?
        descendants = dag.successors(instance)
        for descendant in descendants:
            self.start(descendant)
        self.start(instance)

    def fail(self, instance=None):
        """
        Something is failing.  If we know what it is, we can stage a graceful
        failure cascade with explicit handling.
        """
        dag = self._instance_graph
        if instance is None:
            self.failing() # Down with the ship.
            # Fail every startable component in the container in descending order.
            for node in list(reversed(dag.toporder)):
                node.fail()
                if node.stage is not Stage.failed:
                    raise LifecycleException('Could not properly fail node %s' % node)
            self.failed()
        else:
            descendants = dag.successors(instance)
            covered = len(descendants) == (len(dag.toporder) - 1)
            if covered:
                self.failing() # If all else fails, well, we do too.
            for descendant in list(reversed(descendants)):
                descendant.fail()
                if descendant.stage is not Stage.failed:
                    raise LifecycleException('Could not properly fail node %s' % node)
            # Fail this component.
            instance.fail()
            if instance.stage is not Stage.failed:
                raise LifecycleException('Could not properly fail node %s' % instance)
            if covered:
                self.failed()


class Pycocontainer(LifecycleContainer):

    def __init__(self, name):
        super(Pycocontainer, self).__init__()
        self.name = name
        self._component_registry = {}
        self._component_names = {}
        self._instance_registry = {}


    def register(self, cls, name):
        """
        Register a component definition.
        If a component exists with the same name or class, raise an exception.
        """
        r = self._component_registry
        ri = self._component_names
        if cls not in r.keys():
            if name not in ri.keys():
                component = {}
                varnames = list(cls.__init__.func_code.co_varnames[1:])
                component['name'] = name
                component['varnames'] = varnames
                r[cls] = component
                ri[name] = cls
            else:
                raise DuplicateComponentName('%s' % name)
        else:
            raise DuplicateComponentClass('%s' % cls)


    def instance_of(self, cls=None, name=None, hints={}):
        if cls is None or name is None:
            raise Exception('Cannot instantiate without a class and name.')
        components = self._component_registry
        instances = self._instance_registry
        names = self._component_names

        def retrieve(cls, name):
            """
            Attempt to retrieve an instance with this name and class.
            If there is a mismatch, raise an exception.
            """
            if name in instances.keys():
                ret = instances[name]
                if ret.__class__ is cls:
                    return ret
                else:
                    raise DuplicateInstanceName('Name belongs to component of another class')
            else:
                return instantiate(cls, name)
                      
        def instantiate(cls=None, name='', processing=[]):
            """
            Instantiate a new component instance.
            """
            if cls not in components.keys():
                self.register(cls, name)

            component = components[cls]
            varnames = component['varnames']
            deps = {}
            for vname in varnames:
                if vname in components.keys():
                    deps[vname] = components[vname] 
                else:
                    # is there a hint matching this vname?
                    if vname in hints.keys():
                        # is there an instance in the instance reg with this vname hint?
                        if hints[vname] in instances.keys():
                            instance = instances[hints[vname]]
                            deps[vname] = instance
                        # if not, they're asking for something we don't have.  Bail.
                        else:
                            raise UnsatisfiableDependency('No component instance named %s in container.' % vname)
                    # if not, look for instance matching the component name.
                    else:
                        # is there an instance in the instance registry?
                        if vname in instances.keys():
                            instance = instances[vname]
                            deps[vname] = instance
                        else:
                            # if vname is in component names, recurse
                            if vname in names.keys():
                                cl = names[vname]
                                if vname not in processing:
                                    processing.append(vname)
                                    instance = instantiate(cl, vname, processing)
                                    deps[vname] = instance
                                    processing.remove(vname)
                                else:
                                    raise CircularDependency()
                            # if not, the dependency is unsatisfiable 
                            else:
                                raise UnsatisfiableDependency('No registered component with class %s and name %s in container.' % (cls, vname))

            dag = self._instance_graph
            if len(varnames) == len(deps.keys()):
                instance = cls(**deps)
                instances[name] = instance
                # update the backing dependency digraph
                dag.add(instance)
                for dep in [deps[x] for x in deps.keys()]:
                    dag.add(dep, instance)
                return instance
            else:
                raise Exception('Unsatisfied dependency', 'varnames:%s, deps:%s' % (varnames, deps), r, ri)

        ret = retrieve(cls, name)
        return ret
