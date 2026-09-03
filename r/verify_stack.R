required <- c("DESeq2", "edgeR", "limma", "WGCNA")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing)) {
  stop(sprintf("Missing required R packages: %s", paste(missing, collapse = ", ")))
}
cat("R scientific stack verified\n")
for (pkg in required) {
  cat(sprintf("%s=%s\n", pkg, as.character(packageVersion(pkg))))
}
cat(sprintf("R=%s\n", R.version.string))
