# Use the official Neo4j Enterprise Edition image as the base image
# FROM neo4j:5.16-enterprise
FROM neo4j:2025.11.2-enterprise

# Set environment variables
ENV NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
# ENV NEO4J_AUTH=neo4j/${SUSTAINGRAPH_PASSWORD}
ENV NEO4J_apoc_export_file_enabled=true
ENV NEO4J_apoc_import_file_enabled=true
ENV NEO4J_apoc_import_file_use__neo4j__config=true
# ENV NEO4J_PLUGINS=["apoc", "graph-data-science"]

# Copy the data from the previous instance into the image
# COPY ./Data/data/databases /data/databases
# The key path should be added to the .conf file of neo4j
COPY neo4j_backup/2024/neo4j.dump .
#Keys for enterprise edition
COPY ./keys/neo4j-bloom-server-keyfile.txt usr/share/neo4j/
COPY ./keys/neo4j-gds-keyfile.txt usr/share/neo4j/

# Expose the ports for HTTP (7474), Bolt (7687), and HTTPS (7473)
EXPOSE 7474 7687 7473

CMD ["neo4j", "console"]