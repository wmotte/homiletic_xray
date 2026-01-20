#!/usr/bin/env Rscript
#
# Identify the 10 highest and 10 lowest scoring sermons overall
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
###################################################################
library(tidyverse)

# Create output directory if it doesn't exist
output_dir <- "output"
if (!dir.exists(output_dir)) {
  dir.create(output_dir)
}

# Load data from output directory
data <- read_csv(file.path(output_dir, "data_with_clusters.csv"), show_col_types = FALSE)

cat("Loaded", nrow(data), "sermons with cluster assignments\n\n")

# Get all score columns (need to escape the dot in regex)
score_cols <- names(data)[grepl("\\.score$", names(data))]

if (length(score_cols) == 0) {
  # Try alternative pattern matching
  score_cols <- names(data)[str_detect(names(data), "score$")]
}

cat("Computing overall scores based on", length(score_cols), "score columns...\n")
cat("Score columns found:", length(score_cols), "\n")

# Compute overall average score per sermon
data_with_overall <- data %>%
  mutate(
    overall_score = rowMeans(select(., all_of(score_cols)), na.rm = TRUE),
    n_scores = rowSums(!is.na(select(., all_of(score_cols))))
  )

# Find top 10 and bottom 10
top_10 <- data_with_overall %>%
  arrange(desc(overall_score)) %>%
  head(10) %>%
  mutate(rank = 1:10, category = "TOP")

bottom_10 <- data_with_overall %>%
  arrange(overall_score) %>%
  head(10) %>%
  mutate(rank = 1:10, category = "BOTTOM")

# Combine
top_bottom <- bind_rows(top_10, bottom_10) %>%
  select(category, rank, theologian, sermon_id, sermon_key, cluster,
         overall_score, n_scores, everything())


top_10_display <- top_10 %>%
  select(rank, theologian, sermon_id, overall_score, cluster) %>%
  mutate(overall_score = round(overall_score, 2))

print(as.data.frame(top_10_display), row.names = FALSE)

cat("\n==============================================================================\n")
cat("BOTTOM 10 LOWEST SCORING SERMONS\n")
cat("==============================================================================\n\n")

bottom_10_display <- bottom_10 %>%
  select(rank, theologian, sermon_id, overall_score, cluster) %>%
  mutate(overall_score = round(overall_score, 2))

print(as.data.frame(bottom_10_display), row.names = FALSE)

# Save detailed results
write_csv(top_bottom, file.path(output_dir, "top_bottom_sermons_detailed.csv"))

# Print detailed scores for top sermon
cat("==============================================================================\n")
cat("DETAILED SCORES - HIGHEST SCORING SERMON\n")
cat("==============================================================================\n")
cat("Sermon:", top_10$sermon_key[1], "\n")
cat("Theologian:", top_10$theologian[1], "\n")
cat("Overall score:", round(top_10$overall_score[1], 2), "\n")
cat("Cluster:", top_10$cluster[1], "\n\n")

top_sermon_scores <- top_10 %>%
  select(all_of(score_cols)) %>%
  slice(1) %>%
  pivot_longer(everything(), names_to = "metric", values_to = "score") %>%
  filter(!is.na(score)) %>%
  arrange(desc(score)) %>%
  mutate(score = round(score, 2))

cat("Top 10 individual scores:\n")
print(head(top_sermon_scores, 10), n = 10)

# Print detailed scores for bottom sermon
cat("\n==============================================================================\n")
cat("DETAILED SCORES - LOWEST SCORING SERMON\n")
cat("==============================================================================\n")
cat("Sermon:", bottom_10$sermon_key[1], "\n")
cat("Theologian:", bottom_10$theologian[1], "\n")
cat("Overall score:", round(bottom_10$overall_score[1], 2), "\n")
cat("Cluster:", bottom_10$cluster[1], "\n\n")

bottom_sermon_scores <- bottom_10 %>%
  select(all_of(score_cols)) %>%
  slice(1) %>%
  pivot_longer(everything(), names_to = "metric", values_to = "score") %>%
  filter(!is.na(score)) %>%
  arrange(score) %>%
  mutate(score = round(score, 2))

cat("Bottom 10 individual scores:\n")
print(head(bottom_sermon_scores, 10), n = 10)

# Summary statistics
cat("\n==============================================================================\n")
cat("OVERALL SCORE STATISTICS\n")
cat("==============================================================================\n\n")

stats <- data_with_overall %>%
  summarise(
    min = min(overall_score, na.rm = TRUE),
    q1 = quantile(overall_score, 0.25, na.rm = TRUE),
    median = median(overall_score, na.rm = TRUE),
    mean = mean(overall_score, na.rm = TRUE),
    q3 = quantile(overall_score, 0.75, na.rm = TRUE),
    max = max(overall_score, na.rm = TRUE),
    sd = sd(overall_score, na.rm = TRUE)
  ) %>%
  pivot_longer(everything(), names_to = "statistic", values_to = "value") %>%
  mutate(value = round(value, 2))

print(as.data.frame(stats), row.names = FALSE)

# Save all sermons with overall scores
data_with_overall_export <- data_with_overall %>%
  arrange(desc(overall_score)) %>%
  mutate(rank_overall = row_number()) %>%
  select(rank_overall, theologian, sermon_id, sermon_key,
         cluster, overall_score, n_scores, everything())

write_csv(data_with_overall_export, file.path(output_dir, "all_sermons_with_overall_scores.csv"))

