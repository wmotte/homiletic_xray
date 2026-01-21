#!/usr/bin/env Rscript
#
# REANALYSIS COMPARISON: RUN A vs RUN B
#
# This script compares two independent LLM analysis runs (A and B) on the same
# Sölle sermons to quantify model output variability and identify patterns.
#
# Key analyses:
# - Score extraction from all 9 domains
# - Paired comparison metrics (differences, correlations)
# - Bland-Altman agreement plots
# - Intraclass Correlation Coefficients (ICC)
# - Heatmaps of variability by domain/score
#
# W.M. Otte (w.m.otte@umcutrecht.nl)
#
# ==============================================================================

library(tidyverse)
library(jsonlite)
library(ggrepel)    # For plot labels

# Manual ICC calculation function (two-way random, agreement)
calc_icc <- function(ratings_matrix) {
  # ratings_matrix: n x 2 matrix (n subjects, 2 raters)
  n <- nrow(ratings_matrix)
  k <- 2  # number of raters

  # Grand mean
  grand_mean <- mean(ratings_matrix, na.rm = TRUE)

  # Subject means (row means)
  subj_means <- rowMeans(ratings_matrix, na.rm = TRUE)

  # Rater means (column means)
  rater_means <- colMeans(ratings_matrix, na.rm = TRUE)

  # Sum of squares
  SS_total <- sum((ratings_matrix - grand_mean)^2, na.rm = TRUE)
  SS_subjects <- k * sum((subj_means - grand_mean)^2, na.rm = TRUE)
  SS_raters <- n * sum((rater_means - grand_mean)^2, na.rm = TRUE)
  SS_error <- SS_total - SS_subjects - SS_raters

  # Mean squares
  MS_subjects <- SS_subjects / (n - 1)
  MS_raters <- SS_raters / (k - 1)
  MS_error <- SS_error / ((n - 1) * (k - 1))

  # ICC(2,1) - Two-way random, single measures, absolute agreement
  icc_val <- (MS_subjects - MS_error) / (MS_subjects + (k - 1) * MS_error + (k / n) * (MS_raters - MS_error))

  # Confidence interval (approximate)
  F_val <- MS_subjects / MS_error
  df1 <- n - 1
  df2 <- (n - 1) * (k - 1)

  # Lower and upper bounds
  F_lower <- F_val / qf(0.975, df1, df2)
  F_upper <- F_val * qf(0.975, df2, df1)

  lower_ci <- (F_lower - 1) / (F_lower + k - 1)
  upper_ci <- (F_upper - 1) / (F_upper + k - 1)

  list(
    value = max(0, min(1, icc_val)),
    lbound = max(0, lower_ci),
    ubound = min(1, upper_ci)
  )
}

# ==============================================================================
# CONFIGURATION
# ==============================================================================

input_dir <- "docs"
output_dir <- "output.reanalysis.same.sermons"

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
  cat("Created output directory:", output_dir, "\n")
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

# Safely extract numeric value from JSON path
safe_extract <- function(json_data, path) {
  tryCatch({
    result <- json_data
    for (key in path) {
      if (is.null(result[[key]])) return(NA_real_)
      result <- result[[key]]
    }
    if (is.numeric(result)) return(as.numeric(result))
    return(NA_real_)
  }, error = function(e) NA_real_)
}

