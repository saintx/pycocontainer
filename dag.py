# -*- coding: utf-8 -*-
'''
    dag
    ---

    This module provides a directed, acyclic graph that enforces acyclicity
    via topological sorting.

    :copyright: (c) 2013 by Alexander R. Saint Croix.
    :license: ASL v2.0, see LICENSE for more details.
'''

__version_info__ = ('0', '1', '0')
__version__ = '.'.join(__version_info__)
__author__ = 'Alexander R. Saint Croix'
__license__ = 'Apache Software License v2.0'
__copyright__ = '(c) 2013 by Alexander R. Saint Croix'
__all__ = ['Graph']

import itertools

class Graph(object):
    def __init__(self):
        self.edges = {}
        self.toporder = []

    def vertices(self):
        return self.edges.keys()

    def _edges_copy(self):
        ret = {}
        for item in self.edges:
            ret[item] = [x for x in self.edges[item]]
        return ret

    def successors(self, vertex):
        """
        Returns a topologically ordered list of the successors
        for the given vertex.
        """
        edges = self._edges_copy()
        ret = []
        rem = set(edges[vertex])
        while len(rem) > 0:
            n = rem.pop()
            ret.append(n)
            if n in edges:
                for m in edges[n]:
                    rem.add(m)
        return [x for x in self.toporder if x in ret]

    def precursors(self, vertex):
        """
        Returns a topologically ordered list of the precursors
        for the given vertex.
        """
        edges = self._edges_copy()
        ret = []
        rem = set([x for x in edges if vertex in edges[x]])
        while len(rem) > 0:
            n = rem.pop()
            ret.append(n)
            for precursor in [m for m in edges if n in edges[m]]:
                rem.add(precursor)
        return [x for x in self.toporder if x in ret]
        
    def _toposort(self, graph):
        """
        Uses Khan (1962).  Runs in linear O(V+E) time.
        If the graph is not acyclic, this will raise an exception.
        """
        edges = {}
        for item in graph:
            edges[item] = [x for x in graph[item]]
        children = set(itertools.chain.from_iterable(edges.values()))
        ret = []
        rem = set([x for x in edges if x not in children])
        while len(rem) > 0:
            n = rem.pop()
            ret.append(n)
            if n in edges:
                for m in [x for x in edges[n]]:
                    edges[n].remove(m)
                    # incoming edges for m
                    incoming = [e for e in edges if m in edges[e]]
                    if [] == incoming:
                        rem.add(m)

        remaining_edges = set(itertools.chain.from_iterable(edges.values()))
        if len(remaining_edges) > 0:
            raise Exception('This is not an acyclic digraph: %s' % graph)
        else:
            return ret

    def add(self, v=None, w=None):
        if v is None and w is None:
            return self

        edges = self._edges_copy()
        if v is not None and w is None:
            if v not in edges:
                edges[v] = []
        else:
            if v not in edges:
                edges[v] = [w]
            else:
                edges[v].append(w)
            if w not in edges:
                edges[w] = []

        self.toporder = self._toposort(edges)
        self.edges = edges
        return self
    
    def remove(self, v):
        """
        Removes vertex from all edge relations.
        """
        edges = self._edges_copy()
        if v is not None:
            if v in edges:
                del(edges[v])
            for edge in edges:
                if v in edges[edge]:
                    edges[edge].remove(v)
        self.toporder = self._toposort(edges)
        self.edges = edges
        return self


if __name__ == '__main__':
  import unittest

  class TestDAG(unittest.TestCase):

      def setUp(self):
          pass

      def testAddSingleNode(self):
          class A(object): pass
          a = A()
          g = Graph()
          g.add(a)
          self.assertEqual(1, len(g.vertices()))

      def testAcyclicProperty(self):
          class A(object): pass
          class B(object): pass
          class C(object): pass
          class D(object): pass
          g = Graph()
          a = A()
          b = B()
          c = C()
          d = D()
          g.add(a, b)
          self.assertEqual(2, len(g.vertices()))
          g.add(b, c)
          self.assertEqual(3, len(g.vertices()))
          g.add(d, a)
          self.assertEqual(4, len(g.vertices()))
          self.assertRaises(Exception, g.add, c, d)

      def testGetPrecursorNodes(self):
          g = Graph()
          g.add('c','d')
          g.add('b','c')
          g.add('a','b')
          g.add('a','d')
          g.add('a','c')
          self.assertEqual(['a','b','c'], g.precursors('d'))

      def testGetSuccessorNodes(self):
          g = Graph()
          g.add('a','b')
          g.add('a','d')
          g.add('b','c')
          g.add('c','d')
          self.assertEqual(['b','c','d'], g.successors('a'))

      def testRemoveVertices(self):
          g = Graph()
          g.add('a','b')
          g.add('b','c')
          g.add('c','d')
          self.assertEqual(['a','b','c','d'], g.toporder)
          g.remove('c')
          self.assertEqual(['a','b','d'], g.toporder)


  unittest.main()
