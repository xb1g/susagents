# SustainGraph

ARSINOE SustainGraph is a Knowledge Graph developed to track information related to the evolution of targets defined in the United Nations Sustainable Development Goals (SDGs) at national and regional level. The SustainGraph aims to act as a unified source of knowledge around information related to the SDGs, by taking advantage of the power provided by the development of graph databases and the exploitation of Machine Learning (ML) techniques for data population, knowledge production and analysis.

## Prerequisites

Install Neo4j Enterprise Edition 5.16.0.

Install [APOC 5](https://neo4j.com/labs/apoc/).16.1 Core (Awesome Procedures on Neo4j) plugin.  APOC (Awesome Procedures on Neo4j) contains more than 450 procedures and functions providing functionality for utilities, conversions, graph updates, and more. We’re going to use this tool to scrape web pages and apply NLP techniques on text data.

This repository contains jupyter notebooks for the different entities of the SustainGraph and the import of data by using the official neo4j python driver. The requirements.txt file contains all the dependencies of the python packages used in the Jupyter notebooks. Python version used: 3.11 / 3.10.15 

## Cite

To cite this work, please use:

Fotopoulou E, Mandilara I, Zafeiropoulos A, Laspidou C, Adamos G, Koundouri P and Papavassiliou S (2022) SustainGraph: A knowledge graph for tracking the progress and the interlinking among the sustainable development goals’ targets. Front. Environ. Sci. 10:1003599. doi: [10.3389/fenvs.2022.1003599](https://www.frontiersin.org/articles/10.3389/fenvs.2022.1003599/full)

Available in Zenodo: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7984797.svg)](https://doi.org/10.5281/zenodo.7984797)

## Contact us

For any request for detailed information or expression of interest for participating at this initiative, you may contact:

- Anastasios Zafeiropoulos - tzafeir (at) cn (dot) ntua (dot) gr
- Eleni Fotopoulou - efotopoulou (at) netmode (dot) ntua (dot) gr
- Ioanna Mandilara - ioannamand (at) netmode (dot) ntua (dot) gr
- Christina Maria Androna - andronaxm (at) netmode (dot) ntua (dot) gr