# Extract all scores from a domain JSON
extract_scores <- function(json_data, domain) {
  scores <- list()

  if (domain == "aristoteles") {
    scores$logos <- safe_extract(json_data, c("aristotelian_modes_analysis", "logos", "score"))
    scores$pathos <- safe_extract(json_data, c("aristotelian_modes_analysis", "pathos", "score"))
    scores$ethos <- safe_extract(json_data, c("aristotelian_modes_analysis", "ethos", "score"))
    scores$balance <- safe_extract(json_data, c("rhetorical_balance_analysis", "balance_score"))
    scores$overall_rhetorical <- safe_extract(json_data, c("overall_picture", "overall_rhetorical_score"))
    scores$orthodoxy <- safe_extract(json_data, c("orthodoxy_orthopathy_orthopraxy", "orthodoxy_logos", "score"))
    scores$orthopathy <- safe_extract(json_data, c("orthodoxy_orthopathy_orthopraxy", "orthopathy_pathos", "score"))
    scores$orthopraxy <- safe_extract(json_data, c("orthodoxy_orthopathy_orthopraxy", "orthopraxy_ethos", "score"))

  } else if (domain == "dekker") {
    criteria <- c("1_specific_bible_passage", "2_exegesis_original_context",
                  "3_application_concrete_contemporary", "4_interwoveness_exposition_application",
                  "5_three_parts_misery_redemption_gratitude", "6_two_ways_seriousness_of_choice",
                  "7_christocentric_grace", "8_depth_and_length")
    for (i in seq_along(criteria)) {
      scores[[paste0("criterion_", i)]] <- safe_extract(json_data, c("analysis_per_criterion", criteria[i], "score_1_to_10"))
    }

  } else if (domain == "esthetiek") {
    scores$imagery <- safe_extract(json_data, c("domain_a_poetics_of_language", "criterion_a1_imagery", "score"))
    scores$precision <- safe_extract(json_data, c("domain_a_poetics_of_language", "criterion_a2_carefulness_and_precision", "score"))
    scores$musicality <- safe_extract(json_data, c("domain_a_poetics_of_language", "criterion_a3_musicality_and_rhythm", "score"))
    scores$narrative_arc <- safe_extract(json_data, c("domain_b_dramaturgy_of_structure", "criterion_b1_narrative_arc", "score"))
    scores$integration <- safe_extract(json_data, c("domain_b_dramaturgy_of_structure", "criterion_b2_integration_text_and_context", "score"))
    scores$openness <- safe_extract(json_data, c("domain_b_dramaturgy_of_structure", "criterion_b3_openness_vs_closedness", "score"))
    scores$anti_kitsch <- safe_extract(json_data, c("kitsch_diagnosis", "anti_kitsch_score"))
    scores$space_grace <- safe_extract(json_data, c("space_for_grace_analysis", "space_score"))
    scores$overall_aesthetic <- safe_extract(json_data, c("overall_aesthetics", "overall_aesthetic_score"))

  } else if (domain == "kolb") {
    # Kolb phases
    scores$phase1_concrete <- safe_extract(json_data, c("kolb_phases_analysis", "phase_1_concrete_experience", "score"))
    scores$phase2_reflective <- safe_extract(json_data, c("kolb_phases_analysis", "phase_2_reflective_observation", "score"))
    scores$phase3_abstract <- safe_extract(json_data, c("kolb_phases_analysis", "phase_3_abstract_conceptualization", "score"))
    scores$phase4_active <- safe_extract(json_data, c("kolb_phases_analysis", "phase_4_active_experimentation", "score"))
    # Anderson structures
    scores$declarative <- safe_extract(json_data, c("anderson_structures_analysis", "declarative_assimilating", "score"))
    scores$pragmatic <- safe_extract(json_data, c("anderson_structures_analysis", "pragmatic_converging", "score"))
    scores$narrative <- safe_extract(json_data, c("anderson_structures_analysis", "narrative_accommodating", "score"))
    scores$visionary <- safe_extract(json_data, c("anderson_structures_analysis", "visionary_diverging", "score"))
    # Osmer tasks
    scores$osmer_descriptive <- safe_extract(json_data, c("osmer_tasks_analysis", "descriptive_empirical", "score"))
    scores$osmer_interpretive <- safe_extract(json_data, c("osmer_tasks_analysis", "interpretive", "score"))
    scores$osmer_normative <- safe_extract(json_data, c("osmer_tasks_analysis", "normative", "score"))
    scores$osmer_pragmatic <- safe_extract(json_data, c("osmer_tasks_analysis", "pragmatic", "score"))
    # Learning styles
    scores$style_assimilating <- safe_extract(json_data, c("learning_styles_analysis", "assimilating_style", "score"))
    scores$style_converging <- safe_extract(json_data, c("learning_styles_analysis", "converging_style", "score"))
    scores$style_accommodating <- safe_extract(json_data, c("learning_styles_analysis", "accommodating_style", "score"))
    scores$style_diverging <- safe_extract(json_data, c("learning_styles_analysis", "diverging_style", "score"))
    # Overall
    scores$overall_kolb <- safe_extract(json_data, c("overall_picture", "overall_kolb_score"))

  } else if (domain == "schulz_von_thun") {
    scores$factual_blue <- safe_extract(json_data, c("schulz_von_thun_analysis", "factual_content_blue", "score"))
    scores$self_green <- safe_extract(json_data, c("schulz_von_thun_analysis", "self_revelation_green", "score"))
    scores$relational_yellow <- safe_extract(json_data, c("schulz_von_thun_analysis", "relational_aspect_yellow", "score"))
    scores$appeal_red <- safe_extract(json_data, c("schulz_von_thun_analysis", "appeal_aspect_red", "score"))
    scores$overall_communication <- safe_extract(json_data, c("overall_picture", "overall_communication_score"))

  } else if (domain == "transactional") {
    scores$freedom_cp <- safe_extract(json_data, c("ego_positions_scan", "parent", "freedom_from_critical_parent_CP", "score"))
    scores$healthy_np <- safe_extract(json_data, c("ego_positions_scan", "parent", "healthy_care_NP", "score"))
    scores$adult <- safe_extract(json_data, c("ego_positions_scan", "adult", "score"))
    scores$freedom_ac <- safe_extract(json_data, c("ego_positions_scan", "child", "freedom_from_adapted_child_AC", "score"))
    scores$free_child <- safe_extract(json_data, c("ego_positions_scan", "child", "free_child_FC", "score"))
    scores$purity <- safe_extract(json_data, c("transaction_analysis", "communicative_purity_score"))
    scores$psych_health <- safe_extract(json_data, c("conclusion_and_recommendation", "psychological_health_score"))

  } else if (domain == "metaphor") {
    # Extract prominentie_score from dominant domains (first 3)
    dom_domeinen <- json_data$primaire_analyse$dominante_domeinen
    if (!is.null(dom_domeinen) && length(dom_domeinen) >= 1) {
      scores$domain1_prominentie <- safe_extract(dom_domeinen[[1]], c("prominentie_score"))
    }
    if (!is.null(dom_domeinen) && length(dom_domeinen) >= 2) {
      scores$domain2_prominentie <- safe_extract(dom_domeinen[[2]], c("prominentie_score"))
    }
    if (!is.null(dom_domeinen) && length(dom_domeinen) >= 3) {
      scores$domain3_prominentie <- safe_extract(dom_domeinen[[3]], c("prominentie_score"))
    }

  } else if (domain == "speech_act") {
    # Threefold structure
    scores$locutie_omvang <- safe_extract(json_data, c("drievoudige_structuur_analyse", "locutie", "omvang_procent"))
    scores$illocutie_helderheid <- safe_extract(json_data, c("drievoudige_structuur_analyse", "illocutie", "helderheid_score"))
    # Verb categories (percentages)
    scores$assertieven_pct <- safe_extract(json_data, c("werkwoord_analyse", "assertieven", "procent"))
    scores$directieven_pct <- safe_extract(json_data, c("werkwoord_analyse", "directieven", "procent"))
    scores$expressieven_pct <- safe_extract(json_data, c("werkwoord_analyse", "expressieven", "procent"))
    scores$commissieven_pct <- safe_extract(json_data, c("werkwoord_analyse", "commissieven", "procent"))
    scores$declaratieven_pct <- safe_extract(json_data, c("werkwoord_analyse", "declaratieven", "procent"))
    # Constative/Performative
    scores$constatief_pct <- safe_extract(json_data, c("constatief_performatief_diagnose", "constatief_percentage"))
    scores$performatief_pct <- safe_extract(json_data, c("constatief_performatief_diagnose", "performatief_percentage"))
    # Addressing
    scores$adressering_effectiviteit <- safe_extract(json_data, c("adressering_analyse", "adressering_effectiviteit"))
    # Diagnostic scores
    scores$gebeuren_score <- safe_extract(json_data, c("diagnostische_evaluatie", "gebeuren_score"))
    scores$sacramentele_kracht <- safe_extract(json_data, c("diagnostische_evaluatie", "sacramentele_kracht"))

  } else if (domain == "narrative") {
    # Subject frequency score
    scores$subject_frequentie <- safe_extract(json_data, c("actantiele_analyse", "primair_narratief_programma", "subject", "frequentie_score"))
    # Grammatical analysis
    scores$god_subject_count <- safe_extract(json_data, c("grammaticale_analyse", "subject_check", "god_als_subject_count"))
    scores$mens_subject_count <- safe_extract(json_data, c("grammaticale_analyse", "subject_check", "mens_als_subject_count"))
    scores$rutledge_score <- safe_extract(json_data, c("grammaticale_analyse", "subject_check", "rutledge_score"))
    # Modal prominences
    scores$modal_devoir <- safe_extract(json_data, c("grammaticale_analyse", "modale_analyse", "devoir_faire", "prominentie"))
    scores$modal_vouloir <- safe_extract(json_data, c("grammaticale_analyse", "modale_analyse", "vouloir_faire", "prominentie"))
    scores$modal_savoir <- safe_extract(json_data, c("grammaticale_analyse", "modale_analyse", "savoir_faire", "prominentie"))
    scores$modal_pouvoir <- safe_extract(json_data, c("grammaticale_analyse", "modale_analyse", "pouvoir_faire", "prominentie"))
    # Narrative coherence
    scores$coherentie_score <- safe_extract(json_data, c("diagnostische_evaluatie", "narratieve_coherentie", "coherentie_score"))
  }

  return(scores)
}

