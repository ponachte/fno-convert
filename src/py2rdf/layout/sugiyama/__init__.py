from sys import getrecursionlimit, setrecursionlimit
from grandalf.layouts import SugiyamaLayout
from grandalf.graphs import Vertex, Edge, Graph
from ...visualize.process import ProcessGraphicsItem

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
            self._coord_horizontal_alignment()  # Modified for horizontal alignment
            self._coord_vertical_compact()  # Modified for horizontal stacking
        self.dirvh = curvh  # Restore it
        # Horizontal coordinate assignment of all nodes:
        X = 0
        for l in self.layers:
            dX = max([v.view.w / 2.0 for v in l])
            for v in l:
                vy = sorted(self.grx[v].x)
                # Mean of the 2 medians out of the 4 y-coordinates computed above:
                avgm = (vy[1] + vy[2]) / 2.0
                # Final xy-coordinates :
                v.view.xy = (X + dX, avgm)
            X += 2 * dX + self.xspace
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
                    # Take the median node in dirv layer:
                    um = l.prevlayer()[m]
                    # If vk is "free" align it with um's root
                    if g[vk].align is vk:
                        if dirv == 1:
                            vpair = (vk, um)
                        else:
                            vpair = (um, vk)
                        # If vk<->um link is used for alignment
                        if (vpair not in self.conflicts) and (
                            (r is None) or (dirh * r < dirh * m)
                        ):
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
        # Recursive placement of blocks:
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
        # Then assign y-coord of its root:
        inf = float("infinity")
        rb = inf
        for l in L:
            for v in l[::dirh]:
                g[v].x[self.dirvh] = g[g[v].root].X
                rs = g[g[v].root].sink
                s = g[rs].shift
                if s < inf:
                    g[v].x[self.dirvh] += dirh * s
                rb = min(rb, g[v].x[self.dirvh])
        # Normalize to 0, and reinit root/align/sink/shift/X
        for l in self.layers:
            for v in l:
                # g[v].x[dirvh] -= rb
                g[v].root = g[v].align = g[v].sink = v
                g[v].shift = inf
                g[v].X = None
    
    def __place_block(self, v):
        g = self.grx
        if g[v].X is None:
            # every block is initially placed at x=0
            g[v].X = 0.0
            # place block in which v belongs:
            w = v
            while 1:
                j = g[w].pos - self.dirh  # predecessor in rank must be placed
                r = g[w].rank
                if 0 <= j < len(self.layers[r]):
                    wprec = self.layers[r][j]
                    delta = (
                        self.xspace + (wprec.view.w + w.view.w) / 2.0
                    )  # abs positive minimum displ.
                    # take root and place block:
                    u = g[wprec].root
                    self.__place_block(u)
                    # set sink as sink of prec-block root
                    if g[v].sink is v:
                        g[v].sink = g[u].sink
                    if g[v].sink != g[u].sink:
                        s = g[u].sink
                        newshift = g[v].X - (g[u].X + delta)
                        g[s].shift = min(g[s].shift, newshift)
                    else:
                        g[v].X = max(g[v].X, (g[u].X + delta))
                # take next node to align in block:
                w = g[w].align
                # quit if self aligned
                if w is v:
                    break

def sugiyama_algorithm(edges, nodes):

    class nodeview(object):
        
        def __init__(self, node: ProcessGraphicsItem):
            self.w = node.boundingRect().width()
            self.h = node.boundingRect().height()
            self.xy = None

    v = {}
    e = []
    for src, dest in edges:
        if src not in v:
            v[src] = Vertex(src)
            v[src].view = nodeview(src)
        if dest not in v:
            v[dest] = Vertex(dest)
            v[dest].view = nodeview(dest)
        e.append(Edge(v[src], v[dest]))
    
    g = Graph(v.values(), e)

    sug = HorizontalSugiyamaLayout(g.C[0])
    sug.init_all()
    sug.draw()

    return {vertex.data: (vertex.view.xy[0], vertex.view.xy[1]) for vertex in g.C[0].sV}
