# Spatial Rare Alleles

Repository to store code for simulations and empirical analyses described in: "Study design and the sampling of deleterious rare variants in biobank-scale datasets."
Please see our preprint [here](https://www.biorxiv.org/content/10.1101/2024.12.02.626424v2) for details.

[![DOI](https://zenodo.org/badge/895277147.svg)](https://doi.org/10.5281/zenodo.15398318)

## Figures

Code to produce all figures in the manuscript is available in the `figures` directory. 

## Simulations

We provide code relating to two simulation methods used in the project: branching process simulations (`bp_sims`) and SLiM simulations (`slim_sims`). The main simulation file for the branching process method is `bp_sims/source/simulations.py`. The main simulation file for the SLiM simulations is `slim_sims/scripts/rare_variant_simulation.slim`. 

## Data 

Scripts pertaining to analysis of UK Biobank WES data can be found in `empirical`. Scripts for running PCA are available in `empirical/pca`, while the pipeline for the subsampling experiments can be found in `empirical/subsampling_SIR_v20250127`.