# ==============================================================================
# LOAD AND PARSE ALL JSON FILES
# ==============================================================================

cat("Loading JSON files...\n")

domains <- c("aristoteles", "dekker", "esthetiek", "kolb", "schulz_von_thun", "transactional", "metaphor", "speech_act", "narrative")

# Find all Sölle files
solle_files_A <- list.files(input_dir, pattern = "^solle_\\d+_[a-z_]+\\.json$", full.names = TRUE)
solle_files_B <- list.files(input_dir, pattern = "^solle_\\d+_B_[a-z_]+\\.json$", full.names = TRUE)

# Extract sermon numbers from A files
get_sermon_num <- function(filepath) {
  basename(filepath) %>%
    str_extract("solle_(\\d+)", group = 1) %>%
    as.integer()
}

get_domain <- function(filepath) {
  basename(filepath) %>%
    str_remove("^solle_\\d+_") %>%
    str_remove("^B_") %>%
    str_remove("\\.json$")
}

# Build data frames
all_scores <- tibble()

for (domain in domains) {
  cat("  Processing domain:", domain, "\n")

  # Get A and B files for this domain
  a_files <- solle_files_A[str_detect(solle_files_A, paste0("_", domain, "\\.json$"))]
  b_files <- solle_files_B[str_detect(solle_files_B, paste0("_", domain, "\\.json$"))]

  # Get sermon numbers that have both A and B
  a_sermons <- sapply(a_files, get_sermon_num)
  b_sermons <- sapply(b_files, get_sermon_num)
  paired_sermons <- intersect(a_sermons, b_sermons)

  cat("    Found", length(paired_sermons), "paired sermons\n")

  for (sermon_num in paired_sermons) {
    # Find corresponding files
    a_file <- a_files[sapply(a_files, get_sermon_num) == sermon_num]
    b_file <- b_files[sapply(b_files, get_sermon_num) == sermon_num]

    if (length(a_file) == 1 && length(b_file) == 1) {
      # Load JSONs
      json_a <- tryCatch(read_json(a_file), error = function(e) NULL)
      json_b <- tryCatch(read_json(b_file), error = function(e) NULL)

      if (!is.null(json_a) && !is.null(json_b)) {
        # Extract scores
        scores_a <- extract_scores(json_a, domain)
        scores_b <- extract_scores(json_b, domain)

        # Create rows for each score
        for (score_name in names(scores_a)) {
          all_scores <- bind_rows(all_scores, tibble(
            sermon = sermon_num,
            domain = domain,
            score_type = score_name,
            run_A = scores_a[[score_name]],
            run_B = scores_b[[score_name]]
          ))
        }
      }
    }
  }
}

