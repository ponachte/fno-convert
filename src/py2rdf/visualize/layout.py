from sys import getrecursionlimit, setrecursionlimit
from grandalf.layouts import SugiyamaLayout
from grandalf.graphs import Vertex, Edge, Graph
from .process import ProcessGraphicsItem
from .composition import CompositionGraphicsItem

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

class ClusteredSugiyamaLayout(HorizontalSugiyamaLayout):
    """
    Horizontal version of the Sugiyama Layout that supports clusters.
    The layout places clusters and vertices in a horizontal flow.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setxy(self):
        """Override to support clusters in addition to regular vertices."""
        self._edge_inverter()
        self._detect_alignment_conflicts()
        inf = float("infinity")

        # Initialize vertex and cluster attributes:
        for l in self.layers:
            for v in l:
                self.grx[v].root = v
                self.grx[v].align = v
                self.grx[v].sink = v
                self.grx[v].shift = inf
                self.grx[v].X = None
                self.grx[v].x = [0.0] * 4

        # Layout for the rest of the vertices
        curvh = self.dirvh  # Save current dirvh value
        for dirvh in range(4):
            self.dirvh = dirvh
            self._coord_horizontal_alignment()  # Modified for horizontal alignment
            self._coord_vertical_compact()  # Modified for horizontal stacking
        self.dirvh = curvh  # Restore it
        
        # Layout for clusters (treat clusters like super-nodes)
        self._layout_remaining_vertices()

        self._edge_inverter()

    def _layout_remaining_vertices(self):
        """Layout the remaining vertices and clusters."""
        X = 0
        for l in self.layers:
            dX = max([self._get_item_width(v) for v in l])  # Space between vertices/clusters
            for v in l:
                vy = sorted(self.grx[v].x)
                avgm = (vy[1] + vy[2]) / 2.0
                # Set xy-coordinates:
                v.view.xy = (X + dX, avgm)
                self._layout_cluster_horizontal(v)  # Recursively layout clusters horizontally
            X += 2 * dX + self.xspace  # Increment X for horizontal layout

    def _layout_cluster_horizontal(self, v):
        """
        Recursively layouts clusters and their children in horizontal orientation.
        """
        if isinstance(v.view, CompositionGraphicsItem):
            cluster_item = v.view
            cluster_item.updateBounds()  # Compute bounds based on child vertices or clusters

            # Start horizontal layout for the cluster's child items
            X = cluster_item.bounds.left() + self.xspace
            max_height = 0
            for child in cluster_item.functions:
                child_v = self.grx[child]
                if child_v is not None:
                    # Set position for each child, placing them horizontally within the cluster
                    child_v.view.setPos(X, cluster_item.bounds.top() + self.yspace)
                    X += child_v.view.boundingRect().width() + self.xspace
                    max_height = max(max_height, child_v.view.boundingRect().height())

            # Handle child clusters inside the current cluster
            for child_comp in cluster_item.child_comps:
                comp_v = self.grx[child_comp]
                if comp_v is not None:
                    comp_v.view.setPos(X, cluster_item.bounds.top() + self.yspace)
                    X += comp_v.view.boundingRect().width() + self.xspace
                    max_height = max(max_height, comp_v.view.boundingRect().height())

            # Update the cluster bounds based on its children
            cluster_item.bounds.setWidth(X - cluster_item.bounds.left() + self.xspace)
            cluster_item.bounds.setHeight(max_height + 2 * self.yspace)
            cluster_item.update()  # Repaint the cluster

    def _get_item_width(self, v):
        """
        Get the width of a vertex or cluster. This is used to determine how much horizontal space 
        to allocate for a node in the layout.
        """
        if isinstance(v.view, CompositionGraphicsItem):
            return v.view.boundingRect().width()  # Return the width of the cluster
        return v.view.w / 2.0  # Regular vertices width
    
class nodeview(object):
        def __init__(self, node: ProcessGraphicsItem):
            self.node = node
            self.w = node.boundingRect().width()
            self.h = node.boundingRect().height()
            self.xy = None

def sugiyama_algorithm(edges, compositions):

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

    for comp in compositions:
        if comp not in v:
            v[comp] = Vertex(comp)
            v[comp].view = nodeview(comp)

    g = Graph(v.values(), e)
    sugiyama_layout = ClusteredSugiyamaLayout(g.C[0])
    sugiyama_layout.init_all()
    sugiyama_layout.draw()

    return {vertex.data: (vertex.view.xy[0], vertex.view.xy[1]) for vertex in g.C[0].sV}