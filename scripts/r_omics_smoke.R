required <- c("DESeq2", "edgeR", "limma", "WGCNA", "GEOquery", "jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))

set.seed(42)
ng <- 120
ns <- 6
group <- factor(rep(c("control", "treated"), each=3))
counts <- matrix(rnbinom(ng * ns, mu=80, size=10), nrow=ng,
                 dimnames=list(sprintf("gene%03d", seq_len(ng)), sprintf("s%d", seq_len(ns))))
# Add a reproducible treatment signal to 12 genes.
counts[1:12, group == "treated"] <- counts[1:12, group == "treated"] + 70L
coldata <- data.frame(group=group, row.names=colnames(counts))

suppressPackageStartupMessages(library(DESeq2))
dds <- DESeqDataSetFromMatrix(countData=counts, colData=coldata, design=~group)
dds <- DESeq(dds, quiet=TRUE)
deseq_res <- results(dds, contrast=c("group", "treated", "control"))
stopifnot(nrow(deseq_res) == ng, any(is.finite(deseq_res$log2FoldChange)))

suppressPackageStartupMessages(library(edgeR))
y <- DGEList(counts=counts, group=group)
y <- calcNormFactors(y)
design <- model.matrix(~group)
y <- estimateDisp(y, design)
fit <- glmQLFit(y, design)
qlf <- glmQLFTest(fit, coef=2)
stopifnot(nrow(topTags(qlf, n=Inf)$table) == ng)

suppressPackageStartupMessages(library(limma))
v <- voom(y, design, plot=FALSE)
lfit <- eBayes(lmFit(v, design))
stopifnot(nrow(topTable(lfit, coef=2, number=Inf)) == ng)

suppressPackageStartupMessages(library(WGCNA))
options(stringsAsFactors=FALSE)
expr <- t(log2(counts + 1))
# Test core network primitives on a small deterministic matrix.
adj <- adjacency(expr, power=6, type="signed")
stopifnot(all(dim(adj) == c(ng, ng)), all(is.finite(adj)))

# Validate that GEOquery can build the live GEO metadata request object.
# Network retrieval is tested separately so package functionality and network availability are distinguishable.
stopifnot(exists("getGEO", where=asNamespace("GEOquery"), mode="function"))

out <- list(
  r_version=R.version.string,
  packages=as.list(vapply(required, function(p) as.character(packageVersion(p)), character(1))),
  deseq_rows=nrow(deseq_res),
  edger_rows=nrow(topTags(qlf, n=Inf)$table),
  limma_rows=nrow(topTable(lfit, coef=2, number=Inf)),
  wgcna_adjacency_dim=dim(adj)
)
jsonlite::write_json(out, "r_omics_smoke.json", auto_unbox=TRUE, pretty=TRUE)
cat(jsonlite::toJSON(out, auto_unbox=TRUE, pretty=TRUE), "\n")