cat("\nTotal score comparisons:", nrow(all_scores), "\n")

# ==============================================================================
# CALCULATE DIFFERENCE METRICS
# ==============================================================================

cat("\nCalculating difference metrics...\n")

all_scores <- all_scores %>%
  filter(!is.na(run_A) & !is.na(run_B)) %>%
  mutate(
    difference = run_B - run_A,
    abs_difference = abs(difference),
    mean_score = (run_A + run_B) / 2,
    pct_difference = ifelse(mean_score != 0, abs_difference / mean_score * 100, NA)
  )

cat("Valid paired comparisons:", nrow(all_scores), "\n")

# Save raw comparison data
write_csv(all_scores, file.path(output_dir, "paired_comparison_data.csv"))

# ==============================================================================
# SUMMARY STATISTICS
# ==============================================================================

cat("\nGenerating summary statistics...\n")

# Overall summary
overall_summary <- all_scores %>%
  summarise(
    n_comparisons = n(),
    mean_abs_diff = mean(abs_difference, na.rm = TRUE),
    sd_abs_diff = sd(abs_difference, na.rm = TRUE),
    median_abs_diff = median(abs_difference, na.rm = TRUE),
    max_abs_diff = max(abs_difference, na.rm = TRUE),
    exact_matches = sum(difference == 0),
    pct_exact = mean(difference == 0) * 100,
    within_1pt = sum(abs_difference <= 1),
    pct_within_1pt = mean(abs_difference <= 1) * 100,
    correlation = cor(run_A, run_B, use = "complete.obs")
  )

