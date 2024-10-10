from sys import getrecursionlimit, setrecursionlimit
from typing import List
from grandalf.layouts import SugiyamaLayout
from grandalf.graphs import Vertex, Edge, Graph
from .process import ProcessGraphicsItem
from .composition import CompositionGraphicsItem
from .mapping import MappingGraphicsItem, ControlFlowGraphicsItem

class HorizontalSugiyamaLayout(SugiyamaLayout):
    """
    Horizontal version of the Sugiyama Layout.
    """

    def setxy(self):
        """Computes all vertex coordinates (x,y) using
        an algorithm by Brandes & Kopf, but stacks the nodes horizontally.
        """
        self._edge_inverter()
        self._detect_alignment_conflicts()
        inf = float("infinity")

        # Initialize vertex coordinates attributes:
        for l in self.layers:
            for v in l:
                self.grx[v].root = v
                self.grx[v].align = v
                self.grx[v].sink = v
                self.grx[v].shift = inf
                self.grx[v].X = None
                self.grx[v].x = [0.0] * 4

        curvh = self.dirvh  # Save current dirvh value
        for dirvh in range(4):
            self.dirvh = dirvh
            self._coord_horizontal_alignment()
            self._coord_vertical_compact()
        self.dirvh = curvh  # Restore it

        # Horizontal coordinate assignment of all nodes:
        X = 0
        for l in self.layers:
            dX = max([v.view.w / 2.0 for v in l]) + self.xspace
            for v in l:
                vy = sorted(self.grx[v].x)
                avgm = (vy[1] + vy[2]) / 2.0
                v.view.xy = (X + dX, avgm)
            X += dX * 2  # Adjusted for spacing

        self._edge_inverter()

    def _coord_horizontal_alignment(self):
        """Performs horizontal alignment according to current dirvh internal state."""
        dirh, dirv = self.dirh, self.dirv
        g = self.grx
        for l in self.layers[::-dirv]:
            if not l.prevlayer():
                continue
            r = None
            for vk in l[::dirh]:
                for m in l._medianindex(vk):
                    um = l.prevlayer()[m]
                    if g[vk].align is vk:
                        vpair = (vk, um) if dirv == 1 else (um, vk)
                        if (vpair not in self.conflicts) and ((r is None) or (dirh * r < dirh * m)):
                            g[um].align = vk
                            g[vk].root = g[um].root
                            g[vk].align = g[vk].root
                            r = m

    def _coord_vertical_compact(self):
        """Performs vertical compacting for horizontal stacking."""
        limit = getrecursionlimit()
        N = len(self.layers) + 10
        if N > limit:
            setrecursionlimit(N)
        dirh, dirv = self.dirh, self.dirv
        g = self.grx
        L = self.layers[::-dirv]

        for l in L:
            for v in l[::dirh]:
                if g[v].root is v:
                    self.__place_block(v)

        setrecursionlimit(limit)

        # Mirror all nodes if right-aligned:
        if dirh == -1:
            for l in L:
                for v in l:
                    y = g[v].X
                    if y:
                        g[v].X = -y

        rb = float("infinity")
        for l in L:
            for v in l[::dirh]:
                g[v].x[self.dirvh] = g[g[v].root].X
                rs = g[g[v].root].sink
                s = g[rs].shift
                if s < float("infinity"):
                    g[v].x[self.dirvh] += dirh * s
                rb = min(rb, g[v].x[self.dirvh])

        for l in self.layers:
            for v in l:
                g[v].root = g[v].align = g[v].sink = v
                g[v].shift = float("infinity")
                g[v].X = None

    def __place_block(self, v):
        g = self.grx
        if g[v].X is None:
            g[v].X = 0.0
            w = v
            while True:
                j = g[w].pos - self.dirh
                r = g[w].rank
                if 0 <= j < len(self.layers[r]):
                    wprec = self.layers[r][j]
                    delta = self.xspace + (wprec.view.w + w.view.w) / 2.0
                    u = g[wprec].root
                    self.__place_block(u)
                    if g[v].sink is v:
                        g[v].sink = g[u].sink
                    if g[v].sink != g[u].sink:
                        s = g[u].sink
                        newshift = g[v].X - (g[u].X + delta)
                        g[s].shift = min(g[s].shift, newshift)
                    else:
                        g[v].X = max(g[v].X, (g[u].X + delta))
                w = g[w].align
                if w is v:
                    break

def sugiyama_algorithm(items, edges):
    class View(object):
        def __init__(self, item):
            self.item = item
            self.w = item.boundingRect().width()
            self.h = item.boundingRect().height()
            self.xy = None

    v = {}
    e = []

    # Initialize views and edges
    for item in items:
        if isinstance(item, CompositionGraphicsItem):
            layout_composition(item, edges)
        v[item] = Vertex(item)
        v[item].view = View(item)

    for src, dest in edges:
        if src in v and dest in v:
            e.append(Edge(v[src], v[dest]))

    g = Graph(v.values(), e)
    sugiyama_layout = HorizontalSugiyamaLayout(g.C[0])
    sugiyama_layout.init_all()
    sugiyama_layout.draw()

    return {vertex.data: (vertex.view.xy[0], vertex.view.xy[1]) for vertex in g.C[0].sV}

def layout_composition(comp: CompositionGraphicsItem, mapping_edges):
    positions = sugiyama_algorithm(comp.child_comps | comp.functions, mapping_edges)

    for item, pos in positions.items():
        item.setPos(*pos)

def layout_flow(input: ProcessGraphicsItem, output: ProcessGraphicsItem, compositions, mapping_edges, control_edges):
    # First layout the input process
    input.setPos(0, 0)  # Or adjust based on your requirements

    # Layout each composition
    for comp in compositions:
        layout_composition(comp, mapping_edges)

    # Layout the top-level compositions
    positions = sugiyama_algorithm(compositions, control_edges)

    for item, pos in positions.items():
        item.setPos(*pos)

    # Lastly, layout the output process
    output.setPos(0, sum([c.boundingRect().height() for c in compositions]) + 50)  # Place below compositions or adjust as needed
