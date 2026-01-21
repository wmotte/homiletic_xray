#!/usr/bin/env Rscript
#
# HOMILETIC FEEDBACK TEMPORAL VARIANCE ANALYSIS
#
# This script analyzes the variation in scores for the top 3 theologians
# as sample size increases (sequential analysis).
#
# It explicitly calculates the Dekker score from sub-scores because the
# overall average column is empty in the source data.
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
# ==============================================================================

# Load required libraries
library(tidyverse)
library(data.table)

# Set random seed
set.seed(42)

# Output directory
output_dir <- "output.temporal.variance"
if (!dir.exists(output_dir)) {
  dir.create(output_dir)
}

# 1. Load Data
data_file <- "data/homiletic_feedback_data.tsv"
cat("Reading data...\n")
data_raw <- read_tsv(data_file, show_col_types = FALSE)

# 2. Fix Dekker Scores (Imputation)
cat("Checking and fixing Dekker scores...\n")

# Identify Dekker sub-score columns
dekker_sub_cols <- c(
  "dekker.1_specific_bible_passage.score",
  "dekker.2_exegesis_original_context.score",
  "dekker.3_application_concrete_contemporary.score",
  "dekker.4_interwoveness_exposition_application.score",
  "dekker.5_three_parts_misery_redemption_gratitude.score",
  "dekker.6_two_ways_seriousness_of_choice.score",
  "dekker.7_christocentric_grace.score",
  "dekker.8_depth_and_length.score"
)

# Calculate average if sub-columns exist
if (all(dekker_sub_cols %in% names(data_raw))) {
  cat("  Found all 8 Dekker sub-columns. Computing average...\n")
  
  data_raw <- data_raw %>%
    rowwise() %>%
    mutate(
      dekker_calculated = mean(c_across(all_of(dekker_sub_cols)), na.rm = TRUE)
    ) %>%
    ungroup()
    
  # Replace the empty overall column with the calculated one for the analysis
  # (or create it if it doesn't exist/is empty)
  data_raw$dekker.overall.average_score <- data_raw$dekker_calculated
  
  cat("  Dekker scores computed. Mean:", mean(data_raw$dekker.overall.average_score, na.rm=TRUE), "\n")
  
} else {
  cat("  Warning: Could not find all Dekker sub-columns. Skipping calculation.\n")
}

# 3. Identify Top 3 Theologians
cat("Identifying top theologians...\n")
top_theologians <- data_raw %>%
  count(theologian) %>%
  arrange(desc(n)) %>%
  head(3) %>%
  pull(theologian)

cat("Top 3 Theologians:", paste(top_theologians, collapse = ", "), "\n")

# 4. Define Domains and Score Columns (9 domains for 3x3 grid)
domains <- list(
  aristoteles = "aristoteles.overall.overall_rhetorical_score",
  dekker = "dekker.overall.average_score",
  esthetiek = "esthetiek.overall.overall_aesthetic_score",
  kolb = "kolb.overall.overall_kolb_score",
  schulz = "schulz.overall.overall_communication_score",
  transactional = "transactional.overall.psychological_health_score",
  metaphor = "metaphor.coherentie.score",
  narrative = "narrative.coherentie.score",
  speech_act = "speech_act.diagnose.gebeuren_score"
)

# Function to calculate variance stats for a given sample size
calc_variance_stats <- function(scores, n_sample, n_iterations = 200) {
  variances <- numeric(n_iterations)
  means <- numeric(n_iterations)
  
  for (i in 1:n_iterations) {
    sample_scores <- sample(scores, n_sample, replace = FALSE)
    variances[i] <- var(sample_scores, na.rm = TRUE)
    means[i] <- mean(sample_scores, na.rm = TRUE)
  }
  
  return(data.frame(
    n = n_sample,
    mean_var_est = mean(variances, na.rm = TRUE), # Expected value of variance
    sd_var_est = sd(variances, na.rm = TRUE),     # Stability of variance estimate
    q05_var = quantile(variances, 0.05, na.rm = TRUE),
    q95_var = quantile(variances, 0.95, na.rm = TRUE),
    mean_score_est = mean(means, na.rm = TRUE),
    sd_score_est = sd(means, na.rm = TRUE)        # Standard Error of the Mean
  ))
}

# 5. Perform Analysis
all_results <- list()

