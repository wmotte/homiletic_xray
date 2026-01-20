#!/usr/bin/env Rscript
#
# PLOT FACETED VARIANCE SATURATION
#
# This script reads the pre-computed temporal variance data and generates
# faceted plots with free Y-axis scales to address the magnitude differences
# between domains (specifically Transactional Analysis vs others).
#
# ==============================================================================

library(tidyverse)

# Input/Output
input_file <- "output.temporal.variance/temporal_variance_data.csv"
output_dir <- "output.temporal.variance"

if (!file.exists(input_file)) {
  stop("Data file not found. Please run 05__temporal_variance_analysis.R first.")
}

cat("Reading variance data...\n")
data <- read_csv(input_file, show_col_types = FALSE)

# ==============================================================================
# PLOT 1: Variance Convergence (Value) - Faceted by Domain
# ==============================================================================
cat("Generating Faceted Convergence Plot...\n")

p1 <- data %>%
  ggplot(aes(x = n, y = mean_var_est, color = theologian, fill = theologian)) +
  geom_line(linewidth = 0.8) +
  geom_ribbon(aes(ymin = q05_var, ymax = q95_var), alpha = 0.15, color = NA) +
  # The Key Change: Facet by Domain with Free Y Scales
  facet_wrap(~ domain, scales = "free_y", ncol = 2) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold", size = 11)
  ) +
  labs(
    title = "Variance Saturation: Estimates per Domain",
    subtitle = "Mean Variance + 90% CI vs Sample Size (Free Y-Scales)",
    x = "Number of Sermons (N)",
    y = "Estimated Variance of Scores",
    caption = "Note: Y-axis scales vary significantly between domains."
  )

ggsave(file.path(output_dir, "saturation_faceted_convergence.pdf"), p1, width = 12, height = 10)

# ==============================================================================
# PLOT 2: Stability (SD of Variance) - Faceted by Domain
# This is the best view for "Saturation" (when does the error drop?)
# ==============================================================================
cat("Generating Faceted Stability Plot...\n")

p2 <- data %>%
  ggplot(aes(x = n, y = sd_var_est, color = theologian)) +
  geom_line(linewidth = 0.8) +
  # Facet by Domain with Free Y Scales
  facet_wrap(~ domain, scales = "free_y", ncol = 2) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_blank(),
    strip.text = element_text(face = "bold", size = 11)
  ) +
  labs(
    title = "Variance Saturation: Stability of Estimates",
    subtitle = "Standard Deviation of the Variance Estimator (Lower is more saturated)",
    x = "Number of Sermons (N)",
    y = "Instability (SD of Variance Estimate)",
    caption = "Curves flattening towards zero indicate saturation/sufficiency of sample size."
  )

ggsave(file.path(output_dir, "saturation_faceted_stability.pdf"), p2, width = 12, height = 10)

# ==============================================================================
# PLOT 3: Normalized Instability (Coefficient of Variation)
# This allows comparing saturation *speed* across domains on a fixed scale
# ==============================================================================
cat("Generating Normalized Saturation Plot...\n")

data_norm <- data %>%
  mutate(cv_var = sd_var_est / mean_var_est) # Coefficient of Variation

p3 <- data_norm %>%
  ggplot(aes(x = n, y = cv_var, color = domain)) +
  geom_line(linewidth = 0.8, alpha = 0.8) +
  facet_wrap(~ theologian) +
  coord_cartesian(ylim = c(0, 1.0)) + # Focus on the convergence zone
  theme_minimal() +
  labs(
    title = "Relative Saturation Speed (Normalized)",
    subtitle = "Coefficient of Variation (SD / Mean) of the Variance Estimate",
    x = "Number of Sermons (N)",
    y = "Relative Instability (CV)",
    caption = "Comparison of how fast each domain stabilizes relative to its own magnitude."
  )

ggsave(file.path(output_dir, "saturation_normalized_comparison.pdf"), p3, width = 12, height = 6)

cat("Done. Created faceted plots in", output_dir, "\n")
