# Graphlex Glossary

This glossary explains the main terms that appear in Graphlex documentation, CLI
prompts, configuration files, output files, and network-analysis reports.

## Project and data collection

### Bluesky

The social-media platform from which Graphlex collects public posts for analysis.

### AT Protocol

The open protocol used by Bluesky. Graphlex accesses it through the `atproto`
Python client.

### Post

A piece of text retrieved from Bluesky. Posts are the basic input records used
to find keyword occurrences and co-occurrences.

### Handle

The Bluesky account identifier used to authenticate the API client, such as
`user.bsky.social`.

### Credential

The Bluesky handle and password supplied through environment variables. Graphlex
reads them from `BLUESKY_HANDLE` and `BLUESKY_PASSWORD`.

### Cursor

An opaque pagination token returned by the Bluesky API. Graphlex sends the
returned cursor with the next search request to retrieve the following page of
posts. The first request does not use a cursor.

### Date range

The start and end dates used to restrict which retrieved posts are included in
the analysis.

### Location filter

An optional list of location terms used to restrict collected posts or authors.

## Keywords and text analysis

### Keyword

A word or phrase that Graphlex searches for in post text. Keywords are matched
case-insensitively, so `CO2` and `co2` are treated as the same term.

### Main keywords

The shared keyword set used as the core of the analysis, including terms such as
`green transition`, `global warming`, and `renewable energy`.

### Group keywords

An additional thematic keyword set used to extend the main analysis.

### Extra keywords

Optional keywords used by the full analysis configuration, such as `clean
energy`, `net zero`, and `heatwaves`.

### Analysis configuration

A named combination of keywords and settings. The default configurations are
`main_keywords`, `main_plus_our`, and `full_analysis`.

### Case-insensitive matching

Text matching that ignores capitalization. For example, `Green Transition`,
`green transition`, and `GREEN TRANSITION` match the same keyword.

### Co-occurrence

The appearance of two different keywords in the same post. Each matching pair
increments the pair's co-occurrence count.

### Co-occurrence matrix

A table whose rows and columns are keywords. Each cell contains the number of
posts in which the corresponding pair of keywords occurs together.

### Minimum co-occurrences

The threshold used to decide which keyword pairs become graph edges. The
`MIN_CO_OCCURRENCES` setting defaults to `1`.

### Sentiment

The estimated emotional polarity of a post's text. Graphlex classifies posts as
`positive`, `neutral`, or `negative` and may also record a numeric sentiment
score.

## Network concepts

### Network analysis

The process of converting keyword relationships into a graph and calculating
structural measurements that describe the graph.

### Graph

A mathematical representation of relationships. In Graphlex, the graph is
undirected: a relationship between two keywords has no direction.

### Node

An item in the graph. Each keyword is represented by one node.

### Edge

A relationship between two nodes. Graphlex adds an edge when two keywords
co-occur at least the configured minimum number of times.

### Edge weight

The number of co-occurrences represented by an edge. A larger weight means the
two keywords appeared together in more posts.

### Degree

The number of distinct connections a node has. A keyword with a high degree is
connected to many other keywords.

### Strength

The sum of the weights of all edges connected to a node. Strength measures the
total weighted volume of a keyword's relationships.

### Degree distribution

The set of node degree values across the entire network.

### Strength distribution

The set of node strength values across the entire network.

### Betweenness centrality

A node-level measure of how often a keyword lies on shortest paths between other
keywords. A high value can indicate a bridging term between thematic areas.

### Closeness centrality

A node-level measure based on the distance from one keyword to the other
keywords. Higher closeness generally means a keyword can reach the rest of the
network through relatively short paths.

### Average degree

The mean degree of all nodes in the graph.

### Average strength

The mean weighted strength of all nodes in the graph.

### Graph density

The proportion of possible edges that actually exist. An undirected graph with
every possible connection has density `1`.

### Clustering coefficient

A measure of how likely a node's neighbors are to also be connected to one
another.

### Global clustering coefficient

A graph-level summary of the network's overall tendency to form tightly
connected groups.

### Connected component

A group of nodes in which every node can reach every other node through graph
paths. A disconnected graph contains more than one component.

### Largest connected component

The component containing the greatest number of nodes. Graphlex uses it when a
diameter calculation requires a connected graph.

### Graph diameter

The longest shortest-path distance between two nodes. For a disconnected graph,
Graphlex calculates the diameter of the largest connected component.

### Community

A group of nodes that are more strongly or densely related to one another than
to the rest of the network.

### Community detection

The process of automatically identifying communities in a graph.

### Louvain algorithm

A community-detection algorithm that searches for a division of the graph that
optimises modularity.

### Modularity

A score describing how well a graph is divided into communities. Higher values
generally indicate that connections are concentrated within communities rather
than between them.

### Community assignment

The community identifier assigned to each keyword by the community-detection
algorithm.

## Outputs and execution

### Run

A single execution of the collection and analysis pipeline.

### Run archive

A timestamped, UUID-based directory containing the outputs and configuration
metadata for one run. Archived runs support reproducibility and comparison.

### Export

An output file generated by Graphlex, such as a CSV, XLSX, PNG, or GraphML
file.

### CSV

Comma-separated values text format. Graphlex uses CSV files for tabular data
such as edges, node metrics, global metrics, and community assignments.

### XLSX

The Microsoft Excel workbook format. Graphlex can use it for spreadsheet
exports, including adjacency data.

### GraphML

An XML-based graph exchange format supported by tools such as Gephi and
Cytoscape. It preserves graph nodes, edges, and edge weights for external
analysis.

### Adjacency matrix

A square table describing which nodes are connected. In Graphlex, matrix
values represent keyword co-occurrence counts.

### Spring layout

A network visualisation layout that positions connected nodes as if edges were
springs, bringing strongly related areas closer together.

### Circular layout

A network visualisation layout that places nodes around a circle. It provides a
consistent overview and makes node labels easier to compare.

### Histogram

A chart showing how numeric values are distributed. Graphlex uses histograms for
metrics such as degree, strength, and centrality.

### CLI

Command-line interface. Graphlex can be started locally with the `graphlex`
command after installation.

