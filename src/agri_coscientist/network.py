from __future__ import annotations
import pandas as pd
import networkx as nx


def coexpression_graph(expression: pd.DataFrame, threshold: float = 0.9) -> nx.Graph:
    """expression: genes x samples; Pearson correlation graph for capability testing."""
    corr = expression.T.corr()
    g = nx.Graph()
    g.add_nodes_from(expression.index)
    genes = list(expression.index)
    for i, a in enumerate(genes):
        for b in genes[i+1:]:
            r = float(corr.loc[a,b])
            if abs(r) >= threshold:
                g.add_edge(a,b,weight=r)
    return g


def hub_degree(g: nx.Graph) -> list[tuple[str,int]]:
    return sorted(g.degree, key=lambda x: (-x[1], x[0]))
