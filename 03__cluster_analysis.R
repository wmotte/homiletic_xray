#!/usr/bin/env Rscript
#
# HOMILETIC FEEDBACK CLUSTER ANALYSIS
#
# This script performs k-medoids clustering on homiletic feedback data
# and computes correlation matrices with 95% confidence intervals.
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
# ==============================================================================

# Load required libraries
library(tidyverse)
library(cluster)      # For PAM (k-medoids)
library(factoextra)   # For clustering visualization
library(corrplot)     # For correlation plots
library(psych)        # For correlation confidence intervals

# Set random seed for reproducibility
set.seed(42)

# Create output directory if it doesn't exist
output_dir <- "output"
if (!dir.exists(output_dir)) {
  dir.create(output_dir)
}

# ==============================================================================
# 1. DATA LOADING AND PREPROCESSING
# ==============================================================================

cat("==============================================================================\n")
cat("STEP 1: LOADING DATA\n")
cat("==============================================================================\n")

# Load the TSV file
data_file <- "data/homiletic_feedback_data.tsv"

if (!file.exists(data_file)) {
  stop("Error: ", data_file, " not found!")
}

cat("Reading", data_file, "...\n")
data_raw <- read_tsv(data_file, show_col_types = FALSE)

cat("  - Total sermons:", nrow(data_raw), "\n")
cat("  - Total columns:", ncol(data_raw), "\n")

# ==============================================================================
# 2. EXTRACT NUMERIC COLUMNS
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 2: EXTRACTING NUMERIC PREDICTORS\n")
cat("==============================================================================\n")

# Identify all columns ending with ".score" or that are numeric
score_cols <- names(data_raw)[grepl("\\.score$", names(data_raw))]

cat("  - Found", length(score_cols), "score columns\n")

# Extract numeric data
data_numeric <- data_raw %>%
  select(theologian, sermon_id, sermon_key, all_of(score_cols)) %>%
  mutate(across(all_of(score_cols), as.numeric))

# Check for missing data
missing_summary <- data_numeric %>%
  select(all_of(score_cols)) %>%
  summarise(across(everything(), ~sum(is.na(.)))) %>%
  pivot_longer(everything(), names_to = "variable", values_to = "n_missing") %>%
  arrange(desc(n_missing))

cat("\nMissing data summary (top 10):\n")
print(head(missing_summary, 10))

# Remove columns with >50% missing data
threshold <- 0.5 * nrow(data_numeric)
cols_to_keep <- missing_summary %>%
  filter(n_missing < threshold) %>%
  pull(variable)

cat("\n  - Keeping", length(cols_to_keep), "columns with <50% missing data\n")

# Filter to sermons with complete data
data_complete <- data_numeric %>%
  select(theologian, sermon_id, sermon_key, all_of(cols_to_keep)) %>%
  drop_na()

cat("  - Complete cases:", nrow(data_complete), "sermons\n")
cat("  - Final predictors:", length(cols_to_keep), "variables\n")

# Save metadata columns
metadata <- data_complete %>%
  select(theologian, sermon_id, sermon_key)

# Extract only the numeric predictors for clustering
X <- data_complete %>%
  select(all_of(cols_to_keep)) %>%
  as.data.frame()

rownames(X) <- data_complete$sermon_key

# Standardize the data (important for distance-based clustering)
X_scaled <- scale(X)

cat("\nData standardized (mean=0, sd=1)\n")

# ==============================================================================
# 3. DETERMINE OPTIMAL NUMBER OF CLUSTERS
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 3: DETERMINING OPTIMAL K\n")
cat("==============================================================================\n")

# Test k from 7 to 20
k_range <- 7:20

cat("Testing k from", min(k_range), "to", max(k_range), "\n")
cat("This may take a few minutes...\n\n")

# Initialize storage for metrics
wss <- numeric(length(k_range))
silhouette_avg <- numeric(length(k_range))