# Summary by domain
domain_summary <- all_scores %>%
  group_by(domain) %>%
  summarise(
    n_scores = n(),
    mean_abs_diff = mean(abs_difference, na.rm = TRUE),
    sd_abs_diff = sd(abs_difference, na.rm = TRUE),
    median_abs_diff = median(abs_difference, na.rm = TRUE),
    max_abs_diff = max(abs_difference, na.rm = TRUE),
    exact_matches = sum(difference == 0),
    pct_exact = mean(difference == 0) * 100,
    pct_within_1pt = mean(abs_difference <= 1) * 100,
    correlation = cor(run_A, run_B, use = "complete.obs"),
    .groups = "drop"
  ) %>%
  arrange(desc(mean_abs_diff))

# Summary by score type within domain
score_type_summary <- all_scores %>%
  group_by(domain, score_type) %>%
  summarise(
    n = n(),
    mean_A = mean(run_A, na.rm = TRUE),
    mean_B = mean(run_B, na.rm = TRUE),
    mean_diff = mean(difference, na.rm = TRUE),
    mean_abs_diff = mean(abs_difference, na.rm = TRUE),
    sd_diff = sd(difference, na.rm = TRUE),
    correlation = cor(run_A, run_B, use = "complete.obs"),
    .groups = "drop"
  ) %>%
  arrange(domain, desc(mean_abs_diff))

# Save summaries
write_csv(overall_summary, file.path(output_dir, "summary_overall.csv"))
write_csv(domain_summary, file.path(output_dir, "summary_by_domain.csv"))
write_csv(score_type_summary, file.path(output_dir, "summary_by_score_type.csv"))

# ==============================================================================
# INTRACLASS CORRELATION COEFFICIENT (ICC)
# ==============================================================================

cat("\nCalculating ICC...\n")

# Overall ICC
icc_data <- all_scores %>%
  select(run_A, run_B) %>%
  as.matrix()

icc_result <- calc_icc(icc_data)

icc_summary <- tibble(
  scope = "overall",
  icc_value = icc_result$value,
  lower_ci = icc_result$lbound,
  upper_ci = icc_result$ubound,
  interpretation = case_when(
    icc_result$value >= 0.9 ~ "Excellent",
    icc_result$value >= 0.75 ~ "Good",
    icc_result$value >= 0.5 ~ "Moderate",
    TRUE ~ "Poor"
  )
)

# ICC by domain
for (d in domains) {
  domain_data <- all_scores %>%
    filter(domain == d) %>%
    select(run_A, run_B) %>%
    as.matrix()

  if (nrow(domain_data) >= 3) {
    icc_d <- tryCatch(
      calc_icc(domain_data),
      error = function(e) list(value = NA, lbound = NA, ubound = NA)
    )

    icc_summary <- bind_rows(icc_summary, tibble(
      scope = d,
      icc_value = icc_d$value,
      lower_ci = icc_d$lbound,
      upper_ci = icc_d$ubound,
      interpretation = case_when(
        is.na(icc_d$value) ~ "N/A",
        icc_d$value >= 0.9 ~ "Excellent",
        icc_d$value >= 0.75 ~ "Good",
        icc_d$value >= 0.5 ~ "Moderate",
        TRUE ~ "Poor"
      )
    ))
  }
}

write_csv(icc_summary, file.path(output_dir, "icc_summary.csv"))

# ==============================================================================
# VISUALIZATIONS
# ==============================================================================

cat("\nGenerating visualizations...\n")

# Color palette
domain_colors <- c(
  "aristoteles" = "#E41A1C",
  "dekker" = "#377EB8",
  "esthetiek" = "#4DAF4A",
  "kolb" = "#984EA3",
  "schulz_von_thun" = "#FF7F00",
  "transactional" = "#A65628",
  "metaphor" = "#F781BF",
  "speech_act" = "#999999",
  "narrative" = "#66C2A5"
)

# 1. SCATTER PLOT: Run A vs Run B
p1 <- all_scores %>%
  ggplot(aes(x = run_A, y = run_B, color = domain)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "gray40") +
  geom_point(alpha = 0.6, size = 2) +
  scale_color_manual(values = domain_colors) +
  coord_fixed(xlim = c(0, 10), ylim = c(0, 10)) +
  theme_minimal() +
  theme(legend.position = "bottom") +
  labs(
    title = "Run A vs Run B: Score Agreement",
    subtitle = paste0("Pearson r = ", round(cor(all_scores$run_A, all_scores$run_B), 3)),
    x = "Score (Run A)",
    y = "Score (Run B)",
    color = "Domain"
  )

