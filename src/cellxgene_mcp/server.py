#!/usr/bin/env python3
"""CELLxGENE Census MCP Server - Query interface for CELLxGENE Census single-cell data."""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import sys
import argparse
import tempfile
import json

from fastmcp import FastMCP
from pydantic import BaseModel, Field
from eliot import start_action
import cellxgene_census
import pandas as pd
import numpy as np
from anndata import AnnData

# Configuration
DEFAULT_HOST = os.getenv("MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("MCP_PORT", "3001"))
DEFAULT_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")

class QueryResult(BaseModel):
    """Result from a Census query."""
    rows: List[Dict[str, Any]] = Field(description="Query result rows")
    count: int = Field(description="Number of rows returned")
    query_info: Dict[str, Any] = Field(description="Information about the query that was executed")

class CensusManager:
    """Manages CELLxGENE Census connections and queries."""
    
    def __init__(self, census_version: Optional[str] = None):
        self.census_version = census_version
        self._census = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._census:
            self._census.close()
    
    @asynccontextmanager
    async def get_census(self):
        """Get a Census connection."""
        try:
            census = cellxgene_census.open_soma(census_version=self.census_version)
            yield census
        finally:
            if census:
                census.close()
    
    async def get_obs_metadata(
        self, 
        organism: str = "Homo sapiens",
        value_filter: Optional[str] = None,
        column_names: Optional[List[str]] = None,
        limit: int = 1000
    ) -> QueryResult:
        """Get observation (cell) metadata from Census."""
        with start_action(action_type="get_obs_metadata", organism=organism, value_filter=value_filter) as action:
            try:
                async with self.get_census() as census:
                    obs_df = cellxgene_census.get_obs(
                        census=census,
                        organism=organism,
                        value_filter=value_filter,
                        column_names=column_names
                    )
                    
                    # Limit results to prevent memory issues
                    if len(obs_df) > limit:
                        obs_df = obs_df.head(limit)
                        action.log(message_type="result_limited", original_count=len(obs_df), limited_count=limit)
                    
                    # Convert to list of dictionaries
                    rows = obs_df.to_dict('records')
                    
                    result = QueryResult(
                        rows=rows,
                        count=len(rows),
                        query_info={
                            "organism": organism,
                            "value_filter": value_filter,
                            "column_names": column_names,
                            "limited": len(obs_df) > limit
                        }
                    )
                    
                    action.add_success_fields(rows_count=len(rows))
                    return result
            except Exception as e:
                action.log(message_type="query_failed", error=str(e))
                raise
    
    async def get_var_metadata(
        self, 
        organism: str = "Homo sapiens",
        value_filter: Optional[str] = None,
        column_names: Optional[List[str]] = None,
        limit: int = 1000
    ) -> QueryResult:
        """Get variable (gene) metadata from Census."""
        with start_action(action_type="get_var_metadata", organism=organism, value_filter=value_filter) as action:
            try:
                async with self.get_census() as census:
                    var_df = cellxgene_census.get_var(
                        census=census,
                        organism=organism,
                        value_filter=value_filter,
                        column_names=column_names
                    )
                    
                    # Limit results to prevent memory issues
                    if len(var_df) > limit:
                        var_df = var_df.head(limit)
                        action.log(message_type="result_limited", original_count=len(var_df), limited_count=limit)
                    
                    # Convert to list of dictionaries
                    rows = var_df.to_dict('records')
                    
                    result = QueryResult(
                        rows=rows,
                        count=len(rows),
                        query_info={
                            "organism": organism,
                            "value_filter": value_filter,
                            "column_names": column_names,
                            "limited": len(var_df) > limit
                        }
                    )
                    
                    action.add_success_fields(rows_count=len(rows))
                    return result
            except Exception as e:
                action.log(message_type="query_failed", error=str(e))
                raise
    
    async def get_anndata_slice(
        self,
        organism: str = "Homo sapiens",
        obs_value_filter: Optional[str] = None,
        var_value_filter: Optional[str] = None,
        obs_column_names: Optional[List[str]] = None,
        var_column_names: Optional[List[str]] = None,
        max_cells: int = 10000,
        max_genes: int = 2000
    ) -> Dict[str, Any]:
        """Get a slice of Census data as AnnData summary."""
        with start_action(action_type="get_anndata_slice", organism=organism) as action:
            try:
                async with self.get_census() as census:
                    # Get a slice of the data
                    adata = cellxgene_census.get_anndata(
                        census=census,
                        organism=organism,
                        obs_value_filter=obs_value_filter,
                        var_value_filter=var_value_filter,
                        column_names={
                            "obs": obs_column_names,
                            "var": var_column_names
                        } if obs_column_names or var_column_names else None
                    )
                    
                    # Limit the data size
                    if adata.n_obs > max_cells:
                        adata = adata[:max_cells, :]
                        action.log(message_type="cells_limited", original_count=adata.n_obs, limited_count=max_cells)
                    
                    if adata.n_vars > max_genes:
                        adata = adata[:, :max_genes]
                        action.log(message_type="genes_limited", original_count=adata.n_vars, limited_count=max_genes)
                    
                    # Return summary information instead of raw data
                    result = {
                        "n_obs": adata.n_obs,
                        "n_vars": adata.n_vars,
                        "obs_columns": list(adata.obs.columns),
                        "var_columns": list(adata.var.columns),
                        "obs_sample": adata.obs.head(5).to_dict('records') if adata.n_obs > 0 else [],
                        "var_sample": adata.var.head(5).to_dict('records') if adata.n_vars > 0 else [],
                        "query_info": {
                            "organism": organism,
                            "obs_value_filter": obs_value_filter,
                            "var_value_filter": var_value_filter,
                            "cells_limited": adata.n_obs == max_cells,
                            "genes_limited": adata.n_vars == max_genes
                        }
                    }
                    
                    action.add_success_fields(n_obs=adata.n_obs, n_vars=adata.n_vars)
                    return result
            except Exception as e:
                action.log(message_type="query_failed", error=str(e))
                raise

class CellxGeneMCP(FastMCP):
    """CELLxGENE Census MCP Server with Census query tools."""
    
    def __init__(
        self, 
        name: str = "CELLxGENE Census MCP Server",
        census_version: Optional[str] = None,
        prefix: str = "cellxgene_",
        **kwargs
    ):
        """Initialize the CELLxGENE Census MCP server."""
        super().__init__(name=name, **kwargs)
        
        self.census_manager = CensusManager(census_version=census_version)
        self.prefix = prefix
        
        # Register tools and resources
        self._register_cellxgene_tools()
        self._register_cellxgene_resources()
    
    def _register_cellxgene_tools(self):
        """Register CELLxGENE Census-specific tools."""
        self.tool(
            name=f"{self.prefix}get_census_info", 
            description="Get information about available Census versions and organisms"
        )(self.get_census_info)
        
        self.tool(
            name=f"{self.prefix}get_obs_metadata", 
            description="Get cell (observation) metadata from CELLxGENE Census. Use this to explore available cell types, tissues, diseases, etc."
        )(self.get_obs_metadata)
        
        self.tool(
            name=f"{self.prefix}get_var_metadata", 
            description="Get gene (variable) metadata from CELLxGENE Census. Use this to explore available genes and their annotations."
        )(self.get_var_metadata)
        
        self.tool(
            name=f"{self.prefix}get_data_slice", 
            description="Get a summary of a data slice from CELLxGENE Census based on cell and gene filters. Returns data dimensions and sample metadata."
        )(self.get_data_slice)
        
        self.tool(
            name=f"{self.prefix}get_all_cell_types", 
            description="Get all distinct cell types available in CELLxGENE Census for a specific organism. Optionally includes cell counts for each type."
        )(self.get_all_cell_types)
    
    def _register_cellxgene_resources(self):
        """Register CELLxGENE Census-specific resources."""
        
        @self.resource(f"resource://{self.prefix}census-info")
        def get_census_resource() -> str:
            """
            Get information about the CELLxGENE Census database.
            
            This resource contains information about:
            - Available Census versions
            - Supported organisms
            - Data schema and available metadata fields
            - Usage guidelines for querying the Census
            
            Returns:
                Information about the Census database
            """
            return """
CELLxGENE Census Information:

The CELLxGENE Census is a comprehensive collection of single-cell RNA sequencing data from CZ CELLxGENE Discover.

Available Organisms:
- "Homo sapiens" (human)
- "Mus musculus" (mouse)

Key Metadata Fields:
Observation (cell) metadata:
- cell_type: Cell type annotation
- tissue: Tissue of origin
- disease: Disease state
- sex: Biological sex
- organism: Species
- assay: Sequencing assay used
- suspension_type: Cell or nucleus
- ethnicity: Self-reported ethnicity (human only)
- development_stage: Developmental stage

Variable (gene) metadata:
- feature_id: Ensembl gene ID
- feature_name: Gene symbol
- feature_length: Gene length

Common Query Patterns:
1. Filter by cell type: cell_type == 'T cell'
2. Filter by tissue: tissue == 'lung'
3. Filter by disease: disease == 'COVID-19'
4. Combine filters: cell_type == 'T cell' and tissue == 'lung'
5. Filter genes: feature_name in ['CD4', 'CD8A', 'CD3E']

Note: Queries can return large amounts of data. Use filters to limit results.
"""
    
    async def get_census_info(self) -> Dict[str, Any]:
        """Get information about available Census versions and organisms."""
        with start_action(action_type="get_census_info") as action:
            try:
                # Get available Census versions
                versions = cellxgene_census.get_census_version_directory()
                
                # Get information about the current/latest version
                latest_version = None
                if versions:
                    # Find the latest stable version
                    stable_versions = [v for v in versions if v.get('flags', {}).get('lts', False)]
                    if stable_versions:
                        latest_version = stable_versions[-1]['release_build']
                    else:
                        latest_version = versions[-1]['release_build']
                
                # Actually open Census to get real information
                async with self.census_manager.get_census() as census:
                    # Get actual organisms available in the Census
                    organisms = list(census["census_data"].keys())
                    
                    # Get summary statistics for each organism
                    organism_stats = {}
                    total_cells = 0
                    
                    for organism in organisms:
                        try:
                            # Get basic stats for this organism
                            exp = census["census_data"][organism]
                            
                            # Get a small sample to determine available columns and data types
                            obs_sample = exp.obs.read(column_names=None).concat().to_pandas().head(1)
                            var_sample = exp.var.read(column_names=None).concat().to_pandas().head(1)
                            
                            # Count total cells and genes for this organism
                            obs_count = len(exp.obs.read(column_names=["soma_joinid"]).concat().to_pandas())
                            var_count = len(exp.var.read(column_names=["soma_joinid"]).concat().to_pandas())
                            
                            total_cells += obs_count
                            
                            organism_stats[organism] = {
                                "total_cells": obs_count,
                                "total_genes": var_count,
                                "obs_columns": list(obs_sample.columns) if not obs_sample.empty else [],
                                "var_columns": list(var_sample.columns) if not var_sample.empty else []
                            }
                        except Exception as org_error:
                            action.log(message_type="organism_query_failed", organism=organism, error=str(org_error))
                            organism_stats[organism] = {"error": str(org_error)}
                    
                    # Try to get summary info if available
                    summary_info = {}
                    try:
                        if "census_info" in census and "summary" in census["census_info"]:
                            summary_df = census["census_info"]["summary"].read().concat().to_pandas()
                            summary_info = dict(zip(summary_df["label"], summary_df["value"]))
                    except Exception as summary_error:
                        action.log(message_type="summary_query_failed", error=str(summary_error))
                    
                    result = {
                        "available_versions": [v['release_build'] for v in versions] if versions else [],
                        "latest_stable_version": latest_version,
                        "supported_organisms": organisms,
                        "organism_statistics": organism_stats,
                        "total_cells_across_organisms": total_cells,
                        "census_summary": summary_info,
                        "version_info": versions if versions else []
                    }
                
                action.add_success_fields(
                    versions_count=len(versions) if versions else 0,
                    organisms_count=len(organisms),
                    total_cells=total_cells
                )
                return result
                
            except Exception as e:
                action.log(message_type="query_failed", error=str(e))
                raise
    
    async def get_obs_metadata(
        self,
        organism: str = "Homo sapiens",
        value_filter: Optional[str] = None,
        column_names: Optional[str] = None,
        limit: int = 1000
    ) -> QueryResult:
        """Get cell (observation) metadata from Census."""
        # Parse column names if provided as comma-separated string
        columns = None
        if column_names:
            columns = [col.strip() for col in column_names.split(',')]
        
        return await self.census_manager.get_obs_metadata(
            organism=organism,
            value_filter=value_filter,
            column_names=columns,
            limit=limit
        )
    
    async def get_var_metadata(
        self,
        organism: str = "Homo sapiens",
        value_filter: Optional[str] = None,
        column_names: Optional[str] = None,
        limit: int = 1000
    ) -> QueryResult:
        """Get gene (variable) metadata from Census."""
        # Parse column names if provided as comma-separated string
        columns = None
        if column_names:
            columns = [col.strip() for col in column_names.split(',')]
        
        return await self.census_manager.get_var_metadata(
            organism=organism,
            value_filter=value_filter,
            column_names=columns,
            limit=limit
        )
    
    async def get_data_slice(
        self,
        organism: str = "Homo sapiens",
        obs_value_filter: Optional[str] = None,
        var_value_filter: Optional[str] = None,
        obs_column_names: Optional[str] = None,
        var_column_names: Optional[str] = None,
        max_cells: int = 10000,
        max_genes: int = 2000
    ) -> Dict[str, Any]:
        """Get a summary of a data slice from Census."""
        # Parse column names if provided as comma-separated strings
        obs_columns = None
        if obs_column_names:
            obs_columns = [col.strip() for col in obs_column_names.split(',')]
        
        var_columns = None
        if var_column_names:
            var_columns = [col.strip() for col in var_column_names.split(',')]
        
        return await self.census_manager.get_anndata_slice(
            organism=organism,
            obs_value_filter=obs_value_filter,
            var_value_filter=var_value_filter,
            obs_column_names=obs_columns,
            var_column_names=var_columns,
            max_cells=max_cells,
            max_genes=max_genes
        )
    
    async def get_all_cell_types(
        self,
        organism: str = "Homo sapiens",
        include_counts: bool = False,
        primary_data_only: bool = True
    ) -> Dict[str, Any]:
        """Get all distinct cell types from Census."""
        with start_action(action_type="get_all_cell_types", organism=organism) as action:
            try:
                async with self.census_manager.get_census() as census:
                    # Build value filter
                    value_filter = None
                    if primary_data_only:
                        value_filter = "is_primary_data == True"
                    
                    # Get cell type data
                    obs_df = cellxgene_census.get_obs(
                        census=census,
                        organism=organism,
                        column_names=["cell_type"],
                        value_filter=value_filter
                    )
                    
                    # Get unique cell types
                    unique_cell_types = obs_df['cell_type'].unique().tolist()
                    unique_cell_types.sort()  # Sort alphabetically
                    
                    result = {
                        "organism": organism,
                        "cell_types": unique_cell_types,
                        "total_unique_cell_types": len(unique_cell_types),
                        "primary_data_only": primary_data_only
                    }
                    
                    # Optionally include counts
                    if include_counts:
                        cell_type_counts = obs_df['cell_type'].value_counts()
                        result["cell_type_counts"] = cell_type_counts.to_dict()
                        result["top_10_cell_types"] = cell_type_counts.head(10).to_dict()
                    
                    action.add_success_fields(
                        unique_cell_types_count=len(unique_cell_types),
                        total_cells=len(obs_df)
                    )
                    return result
                    
            except Exception as e:
                action.log(message_type="query_failed", error=str(e))
                raise

def cli_app():
    """CLI application for HTTP transport."""
    parser = argparse.ArgumentParser(description="CELLxGENE Census MCP Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--census-version", help="Specific Census version to use")
    args = parser.parse_args()
    
    server = CellxGeneMCP(census_version=args.census_version)
    server.run(transport="fastapi", host=args.host, port=args.port)

def cli_app_stdio():
    """CLI application for stdio transport."""
    parser = argparse.ArgumentParser(description="CELLxGENE Census MCP Server (stdio)")
    parser.add_argument("--census-version", help="Specific Census version to use")
    args = parser.parse_args()
    
    server = CellxGeneMCP(census_version=args.census_version)
    server.run(transport="stdio")

def cli_app_sse():
    """CLI application for SSE transport."""
    parser = argparse.ArgumentParser(description="CELLxGENE Census MCP Server (SSE)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--census-version", help="Specific Census version to use")
    args = parser.parse_args()
    
    server = CellxGeneMCP(census_version=args.census_version)
    server.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    cli_app_stdio() 