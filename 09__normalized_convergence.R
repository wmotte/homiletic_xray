#!/usr/bin/env Rscript
#
# NORMALIZED CONVERGENCE PLOTS
#
# This script normalizes the variance estimates relative to the final (saturated) value.
# This removes the "absolute magnitude" of the variance (the theologian's style)
# and isolates the "convergence pattern" (the method's reliability).
#
# All curves will converge to y = 1.0.
# Values > 1.0 indicate the variance was initially overestimated.
# Values < 1.0 indicate the variance was initially underestimated.
#
# W.M. Otte (w.m.otte@umcutrecht.nl)
#
# ==============================================================================

library(tidyverse)

# Input/Output
input_file <- "output.temporal.variance/temporal_variance_data.csv"
output_dir <- "output.temporal.variance"

if (!file.exists(input_file)) {
  stop("Data file not found.")
}

data <- read_csv(input_file, show_col_types = FALSE)

# 1. Normalize Data
# We divide every estimate by the *final* estimate (at max N) for that theologian/domain.
# This forces all lines to end at 1.0, allowing direct comparison of the *path* to saturation.

data_norm <- data %>%
  filter(n >= 5) %>%
  arrange(theologian, domain, n) %>%
  group_by(theologian, domain) %>%
  mutate(
    # The "Truth" is assumed to be the final value in the sequence
    final_variance = last(mean_var_est),
    # Normalize: How far off is this estimate from the final truth?
    # 1.0 = Perfect agreement with final saturation
    normalized_convergence = mean_var_est / final_variance
  ) %>%
  ungroup()

cat("Generating Normalized Convergence Plots...\n")

# ==============================================================================
# PLOT: Normalized Convergence (Ratio to Final Value)
# ==============================================================================
p1 <- data_norm %>%
  ggplot(aes(x = n, y = normalized_convergence, color = theologian)) + 
  # Add reference line at 1.0 (Saturation Point)
  geom_hline(yintercept = 1, linetype = "dashed", color = "black", alpha = 0.5) + 
  geom_line(linewidth = 1) + 
  # We can now use FIXED scales because everyone is normalized to ~1.0
  facet_wrap(~ domain, scales = "fixed", ncol = 2) + 
  coord_cartesian(ylim = c(0.75, 1.25)) + # Focus on the relevant window (0.75x to 1.25x error)
  theme_minimal() + 
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_line(color = "grey95"),
    strip.text = element_text(face = "bold", size = 11)
  ) + 
  labs(
    title = "Normalized Convergence Patterns",
    subtitle = "Variance Estimate relative to Final Saturated Value (Ratio)",
    x = "Number of Sermons (N)",
    y = "Ratio to Final Variance (1.0 = Saturated)",
    caption = "Y=1.0: Estimate matches final value. Y>1.0: Initial overestimate. Y<1.0: Initial underestimate."
  )

ggsave(file.path(output_dir, "saturation_normalized_convergence.pdf"), p1, width = 12, height = 10)

cat("Done. Created normalized plot in", output_dir, "\n")
