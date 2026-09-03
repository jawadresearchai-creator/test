suppressPackageStartupMessages({
  library(DESeq2)
  library(edgeR)
  library(limma)
  library(WGCNA)
})

set.seed(42)
ngenes <- 120L
nsamples <- 6L
group <- factor(rep(c("control", "treated"), each = 3))
base_mu <- runif(ngenes, 40, 300)
mu <- outer(base_mu, rep(1, nsamples))
mu[1:12, group == "treated"] <- mu[1:12, group == "treated"] * 2.2
counts <- matrix(rnbinom(ngenes * nsamples, mu = as.vector(mu), size = 12),
                 nrow = ngenes, ncol = nsamples)
rownames(counts) <- sprintf("gene%03d", seq_len(ngenes))
colnames(counts) <- sprintf("sample%d", seq_len(nsamples))
coldata <- data.frame(group = group, row.names = colnames(counts))

dds <- DESeqDataSetFromMatrix(countData = counts, colData = coldata, design = ~ group)
dds <- DESeq(dds, quiet = TRUE)
res <- results(dds, contrast = c("group", "treated", "control"))
stopifnot(nrow(res) == ngenes, all(c("log2FoldChange", "pvalue", "padj") %in% colnames(res)))

y <- DGEList(counts = counts, group = group)
y <- calcNormFactors(y)
design <- model.matrix(~ group)
y <- estimateDisp(y, design = design)
fit <- glmQLFit(y, design)
qlf <- glmQLFTest(fit, coef = 2)
stopifnot(nrow(qlf$table) == ngenes)

v <- voom(y, design, plot = FALSE)
lfit <- eBayes(lmFit(v, design))
stopifnot(nrow(lfit$coefficients) == ngenes)

vsd <- varianceStabilizingTransformation(dds, blind = TRUE)
datExpr <- t(assay(vsd))
cor_mat <- WGCNA::cor(datExpr, use = "p")
stopifnot(nrow(cor_mat) == nsamples, all(is.finite(cor_mat)))

out <- list(
  R = R.version.string,
  DESeq2 = as.character(packageVersion("DESeq2")),
  edgeR = as.character(packageVersion("edgeR")),
  limma = as.character(packageVersion("limma")),
  WGCNA = as.character(packageVersion("WGCNA")),
  genes = ngenes,
  samples = nsamples,
  status = "PASS"
)
writeLines(jsonlite::toJSON(out, auto_unbox = TRUE, pretty = TRUE), "r-smoke-report.json")
cat("R omics smoke test PASS\n")
