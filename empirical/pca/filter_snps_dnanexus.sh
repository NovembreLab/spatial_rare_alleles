#!/bin/bash

# note - log in to dnanexus before running! and go to smartpca_genotypes directory

# for each chromosome
for chrom in {1..22}; do
    echo "starting job for chrom ${chrom}"
    dx run app-swiss-army-knife -y \
        -iin=Rare\ Variants\ in\ Space:/Bulk/Genotype\ Results/Genotype\ calls/ukb22418_c${chrom}_b0_v2.bed \
        -iin=Rare\ Variants\ in\ Space:/Bulk/Genotype\ Results/Genotype\ calls/ukb22418_c${chrom}_b0_v2.bim \
        -iin=Rare\ Variants\ in\ Space:/Bulk/Genotype\ Results/Genotype\ calls/ukb22418_c${chrom}_b0_v2.fam \
        -iin=used_in_pca.tsv \
        -iin=ukb_snps_used_pca.txt \
        -icmd="plink --bfile ukb22418_c${chrom}_b0_v2 --extract ukb_snps_used_pca.txt --make-bed --recode --out c${chrom}_filtered"
done
