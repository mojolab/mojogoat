# MojoGOAT - A Graph Of All Things

## Overview

GOATs help structure information semantically by taking an ontological rather than a taxonomical approach. While a taxonomical approach organizes information into hierarchical categories, an ontological approach focuses on the relationships and connections between concepts, offering greater flexibility and depth. This allows for a more flexible and relational method of organizing and querying data.

In this implementation of the GOAT, we use a "quad" as the semantic structure: `<source><story><target><date>`. Each quad represents a relationship between entities or concepts within a specific context and timestamp, enabling rich, interconnected data representations. For example, a quad might look like this: `PersonA|knows|PersonB|2025-01-05`, indicating that PersonA knows PersonB as of the specified date.

A set of quads can be represented in various formats, such as:

- A table
- A CSV file
- Plain delimited text
- A more complex data structure like JSON

The GOAT framework is designed to take these quads and facilitate their ingestion into a Neo4j graph database using Python bindings.&#x20;

## GOAT Sutras

1. **Ownership Principle**: You can own a GOAT, some GOATs, many GOATs, big GOATs, small GOATs, public GOATs, private GOATs, and so forth, but no one owns THE GOAT. The GOAT is a shared resource, open for exploration and extension.
2. **Data Integrity Principle**: GOATs will eat almost everything, but feeding them rubbish will result in a sick GOAT. This emphasizes the importance of clean, structured, and meaningful data.
3. **Scalability Principle**: When a GOAT gets too fat, make biryani. This is a metaphor for managing and scaling data effectively when the graph becomes too large or unwieldy.

## Set up the Docker image

The GOAT system uses a Docker image to simplify setup and ensure a consistent environment across different machines.

### Steps to Set Up

1. **Install Docker**

   - If you don’t have Docker installed, download and install it from [Docker’s official website](https://www.docker.com/products/docker-desktop/).

2. **Pull the Xetrapal Docker Image**

   - Open a terminal and run the following command to pull the necessary Docker image:
     ```
     docker pull -a arjunvenkatraman/xetrapal
     ```

3. **Start a Docker Container**

   - Run the following command to start a container:
     ```
     docker run -it -p8888:8888 -p5000:5000 --mount type=bind,source=$pwd/xpal-data,target=/xpal-data --mount type=bind,source=$pwd/xpal-src,target=/xpal-src arjunvenkatraman/xetrapal:latest zsh
     ```
     - `-it`: Starts the container in interactive mode with a terminal.
     - `-p8888:8888`: Maps port 8888 of the container to port 8888 on the host machine (for Jupyter Notebook access).
     - `-p5000:5000`: Maps port 5000 for REST API access.
     - `--mount`: Binds local directories (`xpal-data` and `xpal-src`) to directories inside the container, enabling data persistence and code sharing.

4. **Attach a Shell**

   - Attach a shell to the running container to access its command line.

## Run a Jupyter Notebook from the Docker Container

To interact with the GOAT system, use Jupyter Notebook for running and testing your code.

1. **Start Jupyter Notebook**

   - Inside the Docker container, run:
     ```
     jupyter notebook --allow-root --ip 0.0.0.0
     ```

2. **Access Jupyter Notebook**

   - The command output will provide a link similar to:
     ```
     http://127.0.0.1:8888/?token=<TOKEN>
     ```
   - Copy and paste this link into your web browser to open the Jupyter Notebook interface.

3. **Create a New Working Environment**

   - Navigate to the `xpal-data` directory.
   - Create a new folder for your project.
   - Create a new Jupyter Notebook file within this folder to begin your work.

## Connect to the Neo4J Database from Your Jupyter Notebook

Neo4j serves as the backbone of the GOAT system, providing a graph database for storing and querying quads. Follow these steps to set up a connection:

1. **Create a Configuration File**

   - In the `xpal-data/conf` directory, create a `.json` file with the following format:
     ```json
     {
         "database": "neo4j",
         "url": "<NEO4J DB URL>",
         "password": "<NEO4J DB PASSWORD>"
     }
     ```
   - Replace `<NEO4J DB URL>` with the URL of your Neo4j database (e.g., `bolt://localhost:7687`).
   - Replace `<NEO4J DB PASSWORD>` with the password for your Neo4j instance.

2. **Test the Connection**

   - Use your Jupyter Notebook to load this configuration file and test the connection to the Neo4j database. Ensure the credentials and URL are correct to avoid connection issues.

## Set up a Neo4J Free Instance

Neo4j offers a free instance for small-scale projects and experimentation. You can set it up locally or use a cloud-hosted option:

1. **Local Installation**


__Note: Local installations are very hard to maintain and resource intensive to boot__
   - Download Neo4j from [Neo4j’s official website](https://neo4j.com/download/).
   - Follow the installation instructions for your operating system.

2. **Cloud Option**

   - Use Neo4j Aura, a cloud-hosted version of Neo4j, which provides a free tier for basic usage. Sign up at [Neo4j Aura](https://neo4j.com/cloud/aura/).

3. **Configure and Start**

   - For local setups, start the Neo4j server and ensure it’s running on the default Bolt protocol (`bolt://localhost:7687`).
   - For cloud setups, use the provided connection details.

By completing these steps, you’ll have a fully functional GOAT system ready to organize, query, and explore interconnected data using Neo4j and Jupyter Notebook.

