suppressPackageStartupMessages({
  library(DESeq2)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("usage: Rscript scripts/v04_real_de.R <run_dir>")
run_dir <- normalizePath(args[[1]], mustWork = TRUE)

read_json <- function(name) {
  path <- file.path(run_dir, name)
  if (!file.exists(path)) stop(paste("missing required run artifact:", name))
  fromJSON(path, simplifyVector = FALSE)
}

marker <- read_json("PRE_OUTCOME_LOCK_COMPLETE.json")
manifest <- read_json("manifest.json")
freeze <- read_json("dataset_freeze.json")
lock <- read_json("analysis_lock.json")

if (!identical(marker$pre_outcome_boundary, "COMPLETE")) stop("pre-outcome lock marker is not COMPLETE")
if (!identical(marker$count_rows_inspected, FALSE)) stop("pre-outcome marker indicates count rows were inspected before lock")
if (!identical(marker$analysis_lock_sha256, lock$analysis_lock_sha256)) stop("analysis-lock marker mismatch")
if (!identical(marker$dataset_freeze_sha256, freeze$freeze_sha256)) stop("dataset-freeze marker mismatch")
if (!identical(manifest$analysis$de_method, "DESeq2")) stop("manifest does not lock DESeq2")
if (!identical(manifest$analysis$independent_filtering, FALSE)) stop("v0.4 requires DESeq2 independent filtering disabled")
if (!identical(manifest$analysis$cooks_cutoff, FALSE)) stop("v0.4 requires Cook's-distance result exclusion disabled")
if (!identical(manifest$analysis$outlier_policy, "report_not_exclude")) stop("v0.4 outlier policy mismatch")

asset_for <- function(asset_id) {
  matches <- Filter(function(x) identical(x$asset_id, asset_id), freeze$assets)
  if (length(matches) != 1) stop(paste("frozen asset lookup failed:", asset_id))
  path <- file.path(run_dir, freeze$asset_paths[[asset_id]])
  if (!file.exists(path)) stop(paste("frozen asset file missing:", path))
  path
}

read_featurecounts <- function(asset_id, group_name, expected_reps) {
  path <- asset_for(asset_id)
  tab <- read.delim(gzfile(path), check.names = FALSE, stringsAsFactors = FALSE)
  if (!("Geneid" %in% names(tab))) stop(paste(asset_id, "has no Geneid column"))
  annotation_cols <- intersect(c("Geneid", "Chr", "Start", "End", "Strand", "Length"), names(tab))
  count_cols <- setdiff(names(tab), annotation_cols)
  if (length(count_cols) != expected_reps) {
    stop(paste(asset_id, "expected", expected_reps, "sample-count columns but found", length(count_cols), paste(count_cols, collapse = ",")))
  }
  if (anyDuplicated(tab$Geneid)) stop(paste(asset_id, "contains duplicate Geneid values"))
  counts <- as.matrix(tab[, count_cols, drop = FALSE])
  storage.mode(counts) <- "numeric"
  if (anyNA(counts) || any(!is.finite(counts))) stop(paste(asset_id, "contains missing/non-finite counts"))
  if (any(counts < 0)) stop(paste(asset_id, "contains negative counts"))
  if (any(abs(counts - round(counts)) > 1e-8)) stop(paste(asset_id, "contains non-integer counts"))
  storage.mode(counts) <- "integer"
  colnames(counts) <- paste0(gsub("[^A-Za-z0-9]+", "_", group_name), "_rep", seq_len(ncol(counts)))
  list(gene = as.character(tab$Geneid), counts = counts)
}

groups <- manifest$contrast$groups
if (length(groups) != 2) stop("exactly two groups are required")
left <- read_featurecounts(groups[[1]]$asset_id, groups[[1]]$name, groups[[1]]$expected_replicates)
right <- read_featurecounts(groups[[2]]$asset_id, groups[[2]]$name, groups[[2]]$expected_replicates)

if (!setequal(left$gene, right$gene)) stop("featureCounts gene universes differ across frozen assets")
if (!identical(left$gene, right$gene)) {
  order_right <- match(left$gene, right$gene)
  if (anyNA(order_right)) stop("failed to align featureCounts gene order by Geneid")
  right$gene <- right$gene[order_right]
  right$counts <- right$counts[order_right, , drop = FALSE]
}
if (!identical(left$gene, right$gene)) stop("featureCounts Geneid alignment failed")

count_matrix <- cbind(left$counts, right$counts)
rownames(count_matrix) <- left$gene

prefilter <- as.integer(manifest$analysis$prefilter_total_count)
keep <- rowSums(count_matrix) >= prefilter
if (!any(keep)) stop("locked prefilter removed all genes")
count_matrix <- count_matrix[keep, , drop = FALSE]

reference <- manifest$contrast$reference
numerator <- manifest$contrast$numerator
genotype <- factor(c(rep(groups[[1]]$name, ncol(left$counts)), rep(groups[[2]]$name, ncol(right$counts))), levels = c(reference, numerator))
if (anyNA(genotype)) stop("contrast group names do not match locked reference/numerator")
col_data <- data.frame(genotype = genotype, row.names = colnames(count_matrix), check.names = FALSE)

dds <- DESeqDataSetFromMatrix(countData = count_matrix, colData = col_data, design = ~ genotype)
dds <- DESeq(dds, quiet = TRUE)
res <- results(
  dds,
  contrast = c("genotype", numerator, reference),
  alpha = as.numeric(manifest$analysis$fdr_threshold),
  independentFiltering = FALSE,
  cooksCutoff = FALSE,
  pAdjustMethod = "BH"
)

res_df <- as.data.frame(res)
res_df$Geneid <- rownames(res_df)
res_df <- res_df[, c("Geneid", setdiff(names(res_df), "Geneid"))]

out_dir <- file.path(run_dir, "results")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(res_df, file.path(out_dir, "deseq2_all_genes.csv"), row.names = FALSE, na = "")

fdr <- as.numeric(manifest$analysis$fdr_threshold)
effect <- as.numeric(manifest$analysis$effect_threshold_for_enrichment)
sig <- !is.na(res_df$padj) & res_df$padj <= fdr & abs(res_df$log2FoldChange) >= effect
up <- sig & res_df$log2FoldChange > 0
down <- sig & res_df$log2FoldChange < 0
write.csv(res_df[sig, , drop = FALSE], file.path(out_dir, "deseq2_enrichment_candidates.csv"), row.names = FALSE, na = "")

vsd <- vst(dds, blind = FALSE)
pca <- plotPCA(vsd, intgroup = "genotype", returnData = TRUE)
pca$sample <- rownames(pca)
write.csv(pca, file.path(out_dir, "pca_coordinates.csv"), row.names = FALSE)

cooks <- assays(dds)[["cooks"]]
finite_cooks <- cooks[is.finite(cooks)]
cooks_diag <- list(
  available = !is.null(cooks),
  finite_values = length(finite_cooks),
  maximum = if (length(finite_cooks)) max(finite_cooks) else NULL,
  median = if (length(finite_cooks)) median(finite_cooks) else NULL,
  action = "reported_not_excluded"
)

summary <- list(
  scenario_id = manifest$scenario_id,
  capability_only = TRUE,
  method = "DESeq2",
  design = "~ genotype",
  contrast = paste0(numerator, " vs ", reference),
  independent_filtering = FALSE,
  cooks_cutoff = FALSE,
  outlier_policy = "report_not_exclude",
  p_adjust_method = "BH",
  fdr_threshold = fdr,
  enrichment_effect_threshold_abs_log2fc = effect,
  genes_before_prefilter = length(keep),
  genes_after_prefilter = sum(keep),
  samples = ncol(count_matrix),
  replicates_per_group = c(setNames(list(ncol(left$counts)), groups[[1]]$name), setNames(list(ncol(right$counts)), groups[[2]]$name)),
  significant_for_enrichment = sum(sig),
  up_for_enrichment = sum(up),
  down_for_enrichment = sum(down),
  size_factors = as.list(setNames(as.numeric(sizeFactors(dds)), names(sizeFactors(dds)))),
  cooks_distance_diagnostic = cooks_diag,
  analysis_lock_sha256 = lock$analysis_lock_sha256,
  dataset_freeze_sha256 = freeze$freeze_sha256,
  status = "PASS"
)
write(toJSON(summary, auto_unbox = TRUE, pretty = TRUE, null = "null"), file.path(out_dir, "deseq2_summary.json"))
cat(toJSON(summary, auto_unbox = TRUE, pretty = TRUE), "\n")