# Compute metrics for each k
for (i in seq_along(k_range)) {
  k <- k_range[i]
  cat("  Testing k =", k, "...")

  # Perform k-medoids clustering
  pam_result <- pam(X_scaled, k = k, metric = "euclidean")

  # Store within-cluster sum of squares
  wss[i] <- sum(pam_result$clusinfo[, "av_diss"] * pam_result$clusinfo[, "size"])

  # Store average silhouette width
  silhouette_avg[i] <- pam_result$silinfo$avg.width

  cat(" WSS =", round(wss[i], 2), ", Silhouette =", round(silhouette_avg[i], 3), "\n")
}

# Create results dataframe
k_metrics <- data.frame(
  k = k_range,
  wss = wss,
  silhouette = silhouette_avg
)

# Determine optimal k using silhouette method
optimal_k <- k_metrics$k[which.max(k_metrics$silhouette)]

cat("\n--- OPTIMAL K SELECTION ---\n")
cat("Optimal k (highest silhouette):", optimal_k, "\n")
cat("Silhouette score:", round(max(k_metrics$silhouette), 3), "\n")

# Save k-selection plot
cat("\nCreating k-selection plots...\n")

pdf(file.path(output_dir, "cluster_k_selection.pdf"), width = 12, height = 5)
par(mfrow = c(1, 2))

# Elbow plot
plot(k_metrics$k, k_metrics$wss, type = "b", pch = 19,
     xlab = "Number of clusters (k)", ylab = "Total within-cluster dissimilarity",
     main = "Elbow Method", col = "steelblue", lwd = 2)
grid()

# Silhouette plot
plot(k_metrics$k, k_metrics$silhouette, type = "b", pch = 19,
     xlab = "Number of clusters (k)", ylab = "Average silhouette width",
     main = "Silhouette Method", col = "darkgreen", lwd = 2)
abline(v = optimal_k, col = "red", lty = 2, lwd = 2)
text(optimal_k, max(k_metrics$silhouette),
     paste("Optimal k =", optimal_k), pos = 4, col = "red")
grid()

dev.off()

cat("  Saved: cluster_k_selection.pdf\n")

# ==============================================================================
# 4. PERFORM K-MEDOIDS CLUSTERING WITH OPTIMAL K
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 4: K-MEDOIDS CLUSTERING (k =", optimal_k, ")\n")
cat("==============================================================================\n")

# Perform final clustering
pam_final <- pam(X_scaled, k = optimal_k, metric = "euclidean")

cat("Clustering complete!\n\n")

# Add cluster assignments to data
data_clustered <- data_complete %>%
  mutate(cluster = as.factor(pam_final$clustering))

# Cluster summary
cluster_summary <- data_clustered %>%
  group_by(cluster) %>%
  summarise(
    n = n(),
    .groups = "drop"
  ) %>%
  mutate(percentage = round(100 * n / sum(n), 1))

cat("Cluster sizes:\n")
print(cluster_summary)

# Theologian distribution across clusters
cat("\nTheologian distribution across clusters:\n")
theologian_cluster <- data_clustered %>%
  count(cluster, theologian) %>%
  pivot_wider(names_from = cluster, values_from = n, values_fill = 0)
print(theologian_cluster)

# Identify medoids (representative sermons)
medoid_ids <- rownames(X_scaled)[pam_final$id.med]
cat("\nMedoids (representative sermons per cluster):\n")
for (i in seq_along(medoid_ids)) {
  cat("  Cluster", i, ":", medoid_ids[i], "\n")
}

# ==============================================================================
# 5. CLUSTER VISUALIZATION
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 5: CLUSTER VISUALIZATION\n")
cat("==============================================================================\n")

# PCA for visualization
cat("Performing PCA for 2D visualization...\n")
pca_result <- prcomp(X_scaled)
variance_explained <- summary(pca_result)$importance[2, 1:2] * 100

# Create visualization dataframe
viz_data <- data.frame(
  PC1 = pca_result$x[, 1],
  PC2 = pca_result$x[, 2],
  cluster = data_clustered$cluster,
  theologian = data_clustered$theologian,
  sermon_key = data_clustered$sermon_key
)

# Create cluster plot
cat("Creating cluster visualization...\n")

pdf(file.path(output_dir, "cluster_visualization.pdf"), width = 10, height = 8)

