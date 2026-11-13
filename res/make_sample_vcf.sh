#!/bin/bash

# Rebuild res/data/subset_grch38.vep.vcf: 6 samples of the 1000 Genomes 30x high-coverage release (GRCh38),
# chr19:400,000-500,000, SNVs and indels found in these samples, annotated with Ensembl VEP.
# Needs Docker and internet access (only the region is downloaded; VEP queries Ensembl's public database).

set -e

SOURCE=http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000G_2504_high_coverage/working/20220422_3202_phased_SNV_INDEL_SV/1kGP_high_coverage_Illumina.chr19.filtered.SNV_INDEL_SV_phased_panel.vcf.gz
SAMPLES=HG00115,HG00116,HG00117,HG00118,HG00119,HG00120
REGION=chr19:400000-500000

OUT_DIR=$(cd "$(dirname "$0")/data" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
echo "chr19 19" > "$WORK/rename.txt"

# Recompute AC/AN for the 6 samples, keep sites they carry, drop source IDs and cohort-wide INFO, use "19" as chromosome name
docker run --rm --user "$(id -u):$(id -g)" -v "$WORK":/data -w /data staphb/bcftools:1.21 sh -c "
bcftools view -r $REGION -s $SAMPLES '$SOURCE' -Ou \
 | bcftools view -v snps,indels -Ou \
 | bcftools +fill-tags -Ou -- -t AC,AN \
 | bcftools view -c 1 -Ou \
 | bcftools annotate -x ID -Ou \
 | bcftools annotate -x '^INFO/AC,INFO/AN' -Ou \
 | bcftools annotate --rename-chrs rename.txt -Ov -o subset_grch38.vcf
"

docker run --rm --user "$(id -u):$(id -g)" -v "$WORK":/data ensemblorg/ensembl-vep:release_116.3 vep \
    --input_file /data/subset_grch38.vcf --output_file /data/subset_grch38.vep.vcf \
    --vcf --database --species homo_sapiens --assembly GRCh38 \
    --symbol --hgvs --check_existing --force_overwrite --no_stats

cp "$WORK/subset_grch38.vep.vcf" "$OUT_DIR/subset_grch38.vep.vcf"
echo "Written $OUT_DIR/subset_grch38.vep.vcf"
