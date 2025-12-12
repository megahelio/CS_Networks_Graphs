import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import concurrent.futures
import multiprocessing
from collections import Counter
import warnings

# Module-level worker function for parallelism
def _betweenness_worker(G, nodes_chunk, weight):
    return nx.betweenness_centrality_subset(G, sources=nodes_chunk, targets=list(G.nodes()), weight=weight)

class GraphMetrics:
    def __init__(self, adjacency_matrix):
        """
        Initializes the GraphMetrics object.
        
        Args:
            adjacency_matrix (list or np.ndarray): The adjacency matrix of the graph.
        """
        self.adj_matrix = np.array(adjacency_matrix)
        self.n_nodes = self.adj_matrix.shape[0]
        
        # Check if directed (asymmetric matrix)
        is_symmetric = np.allclose(self.adj_matrix, self.adj_matrix.T)
        if is_symmetric:
            self.G = nx.from_numpy_array(self.adj_matrix, create_using=nx.Graph)
            self.directed = False
        else:
            self.G = nx.from_numpy_array(self.adj_matrix, create_using=nx.DiGraph)
            self.directed = True
            
        # Check if weighted (values other than 0 and 1)
        unique_values = np.unique(self.adj_matrix)
        self.weighted = np.any((unique_values != 0) & (unique_values != 1))
        
    def compute_structural_variables(self):
        """Returns fundamental structural variables."""
        return {
            "V": list(self.G.nodes()),
            "E": list(self.G.edges(data=True)) if self.weighted else list(self.G.edges()),
            "n": self.G.number_of_nodes(),
            "m": self.G.number_of_edges(),
            "A_ij": self.adj_matrix,
            "weighted": self.weighted,
            "directed": self.directed
        }

    
    def compute_local_centrality(self):
        """Computes local centrality measures for each node."""
        
        # Degree
        if self.directed:
            degree = dict(self.G.in_degree()) 
        else:
            degree = dict(self.G.degree())
            
        # Strength (Weighted Degree)
        if self.weighted:
            strength = dict(self.G.degree(weight='weight'))
        else:
            strength = degree 
            
        # Closeness Centrality
        closeness = nx.closeness_centrality(self.G, distance='weight' if self.weighted else None)
        
        # Betweenness Centrality
        weight_attr = 'weight' if self.weighted else None
        betweenness = nx.betweenness_centrality(self.G, weight=weight_attr)

        # Local Clustering
        clustering = nx.clustering(self.G, weight=weight_attr)
        
        return {
            "degree": degree,
            "strength": strength,
            "closeness": closeness,
            "betweenness": betweenness,
            "clustering_coefficient_local": clustering
        }

    def compute_global_measures(self):
        """Computes global graph measures."""
        
        # Density
        density = nx.density(self.G)
        
        # Diameter & Avg Path Length
        if nx.is_directed(self.G):
            if nx.is_strongly_connected(self.G):
                diameter = nx.diameter(self.G)
                avg_path_length = nx.average_shortest_path_length(self.G)
            else:
                largest_cc = max(nx.strongly_connected_components(self.G), key=len)
                if len(largest_cc) > 1:
                    subgraph = self.G.subgraph(largest_cc)
                    diameter = nx.diameter(subgraph)
                    avg_path_length = nx.average_shortest_path_length(subgraph)
                else:
                    diameter = 0
                    avg_path_length = 0
        else:
            if nx.is_connected(self.G):
                diameter = nx.diameter(self.G)
                avg_path_length = nx.average_shortest_path_length(self.G)
            else:
                largest_cc = max(nx.connected_components(self.G), key=len)
                if len(largest_cc) > 1:
                    subgraph = self.G.subgraph(largest_cc)
                    diameter = nx.diameter(subgraph)
                    avg_path_length = nx.average_shortest_path_length(subgraph)
                else:
                    diameter = 0
                    avg_path_length = 0

        # Global Clustering (Transitivity)
        global_clustering = nx.transitivity(self.G)
        
        # Average Clustering
        avg_clustering = nx.average_clustering(self.G, weight='weight' if self.weighted else None)
        
        # Modularity & Communities
        try:
            communities = list(nx.community.greedy_modularity_communities(self.G, weight='weight' if self.weighted else None))
            modularity = nx.community.modularity(self.G, communities, weight='weight' if self.weighted else None)
            # Convert frozensets to lists for JSON serialization
            communities_list = [list(c) for c in communities]
        except:
            modularity = 0.0
            communities_list = []

        # Degree Distribution stats
        degrees = [d for n, d in self.G.degree()]
        avg_degree = np.mean(degrees) if degrees else 0
        
        if self.weighted:
            strengths = [d for n, d in self.G.degree(weight='weight')]
            avg_strength = np.mean(strengths) if strengths else 0
        else:
            avg_strength = avg_degree

        return {
            "density": density,
            "diameter": diameter,
            "global_clustering_transitivity": global_clustering,
            "average_clustering": avg_clustering,
            "modularity_Q": modularity,
            "communities": communities_list,
            "average_degree": avg_degree,
            "average_strength": avg_strength,
            "average_path_length": avg_path_length
        }

    def plot_distributions(self, output_dir):
        """Generates and saves histograms for local metrics."""
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        metrics = self.compute_local_centrality()
        
        # 1. Degree Distribution
        degrees = list(metrics['degree'].values())
        plt.figure()
        plt.hist(degrees, bins=20, color='skyblue', edgecolor='black')
        plt.title('Degree Distribution')
        plt.xlabel('Degree')
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(output_dir, 'dist_degree.png'))
        plt.close()

        # 2. Strength Distribution
        if self.weighted:
            strengths = list(metrics['strength'].values())
            plt.figure()
            plt.hist(strengths, bins=20, color='lightgreen', edgecolor='black')
            plt.title('Strength Distribution')
            plt.xlabel('Strength')
            plt.ylabel('Frequency')
            plt.savefig(os.path.join(output_dir, 'dist_strength.png'))
            plt.close()

        # 3. Betweenness Distribution
        betweenness = list(metrics['betweenness'].values())
        plt.figure()
        plt.hist(betweenness, bins=20, color='salmon', edgecolor='black')
        plt.title('Betweenness Centrality Distribution')
        plt.xlabel('Betweenness')
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(output_dir, 'dist_betweenness.png'))
        plt.close()

        # 4. Closeness Distribution
        closeness = list(metrics['closeness'].values())
        plt.figure()
        plt.hist(closeness, bins=20, color='orange', edgecolor='black')
        plt.title('Closeness Centrality Distribution')
        plt.xlabel('Closeness')
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(output_dir, 'dist_closeness.png'))
        plt.close()
        
        # 5. Graph Visualization
        self.plot_graph(os.path.join(output_dir, 'graph_viz.png'))

    def plot_graph(self, output_path=None):
        """Visualizes the graph."""
        plt.figure(figsize=(12, 10))
        pos = nx.spring_layout(self.G, seed=42, k=0.3) # k regulates spacing
        
        # Node size by degree
        d = dict(self.G.degree(weight='weight' if self.weighted else None))
        node_sizes = [v * 20 + 50 for v in d.values()]
        
        nx.draw_networkx_nodes(self.G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.9)
        
        # Edges
        if self.weighted:
            weights = [self.G[u][v]['weight'] for u,v in self.G.edges()]
            # Normalize for visualization width
            max_w = max(weights) if weights else 1
            widths = [w/max_w * 3 for w in weights]
            nx.draw_networkx_edges(self.G, pos, width=widths, alpha=0.4, edge_color='gray')
        else:
            nx.draw_networkx_edges(self.G, pos, alpha=0.4, edge_color='gray')
            
        nx.draw_networkx_labels(self.G, pos, font_size=8)
        
        plt.title("Keyword Co-occurrence Graph")
        plt.axis('off')
        
        if output_path:
            plt.savefig(output_path)
            plt.close()
        else:
            plt.show()

    def report_all(self):
        """Aggregates all metrics."""
        structural = self.compute_structural_variables()
        local = self.compute_local_centrality()
        global_measures = self.compute_global_measures()
        
        return {
            "structural": structural,
            "local": local,
            "global": global_measures
        }