p1 <- ggplot(viz_data, aes(x = PC1, y = PC2, color = cluster)) +
  geom_point(alpha = 0.6, size = 2) +
  stat_ellipse(level = 0.95, size = 1) +
  labs(
    title = paste0("K-Medoids Clustering (k = ", optimal_k, ")"),
    subtitle = paste0("Silhouette score: ", round(pam_final$silinfo$avg.width, 3)),
    x = paste0("PC1 (", round(variance_explained[1], 1), "% variance)"),
    y = paste0("PC2 (", round(variance_explained[2], 1), "% variance)"),
    color = "Cluster"
  ) +
  theme_minimal() +
  theme(legend.position = "right")

print(p1)

# Add theologian coloring
p2 <- ggplot(viz_data, aes(x = PC1, y = PC2, color = theologian)) +
  geom_point(alpha = 0.6, size = 2) +
  labs(
    title = "Sermons by Theologian",
    x = paste0("PC1 (", round(variance_explained[1], 1), "% variance)"),
    y = paste0("PC2 (", round(variance_explained[2], 1), "% variance)"),
    color = "Theologian"
  ) +
  theme_minimal() +
  theme(legend.position = "right")

print(p2)

dev.off()

cat("  Saved: cluster_visualization.pdf\n")

# Silhouette plot
cat("\nCreating silhouette plot...\n")

pdf(file.path(output_dir, "cluster_silhouette.pdf"), width = 10, height = 8)
plot(silhouette(pam_final), col = 1:optimal_k, border = NA,
     main = paste0("Silhouette Plot (k = ", optimal_k, ")"))
dev.off()

cat("  Saved: cluster_silhouette.pdf\n")

# ==============================================================================
# 6. CLUSTER CHARACTERIZATION
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 6: CLUSTER CHARACTERIZATION\n")
cat("==============================================================================\n")

# Compute mean scores per cluster
cluster_profiles <- data_clustered %>%
  group_by(cluster) %>%
  summarise(across(all_of(cols_to_keep), ~mean(., na.rm = TRUE)), .groups = "drop")

# Find top 5 distinguishing features per cluster
cat("\nTop 5 distinguishing features per cluster:\n\n")

for (k in 1:optimal_k) {
  cat("CLUSTER", k, "(n =", cluster_summary$n[k], "):\n")

  cluster_profile <- cluster_profiles %>%
    filter(cluster == k) %>%
    select(-cluster) %>%
    pivot_longer(everything(), names_to = "variable", values_to = "score") %>%
    arrange(desc(score))

  cat("  Highest scores:\n")
  top_scores <- head(cluster_profile, 5)
  for (i in 1:nrow(top_scores)) {
    cat("    ", i, ".", top_scores$variable[i], ":", round(top_scores$score[i], 2), "\n")
  }
  cat("\n")
}

# Save cluster profiles
write_csv(cluster_profiles, file.path(output_dir, "cluster_profiles.csv"))
cat("Saved: cluster_profiles.csv\n")

# Save clustered data
write_csv(data_clustered, file.path(output_dir, "data_with_clusters.csv"))
cat("Saved: data_with_clusters.csv\n")

# ==============================================================================
# 7. CORRELATION ANALYSIS WITH 95% CI
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 7: CORRELATION ANALYSIS\n")
cat("==============================================================================\n")

cat("Computing correlation matrix with 95% confidence intervals...\n")
cat("This may take a few minutes for", length(cols_to_keep), "variables...\n\n")

# Compute correlation matrix
cor_matrix <- cor(X, use = "pairwise.complete.obs", method = "pearson")

# Compute correlation with CIs using psych package
# Note: For large matrices this can be slow, so we'll compute CIs for a subset
# or save full matrix without CIs if too large