ggsave(file.path(output_dir, "plot_scatter_agreement.pdf"), p1, width = 8, height = 8)

# 2. BLAND-ALTMAN PLOT
p2 <- all_scores %>%
  ggplot(aes(x = mean_score, y = difference, color = domain)) +
  geom_hline(yintercept = 0, linetype = "solid", color = "gray40") +
  geom_hline(yintercept = c(-1.96 * sd(all_scores$difference), 1.96 * sd(all_scores$difference)),
             linetype = "dashed", color = "red", alpha = 0.7) +
  geom_hline(yintercept = mean(all_scores$difference), linetype = "dashed", color = "blue") +
  geom_point(alpha = 0.6, size = 2) +
  scale_color_manual(values = domain_colors) +
  theme_minimal() +
  theme(legend.position = "bottom") +
  labs(
    title = "Bland-Altman Plot: Agreement Between Runs",
    subtitle = paste0("Mean difference = ", round(mean(all_scores$difference), 3),
                      ", 95% LoA = [", round(mean(all_scores$difference) - 1.96*sd(all_scores$difference), 2),
                      ", ", round(mean(all_scores$difference) + 1.96*sd(all_scores$difference), 2), "]"),
    x = "Mean Score (A + B) / 2",
    y = "Difference (B - A)",
    color = "Domain"
  )

ggsave(file.path(output_dir, "plot_bland_altman.pdf"), p2, width = 10, height = 7)

# 3. BOX PLOT: Absolute Differences by Domain
p3 <- all_scores %>%
  ggplot(aes(x = reorder(domain, abs_difference, FUN = median), y = abs_difference, fill = domain)) +
  geom_boxplot(alpha = 0.7, outlier.alpha = 0.5) +
  geom_jitter(width = 0.2, alpha = 0.3, size = 1) +
  scale_fill_manual(values = domain_colors) +
  coord_flip() +
  theme_minimal() +
  theme(legend.position = "none") +
  labs(
    title = "Score Variability by Domain",
    subtitle = "Absolute difference between Run A and Run B",
    x = NULL,
    y = "Absolute Difference (points)"
  )

ggsave(file.path(output_dir, "plot_boxplot_domains.pdf"), p3, width = 9, height = 6)

# 4. HEATMAP: Mean Absolute Difference by Domain and Score Type
heatmap_data <- score_type_summary %>%
  select(domain, score_type, mean_abs_diff) %>%
  mutate(
    score_label = str_replace_all(score_type, "_", " ") %>% str_to_title()
  )

p4 <- heatmap_data %>%
  ggplot(aes(x = domain, y = reorder(score_label, mean_abs_diff), fill = mean_abs_diff)) +
  geom_tile(color = "white", linewidth = 0.5) +
  geom_text(aes(label = round(mean_abs_diff, 2)), size = 2.5, color = "black") +
  scale_fill_gradient2(
    low = "#2166AC", mid = "#F7F7F7", high = "#B2182B",
    midpoint = 1, limits = c(0, max(heatmap_data$mean_abs_diff, na.rm = TRUE)),
    name = "Mean |Diff|"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, size = 9),
    axis.text.y = element_text(size = 7),
    panel.grid = element_blank()
  ) +
  labs(
    title = "Variability Heatmap: Mean Absolute Difference",
    subtitle = "By domain and score type (lighter = more stable)",
    x = NULL,
    y = NULL
  )

ggsave(file.path(output_dir, "plot_heatmap_variability.pdf"), p4, width = 10, height = 14)

# 5. HISTOGRAM: Distribution of Differences
p5 <- all_scores %>%
  ggplot(aes(x = difference, fill = domain)) +
  geom_histogram(binwidth = 0.5, alpha = 0.7, position = "identity") +
  geom_vline(xintercept = 0, linetype = "dashed", color = "black") +
  scale_fill_manual(values = domain_colors) +
  facet_wrap(~ domain, scales = "free_y", ncol = 2) +
  theme_minimal() +
  theme(legend.position = "none") +
  labs(
    title = "Distribution of Score Differences (B - A)",
    subtitle = "Centered at 0 indicates no systematic bias",
    x = "Difference (Run B - Run A)",
    y = "Count"
  )

ggsave(file.path(output_dir, "plot_histogram_differences.pdf"), p5, width = 10, height = 8)

