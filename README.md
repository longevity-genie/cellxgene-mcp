# CELLxGENE Census MCP Server

A Model Context Protocol (MCP) server that provides access to the [CZ CELLxGENE Discover Census](https://chanzuckerberg.github.io/cellxgene-census/) - a comprehensive collection of single-cell RNA sequencing data.

## Features

- 🧬 **Query cell metadata**: Explore cell types, tissues, diseases, and other cell annotations
- 🧫 **Query gene metadata**: Search genes and their annotations across the Census
- 📊 **Data slice summaries**: Get overview statistics of data slices without downloading full matrices
- 🔍 **Flexible filtering**: Use pandas-style queries to filter cells and genes
- 🌍 **Multi-organism support**: Access data from human and mouse
- ⚡ **Memory-efficient**: Built-in limits to prevent memory overload

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install with uv (recommended)

```bash
# Clone the repository
git clone <repository-url>
cd cellxgene-mcp

# Install dependencies
uv sync

# Install the package in development mode
uv pip install -e .
```

### Install with pip

```bash
pip install -r requirements.txt
pip install -e .
```

## Quick Start

### Running the MCP Server

#### Stdio Transport (for MCP clients)
```bash
uv run cellxgene-mcp
```

#### HTTP Transport (for web access)
```bash
uv run server --host 0.0.0.0 --port 3001
```

#### SSE Transport
```bash
uv run sse --host 0.0.0.0 --port 3001
```

### MCP Client Configuration

Add this to your MCP client configuration:

#### For stdio transport:
```json
{
  "mcpServers": {
    "cellxgene-mcp": {
      "command": "uv",
      "args": ["run", "cellxgene-mcp"]
    }
  }
}
```

#### For HTTP transport:
```json
{
  "mcpServers": {
    "cellxgene-mcp": {
      "url": "http://localhost:3001/mcp"
    }
  }
}
```

## Available Tools

### `cellxgene_get_census_info`
Get information about available Census versions and supported organisms.

**Returns:**
- Available Census versions
- Latest stable version
- Supported organisms
- Data types

### `cellxgene_get_obs_metadata`
Query cell (observation) metadata from the Census.

**Parameters:**
- `organism` (str): "Homo sapiens" or "Mus musculus" (default: "Homo sapiens")
- `value_filter` (str, optional): Pandas-style filter expression
- `column_names` (str, optional): Comma-separated list of columns to return
- `limit` (int): Maximum number of rows to return (default: 1000)

**Example filters:**
```
cell_type == 'T cell'
tissue == 'lung' and disease == 'COVID-19'
sex == 'female' and cell_type in ['T cell', 'B cell']
```

### `cellxgene_get_var_metadata`
Query gene (variable) metadata from the Census.

**Parameters:**
- `organism` (str): "Homo sapiens" or "Mus musculus" (default: "Homo sapiens")
- `value_filter` (str, optional): Pandas-style filter expression
- `column_names` (str, optional): Comma-separated list of columns to return
- `limit` (int): Maximum number of rows to return (default: 1000)

**Example filters:**
```
feature_name in ['CD4', 'CD8A', 'CD3E']
feature_id == 'ENSG00000010610'
```

### `cellxgene_get_data_slice`
Get a summary of a data slice from the Census.

**Parameters:**
- `organism` (str): "Homo sapiens" or "Mus musculus"
- `obs_value_filter` (str, optional): Filter for cells
- `var_value_filter` (str, optional): Filter for genes
- `obs_column_names` (str, optional): Cell metadata columns to include
- `var_column_names` (str, optional): Gene metadata columns to include
- `max_cells` (int): Maximum number of cells (default: 10000)
- `max_genes` (int): Maximum number of genes (default: 2000)

**Returns:**
- Number of cells and genes
- Sample metadata
- Column information
- Query information

## Available Resources

### `resource://cellxgene_census-info`
Comprehensive information about the CELLxGENE Census database, including:
- Available organisms
- Key metadata fields
- Common query patterns
- Usage guidelines

## Data Schema

### Cell (Observation) Metadata Fields
- `cell_type`: Cell type annotation
- `tissue`: Tissue of origin  
- `disease`: Disease state
- `sex`: Biological sex
- `organism`: Species
- `assay`: Sequencing assay used
- `suspension_type`: Cell or nucleus
- `ethnicity`: Self-reported ethnicity (human only)
- `development_stage`: Developmental stage

### Gene (Variable) Metadata Fields
- `feature_id`: Ensembl gene ID
- `feature_name`: Gene symbol
- `feature_length`: Gene length

## Example Queries

### Explore T cells in lung tissue
```python
# Get T cells from lung tissue
obs_data = await get_obs_metadata(
    organism="Homo sapiens",
    value_filter="cell_type == 'T cell' and tissue == 'lung'",
    column_names="cell_type,tissue,disease,sex,assay"
)
```

### Find COVID-19 related data
```python
# Get cells from COVID-19 studies
obs_data = await get_obs_metadata(
    organism="Homo sapiens", 
    value_filter="disease == 'COVID-19'",
    column_names="cell_type,tissue,disease,assay"
)
```

### Search for specific genes
```python
# Get information about immune genes
var_data = await get_var_metadata(
    organism="Homo sapiens",
    value_filter="feature_name in ['CD4', 'CD8A', 'CD3E', 'IL2']",
    column_names="feature_id,feature_name,feature_length"
)
```

### Get data slice summary
```python
# Get summary of T cell data slice
data_summary = await get_data_slice(
    organism="Homo sapiens",
    obs_value_filter="cell_type == 'T cell'",
    var_value_filter="feature_name in ['CD4', 'CD8A', 'CD3E']",
    max_cells=5000,
    max_genes=100
)
```

## Development

### Project Structure
```
cellxgene-mcp/
├── src/cellxgene_mcp/
│   ├── __init__.py
│   └── server.py
├── test/
├── mcp-config*.json
├── pyproject.toml
└── README.md
```

### Running Tests
```bash
uv run pytest test/
```

### Code Formatting
```bash
uv run ruff format .
uv run ruff check .
```

## Limitations

- **Memory limits**: Built-in limits prevent downloading extremely large datasets
- **Query complexity**: Very complex queries may be slow
- **Rate limiting**: Respect Census service rate limits
- **Network dependency**: Requires internet connection to access Census data

## Related Projects

- [CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/)
- [FastMCP](https://github.com/pydantic/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## License

MIT License - see LICENSE file for details.

## Support

- File issues on the GitHub repository
- Check the [CELLxGENE Census documentation](https://chanzuckerberg.github.io/cellxgene-census/) for data questions
- Review the [MCP specification](https://spec.modelcontextprotocol.io/) for protocol questions 