if (length(cols_to_keep) <= 50) {
  cat("Computing confidence intervals for all correlations...\n")
  cor_with_ci <- corr.test(X, method = "pearson", adjust = "none")

  # Extract correlation matrix, p-values, and confidence intervals
  cor_r <- cor_with_ci$r
  cor_p <- cor_with_ci$p
  cor_ci_lower <- cor_with_ci$ci[, "lower"]
  cor_ci_upper <- cor_with_ci$ci[, "upper"]

  # Create comprehensive correlation table
  cor_long <- cor_r %>%
    as.data.frame() %>%
    rownames_to_column("var1") %>%
    pivot_longer(-var1, names_to = "var2", values_to = "correlation")

  p_long <- cor_p %>%
    as.data.frame() %>%
    rownames_to_column("var1") %>%
    pivot_longer(-var1, names_to = "var2", values_to = "p_value")

  cor_table <- cor_long %>%
    left_join(p_long, by = c("var1", "var2")) %>%
    mutate(
      significance = case_when(
        p_value < 0.001 ~ "***",
        p_value < 0.01 ~ "**",
        p_value < 0.05 ~ "*",
        TRUE ~ ""
      )
    ) %>%
    filter(var1 != var2) %>%  # Remove diagonal
    arrange(desc(abs(correlation)))

} else {
  cat("Large matrix (>50 vars). Computing correlations without full CI table...\n")
  cor_r <- cor_matrix

  # Create basic correlation table
  cor_table <- cor_r %>%
    as.data.frame() %>%
    rownames_to_column("var1") %>%
    pivot_longer(-var1, names_to = "var2", values_to = "correlation") %>%
    filter(var1 != var2) %>%  # Remove diagonal
    arrange(desc(abs(correlation)))
}

# Save correlation matrix
write_csv(as.data.frame(cor_r), file.path(output_dir, "correlation_matrix.csv"))
cat("Saved: correlation_matrix.csv\n")

# Save correlation table (top correlations)
write_csv(cor_table, file.path(output_dir, "correlation_table.csv"))
cat("Saved: correlation_table.csv\n")

# Display top positive and negative correlations
cat("\nTOP 10 POSITIVE CORRELATIONS:\n")
top_positive <- cor_table %>%
  filter(correlation > 0) %>%
  head(10)
print(top_positive)

cat("\nTOP 10 NEGATIVE CORRELATIONS:\n")
top_negative <- cor_table %>%
  filter(correlation < 0) %>%
  arrange(correlation) %>%
  head(10)
print(top_negative)

# ==============================================================================
# 8. CORRELATION VISUALIZATION
# ==============================================================================

cat("\n==============================================================================\n")
cat("STEP 8: CORRELATION VISUALIZATION\n")
cat("==============================================================================\n")

cat("Creating correlation heatmap...\n")

# For large matrices, select only variables with highest variance
if (length(cols_to_keep) > 50) {
  cat("Large matrix detected. Showing top 50 variables by variance...\n")

  var_scores <- apply(X, 2, var, na.rm = TRUE)
  top_vars <- names(sort(var_scores, decreasing = TRUE))[1:50]
  cor_r_subset <- cor_r[top_vars, top_vars]
} else {
  cor_r_subset <- cor_r
}

# Create correlation plot
pdf(file.path(output_dir, "correlation_heatmap.pdf"), width = 16, height = 16)

corrplot(cor_r_subset,
         method = "color",
         type = "upper",
         order = "hclust",
         tl.cex = 0.6,
         tl.col = "black",
         col = colorRampPalette(c("blue", "white", "red"))(200),
         title = "Correlation Matrix (Hierarchically Clustered)",
         mar = c(0, 0, 2, 0))

dev.off()

cat("  Saved: correlation_heatmap.pdf\n")

# Create network plot of strong correlations
cat("\nCreating correlation network plot (|r| > 0.75)...\n")

pdf(file.path(output_dir, "correlation_network.pdf"), width = 12, height = 12)

# Select only strong correlations
cor_r_strong <- cor_r_subset
cor_r_strong[abs(cor_r_strong) < 0.75] <- 0

corrplot(cor_r_strong,
         method = "circle",
         type = "upper",
         order = "hclust",
         tl.cex = 0.7,
         tl.col = "black",
         col = colorRampPalette(c("blue", "white", "red"))(200),
         title = "Strong Correlations (|r| > 0.75)",
         mar = c(0, 0, 2, 0))

dev.off()

cat("  Saved: correlation_network.pdf\n")