# 6. STABILITY PLOT: Agreement by Sermon
sermon_summary <- all_scores %>%
  group_by(sermon) %>%
  summarise(
    mean_abs_diff = mean(abs_difference, na.rm = TRUE),
    n_scores = n(),
    .groups = "drop"
  )

p6 <- sermon_summary %>%
  ggplot(aes(x = factor(sermon), y = mean_abs_diff)) +
  geom_bar(stat = "identity", fill = "#4DAF4A", alpha = 0.7) +
  geom_hline(yintercept = mean(sermon_summary$mean_abs_diff), linetype = "dashed", color = "red") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1)) +
  labs(
    title = "Mean Variability by Sermon",
    subtitle = paste0("Red line = overall mean (", round(mean(sermon_summary$mean_abs_diff), 2), ")"),
    x = "Sermon Number",
    y = "Mean Absolute Difference"
  )

ggsave(file.path(output_dir, "plot_variability_by_sermon.pdf"), p6, width = 12, height = 6)

# 7. CORRELATION MATRIX BY DOMAIN
cor_matrix <- domain_summary %>%
  select(domain, correlation) %>%
  mutate(correlation = round(correlation, 3))

p7 <- cor_matrix %>%
  ggplot(aes(x = reorder(domain, correlation), y = 1, fill = correlation)) +
  geom_tile(color = "white", linewidth = 1) +
  geom_text(aes(label = correlation), size = 5, fontface = "bold") +
  scale_fill_gradient2(
    low = "#D73027", mid = "#FFFFBF", high = "#1A9850",
    midpoint = 0.8, limits = c(0.5, 1),
    name = "Correlation"
  ) +
  coord_flip() +
  theme_minimal() +
  theme(
    axis.text.x = element_blank(),
    axis.ticks = element_blank(),
    panel.grid = element_blank()
  ) +
  labs(
    title = "Run A-B Correlation by Domain",
    subtitle = "Higher values indicate better agreement",
    x = NULL, y = NULL
  )

ggsave(file.path(output_dir, "plot_correlation_by_domain.pdf"), p7, width = 8, height = 5)

# 8. EXACT MATCH vs DEVIATION PLOT
agreement_levels <- all_scores %>%
  mutate(
    agreement_level = case_when(
      abs_difference == 0 ~ "Exact match (0)",
      abs_difference <= 0.5 ~ "Within 0.5",
      abs_difference <= 1 ~ "Within 1",
      abs_difference <= 2 ~ "Within 2",
      TRUE ~ "> 2 points"
    )
  ) %>%
  count(domain, agreement_level) %>%
  group_by(domain) %>%
  mutate(pct = n / sum(n) * 100) %>%
  ungroup()

agreement_levels$agreement_level <- factor(
  agreement_levels$agreement_level,
  levels = c("Exact match (0)", "Within 0.5", "Within 1", "Within 2", "> 2 points")
)

p8 <- agreement_levels %>%
  ggplot(aes(x = domain, y = pct, fill = agreement_level)) +
  geom_bar(stat = "identity", position = "stack") +
  scale_fill_manual(values = c(
    "Exact match (0)" = "#1A9850",
    "Within 0.5" = "#91CF60",
    "Within 1" = "#FFFFBF",
    "Within 2" = "#FEE08B",
    "> 2 points" = "#D73027"
  ), name = "Agreement") +
  coord_flip() +
  theme_minimal() +
  labs(
    title = "Agreement Level Distribution by Domain",
    subtitle = "Green = exact match, Red = large deviation",
    x = NULL,
    y = "Percentage of scores"
  )

ggsave(file.path(output_dir, "plot_agreement_levels.pdf"), p8, width = 10, height = 6)

# ==============================================================================
# WRITE FINDINGS REPORT
# ==============================================================================

cat("\nWriting findings report...\n")

