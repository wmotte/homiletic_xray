#!/usr/bin/env Rscript
#
# CHECK SCORE SCALES
#
# This script computes summary statistics for score columns to verify scales.
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
# ==============================================================================

library(tidyverse)

# 1. Load Data
data_file <- "data/homiletic_feedback_data.tsv"
data_raw <- read_tsv(data_file, show_col_types = FALSE)

# 2. Define Domains (9 domains total)
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

# 3. Compute Summary Stats
results <- list()

for (dom_name in names(domains)) {
  col_name <- domains[[dom_name]]
  
  if (col_name %in% names(data_raw)) {
    scores <- as.numeric(data_raw[[col_name]])
    scores <- scores[!is.na(scores)]
    
    stats <- data.frame(
      domain = dom_name,
      min = min(scores),
      max = max(scores),
      mean = mean(scores),
      sd = sd(scores),
      var = var(scores),
      n = length(scores)
    )
    results[[dom_name]] <- stats
  }
}

final_df <- bind_rows(results)
print(final_df)
