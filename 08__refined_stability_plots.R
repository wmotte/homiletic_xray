#!/usr/bin/env Rscript
#
# REFINED SATURATION PLOTS (ZOOMED)
#
# This script generates "zoomed-in" versions of the variance analysis plots.
# By excluding the highly unstable initial sample sizes (N < 15), we can
# better visualize the subtle fluctuations and convergence in the later stages.
#
# Wim Otte (w.m.otte@umcutrecht.nl)
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

# Filter out the initial "chaos" to zoom in on the stabilization phase
# We start at N = 5 to allow the Y-axis to scale appropriately for the tail
data_zoomed <- data %>%
  filter(n >= 5)

cat("Generating Zoomed Plots (N >= 5)...\n")

# ==============================================================================
# PLOT 1: Zoomed Convergence (Is the variance still drifting?)
# ==============================================================================
p1 <- data_zoomed %>%
  ggplot(aes(x = n, y = mean_var_est, color = theologian, fill = theologian)) +
  geom_line(linewidth = 1) +
  geom_ribbon(aes(ymin = q05_var, ymax = q95_var), alpha = 0.1, color = NA) +
  geom_point(size = 1.5) + # Add points to see the steps clearly
  facet_wrap(~ domain, scales = "free_y", ncol = 2) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_line(color = "grey90"),
    strip.text = element_text(face = "bold", size = 11)
  ) +
  labs(
    title = "Variance Convergence (Zoomed: N >= 5)",
    subtitle = "Focusing on the stabilization phase (excluding initial volatility)",
    x = "Number of Sermons (N)",
    y = "Estimated Variance",
    caption = "Free Y-scales. Including N >= 5 reveals initial drops."
  )

ggsave(file.path(output_dir, "saturation_zoomed_convergence.pdf"), p1, width = 12, height = 10)

# ==============================================================================
# PLOT 2: Zoomed Stability (How much does the estimate still jump?)
# ==============================================================================
p2 <- data_zoomed %>%
  ggplot(aes(x = n, y = sd_var_est, color = theologian)) +
  geom_line(linewidth = 1) +
  geom_point(size = 1.5) +
  facet_wrap(~ domain, scales = "free_y", ncol = 2) +
  theme_minimal() +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_line(color = "grey90"),
    strip.text = element_text(face = "bold", size = 11)
  ) +
  labs(
    title = "Instability of Variance Estimate (Zoomed: N >= 5)",
    subtitle = "Standard Deviation of the Estimator (Lower is better)",
    x = "Number of Sermons (N)",
    y = "Instability (SD)",
    caption = "Free Y-scales. Shows residual fluctuation in the estimate."
  )

ggsave(file.path(output_dir, "saturation_zoomed_stability.pdf"), p2, width = 12, height = 10)

# ==============================================================================
# PLOT 3: Rate of Change (Percentage Change in Variance Estimate)
# ==============================================================================
# This calculates the relative change from the previous step.
# If this is close to 0, the estimate has stopped changing (saturated).

data_change <- data %>%
  arrange(theologian, domain, n) %>%
  group_by(theologian, domain) %>%
  mutate(
    pct_change = abs((mean_var_est - lag(mean_var_est)) / lag(mean_var_est)) * 100
  ) %>%
  filter(n >= 5) # Zoom in

p3 <- data_change %>%
  ggplot(aes(x = n, y = pct_change, color = theologian)) +
  geom_hline(yintercept = 5, linetype = "dashed", color = "gray50") + # 5% threshold
  geom_line(linewidth = 0.8) +
  geom_point(size = 1) +
  facet_wrap(~ domain, ncol = 2) + # Fixed scale here might be better to compare domains? No, free is safer.
  coord_cartesian(ylim = c(0, 20)) + # Focus on 0-20% change
  theme_minimal() +
  labs(
    title = "Saturation: Rate of Change (Zoomed: N >= 5)",
    subtitle = "Percentage change in Variance Estimate from previous step",
    x = "Number of Sermons (N)",
    y = "% Change in Variance Estimate",
    caption = "Dashed line = 5% threshold. Values consistently below line indicate saturation."
  )

ggsave(file.path(output_dir, "saturation_rate_of_change.pdf"), p3, width = 12, height = 10)

cat("Done. Created zoomed plots in", output_dir, "\n")