findings_text <- paste0(
"================================================================================
REANALYSIS COMPARISON: RUN A vs RUN B
D. Sölle Sermons - Model Output Variability Analysis
================================================================================

EXECUTIVE SUMMARY
-----------------
This analysis compares two independent LLM analysis runs (A and B) on the same
set of D. Sölle sermons across 9 analytical domains to quantify model output
variability and assess reliability.

OVERALL STATISTICS
------------------
Total paired comparisons: ", overall_summary$n_comparisons, "
Mean absolute difference: ", round(overall_summary$mean_abs_diff, 3), " points
SD of absolute difference: ", round(overall_summary$sd_abs_diff, 3), " points
Median absolute difference: ", round(overall_summary$median_abs_diff, 3), " points
Maximum absolute difference: ", overall_summary$max_abs_diff, " points

AGREEMENT METRICS
-----------------
Exact matches (difference = 0): ", overall_summary$exact_matches, " (", round(overall_summary$pct_exact, 1), "%)
Within 1 point: ", overall_summary$within_1pt, " (", round(overall_summary$pct_within_1pt, 1), "%)
Overall correlation (Pearson r): ", round(overall_summary$correlation, 3), "
Overall ICC: ", round(icc_summary$icc_value[1], 3), " [", round(icc_summary$lower_ci[1], 3), "-", round(icc_summary$upper_ci[1], 3), "] - ", icc_summary$interpretation[1], "

DOMAIN-LEVEL FINDINGS
---------------------
Ranked by mean absolute difference (highest variability first):

", paste(
  sprintf("%d. %s: Mean |diff| = %.2f, Correlation = %.3f, Exact matches = %.1f%%",
          1:nrow(domain_summary),
          domain_summary$domain,
          domain_summary$mean_abs_diff,
          domain_summary$correlation,
          domain_summary$pct_exact),
  collapse = "\n"
), "

KEY INSIGHTS
------------
1. CONSISTENCY LEVEL: The overall ICC of ", round(icc_summary$icc_value[1], 3), " indicates ", tolower(icc_summary$interpretation[1]),
" agreement between runs, suggesting the LLM produces relatively consistent scores
   when analyzing the same sermon content.

2. SYSTEMATIC BIAS: The mean difference (B - A) of ", round(mean(all_scores$difference), 3), " suggests ",
ifelse(abs(mean(all_scores$difference)) < 0.1, "no systematic bias",
       ifelse(mean(all_scores$difference) > 0, "Run B tends to score slightly higher", "Run B tends to score slightly lower")),
" between runs.

3. DOMAIN VARIABILITY: ", domain_summary$domain[1], " shows the highest variability (",
round(domain_summary$mean_abs_diff[1], 2), " mean |diff|), while ",
domain_summary$domain[nrow(domain_summary)], " is most stable (",
round(domain_summary$mean_abs_diff[nrow(domain_summary)], 2), " mean |diff|).

4. SCORE TYPE VARIABILITY: Some specific score types within domains show notably
   higher variability than others (see heatmap and summary_by_score_type.csv).

5. PRACTICAL INTERPRETATION: With ", round(overall_summary$pct_within_1pt, 1), "% of scores within 1 point
   difference, the model shows acceptable reliability for comparative analysis
   across sermons, though individual scores should be interpreted with caution
   (typical uncertainty of ~", round(overall_summary$mean_abs_diff, 1), " points).

RECOMMENDATIONS
---------------
- When comparing sermons, focus on differences > ", round(2 * overall_summary$sd_abs_diff, 1), " points for confidence
- Consider averaging multiple runs for high-stakes analyses
- Domain-specific findings should weight reliability levels appropriately
- Absolute scores are less reliable than relative rankings

OUTPUT FILES
------------
- paired_comparison_data.csv: Raw paired comparison data
- summary_overall.csv: Overall summary statistics
- summary_by_domain.csv: Domain-level summary
- summary_by_score_type.csv: Score type-level summary
- icc_summary.csv: Intraclass correlation coefficients
- plot_*.pdf: Various visualization files

================================================================================
Analysis completed: ", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "
================================================================================
"
)

writeLines(findings_text, file.path(output_dir, "FINDINGS_REPORT.txt"))

# ==============================================================================
# FINAL OUTPUT
# ==============================================================================

cat("\n================================================================================\n")
cat("ANALYSIS COMPLETE\n")
cat("================================================================================\n")
cat("Output directory:", output_dir, "\n\n")
cat("Key findings:\n")
cat("  - Overall ICC:", round(icc_summary$icc_value[1], 3), "(", icc_summary$interpretation[1], ")\n")
cat("  - Mean absolute difference:", round(overall_summary$mean_abs_diff, 3), "points\n")
cat("  - Correlation (A vs B):", round(overall_summary$correlation, 3), "\n")
cat("  - Exact matches:", overall_summary$pct_exact, "%\n")
cat("  - Within 1 point:", round(overall_summary$pct_within_1pt, 1), "%\n")
cat("\nMost variable domain:", domain_summary$domain[1], "\n")
cat("Most stable domain:", domain_summary$domain[nrow(domain_summary)], "\n")
cat("================================================================================\n")
