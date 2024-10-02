import streamlit as st
import networkx as nx
from pyvis.network import Network  # type: ignore
import re
import random
import google.generativeai as genai  # type: ignore
import json
import pandas as pd
from tabula import read_pdf  # type: ignore
 
st.set_page_config(layout="wide")
# Configuration
api_key = "AIzaSyC2_5wdKNKFbjttRG1yJpfPt-y_JLmh5Lo"  # Ensure API_KEY is set in your environment variables
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")
 
# Function to generate a random color in hex format
def random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))
 
# Function to parse nodes and relationships from the Cypher data
def parse_cypher(cypher):
    nodes = set()
    edges = []
     
    # Regex to match nodes and relationships
    node_pattern = r"\((\w+):(\w+) {.*?}\)"
    relationship_pattern = r"\((\w+)\)-\[:(\w+)(?: {.*?})?\]->\((\w+)\)"
 
    # Extract nodes
    for match in re.findall(node_pattern, cypher):
        node_name, node_type = match
        nodes.add((node_name, node_type))
 
    # Extract edges
    for match in re.findall(relationship_pattern, cypher):
        start_node, rel_type, end_node = match
        edges.append((start_node, end_node, rel_type))
     
    return list(nodes), edges
 
# Function to read unstructured data from files
def read_unstructured_files(uploaded_files):
    all_data = []
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.json'):
            all_data.append(json.load(uploaded_file))  # Read JSON file directly
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)  # Read CSV file directly
            all_data.extend(df.to_dict(orient='records'))  # Convert DataFrame to list of dictionaries
        elif uploaded_file.name.endswith('.pdf'):
            try:
                dfs = read_pdf(uploaded_file, pages='all', multiple_tables=True)
                for df in dfs:
                    all_data.extend(df.to_dict(orient='records'))
            except Exception as e:
                raise ValueError(f"Error reading PDF: {e}")
        else:
            raise ValueError("Unsupported file format. Please provide a JSON, CSV, or PDF file.")
    return all_data
 
# Generate Cypher queries using Google Generative AI
def generate_cypher_queries(unstructured_data):
    unstructured_data_str = json.dumps(unstructured_data, indent=2)
    prompt = (
        "Analyze the following unstructured data to identify main class node, other nodes, relationships. "
        "Don't create much properties, just connect them via relationships with the nodes. "
        "Take full name of the nodes for better graph visualisation. "
        "Keep the main focus only on Nodes and Edges. "
        "Important -- Make sure to find out the parent node and relationships between all nodes intelligently if the prompt specific relationship are not present"
        f"Unstructured Data:\n{unstructured_data_str}\n\n"
        "Important -- Make sure each node should be a dictionary with at least an id and a label. "
        "Important -- Always ensure edges and nodes are present in the cypher queries and are connected "
        "There should always be a parent class which should be connected to the main child nodes, for example - Main class is Vehicle which is connected to all other car brands. "
        "All car brands should be connected to their cars, the cars must be connected with the battery. "
        "Battery values must be connected with the cars with relations. "
        "Make sure all values in the data which are important are used in the cypher queries. "
        "Don't use unwind and only provide cypher queries, do not provide any kind of explanation. "
        "MATCH and CREATE should be in the same line like this: CREATE(charlie:Person {name: 'Charlie Sheen'}), (charlie)-[:ACTED_IN {role: 'Bud Fox'}]->(wallStreet)."
    )
    response = model.generate_content(prompt)
    return response.text.strip()
 
# Generate responses to user questions using Google Generative AI
def generate_response(data, question):
    prompt = (
        "You are a chatbot that answers questions about the data. "
        "The data is as follows:\n\n"
        f"{data}\n\n"
        "The user has asked the following question:\n"
        f"{question}\n\n"
        "Please provide a detailed and accurate answer based on the data."
    )
    response = model.generate_content(prompt)
    return response.text.strip()
 
# Function to draw the graph
def draw_graph(G):
    net = Network(notebook=True, height="900px", width="100%")
    node_colors = {node_type: random_color() for node_type in set(nx.get_node_attributes(G, 'type').values())}
    edge_colors = {rel_type: random_color() for rel_type in set(nx.get_edge_attributes(G, 'relationship').values())}
 
    # Add nodes with colors
    for node_name, data in G.nodes(data=True):
        net.add_node(node_name, title=data['type'], color=node_colors[data['type']])
 
    # Add edges with colors
    for start_node, end_node, data in G.edges(data=True):
        net.add_edge(start_node, end_node, title=data['relationship'], color=edge_colors[data['relationship']])
 
    net.show("graph.html")
    return "graph.html"
 
# Streamlit app
st.title("Digital Twin")
 
# Sidebar for file upload
uploaded_files = st.sidebar.file_uploader("Upload your data files (CSV, JSON, or PDF):", type=["csv", "json", "pdf"], accept_multiple_files=True)
 
if uploaded_files:
    # Read the contents of the files
    unstructured_data = read_unstructured_files(uploaded_files)
 
    # Generate Cypher queries using the LLM
    cypher_queries = generate_cypher_queries(unstructured_data)
 
    # Parse the provided Cypher data
    nodes, edges = parse_cypher(cypher_queries)
 
    # Create a directed graph
    G = nx.DiGraph()
    for node_name, node_type in nodes:
        G.add_node(node_name, type=node_type)
    for start_node, end_node, rel_type in edges:
        G.add_edge(start_node, end_node, relationship=rel_type)
 
    # Main layout
    col1, col2 = st.columns(2)  # 50/50 split
 
    if 'graph_html' not in st.session_state:
        st.session_state.graph_html = None
 
    with col1:
        # Box for Knowledge Graph
        st.header("Knowledge Graph")
        # Button to generate the graph
        if st.button("Generate Graph"):
            # Draw and display the graph
            st.session_state.graph_html = draw_graph(G)
 
        if st.session_state.graph_html is not None:
            st.components.v1.html(open(st.session_state.graph_html, 'r').read(), height=600, width=700)
 
    with col2:
        # Box for Chatbot
        st.header("Chatbot")
        st.markdown("### Ask your questions below:")
        question = st.text_input("Enter your question:")
         
        if st.button("Ask"):
            if question:
                answer = generate_response(cypher_queries, question)
                st.write("Chatbot response:", answer)
            else:
                st.warning("Please enter a question before asking.")
 