for (theo in top_theologians) {
  cat("\nProcessing theologian:", theo, "\n")
  theo_data <- data_raw %>%
    filter(theologian == theo)
  
  for (dom_name in names(domains)) {
    col_name <- domains[[dom_name]]
    
    # Extract scores
    if (col_name %in% names(theo_data)) {
      scores <- as.numeric(theo_data[[col_name]])
      scores <- scores[!is.na(scores)]
      
      total_n <- length(scores)
      cat("  Domain:", dom_name, "(N =", total_n, ")\n")
      
      if (total_n < 10) {
        cat("    Skipping (not enough data)\n")
        next
      }
      
      # A. Sequential Analysis (steps of 5)
      steps <- seq(5, total_n, by = 5)
      # Ensure total_n is included if not in steps
      if (tail(steps, 1) != total_n) steps <- c(steps, total_n)
      
      seq_res <- map_dfr(steps, function(k) {
        calc_variance_stats(scores, k, n_iterations = 500)
      })
      
      seq_res$theologian <- theo
      seq_res$domain <- dom_name
      seq_res$analysis_type <- "sequential"
      all_results[[paste(theo, dom_name, "seq", sep="_")]] <- seq_res
      
      # B. Split Half Analysis for specific user query (50% vs 50%)
      # We simulate this by comparing N/2 variance stats to Full N variance stats
      # (Already included in sequential analysis, but we can flag it)
      
    } else {
      cat("    Warning: Column", col_name, "not found!\n")
    }
  }
}

# Combine results
final_df <- bind_rows(all_results)

# 6. Plotting

cat("\nGenerating plots...\n")

# Plot 1: Variance Estimate Convergence (Mean Variance Estimate vs N)
# Does the *value* of the variance change as we add more data? (Natural Variation Saturation)
p1 <- final_df %>%
  ggplot(aes(x = n, y = mean_var_est, color = domain, fill = domain)) +
  geom_line() +
  geom_ribbon(aes(ymin = q05_var, ymax = q95_var), alpha = 0.1, color = NA) +
  facet_wrap(~theologian, nrow = 3, ncol = 3, scales = "free") +
  scale_x_continuous(breaks = seq(0, 400, by = 20)) +
  theme_minimal() +
  labs(
    title = "Convergence of Score Variance Estimates",
    subtitle = "Estimated Variance (Mean + 90% Confidence Interval) vs Sample Size",
    x = "Number of Sermons (N)",
    y = "Variance of Scores",
    caption = "Shaded area represents the uncertainty (90% CI) of the variance estimate at size N"
  )

ggsave(file.path(output_dir, "variance_convergence_estimates.pdf"), p1, width = 14, height = 12)

# Plot 2: Stability of Variance Estimate (SD of Variance vs N)
# How much does the variance estimate fluctuate if we use smaller samples?
p2 <- final_df %>%
  ggplot(aes(x = n, y = sd_var_est, color = domain)) +
  geom_line() +
  facet_wrap(~theologian, nrow = 3, ncol = 3, scales = "free") +
  scale_x_continuous(breaks = seq(0, 400, by = 20)) +
  theme_minimal() +
  labs(
    title = "Stability of Variance Estimates (Saturation Analysis)",
    subtitle = "Standard Deviation of the Variance Estimator vs Sample Size",
    x = "Number of Sermons (N)",
    y = "SD of Variance Estimate (instability)",
    caption = "Lower values indicate a more stable/saturated estimate of natural variation"
  )

ggsave(file.path(output_dir, "variance_stability_analysis.pdf"), p2, width = 14, height = 12)

# Plot 3: Specific Check for 50% split (User Query)
# We calculate the instability at 50% N vs 100% N (100% N instability is 0 for the single dataset, but we want to show the trend)
# Actually, let's just show the sequential plots for each domain separately for clarity

for (dom in names(domains)) {
  p_dom <- final_df %>%
    filter(domain == dom) %>%
    ggplot(aes(x = n, y = mean_var_est, color = theologian)) +
    geom_line(linewidth = 1) +
    geom_ribbon(aes(ymin = q05_var, ymax = q95_var, fill = theologian), alpha = 0.15, color = NA) +
    scale_x_continuous(breaks = seq(0, 400, by = 20)) +
    theme_minimal() +
    labs(
      title = paste("Sequential Variance Analysis:", dom),
      subtitle = "Does variance change/saturate with more sermons?",
      x = "Number of Sermons",
      y = "Estimated Variance"
    )
  ggsave(file.path(output_dir, paste0("domain_variance_", dom, ".pdf")), p_dom, width = 10, height = 6)
}

# Save summary CSV
write_csv(final_df, file.path(output_dir, "temporal_variance_data.csv"))

cat("Done. Check", output_dir, "for results.\n")