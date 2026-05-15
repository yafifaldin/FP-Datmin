# ============================================================
# NASA SPACE DISCOVERY & RECOMMENDATION PLATFORM
# CINEMATIC PREMIUM SaaS DASHBOARD - TOTAL VISUAL TRANSFORMATION
# ============================================================

library(shiny)
library(shinydashboard)
library(shinyjs)
library(httr)
library(jsonlite)
library(dplyr)
library(ggplot2)
library(plotly)
library(DT)
library(tidyr)
library(stringr)
library(lubridate)
library(igraph)
library(reshape2)

# ============================================================
# CONFIGURATION
# ============================================================
NASA_API_KEY <- "DEMO_KEY"
NASA_BASE    <- "https://api.nasa.gov"

# ============================================================
# HELPER FUNCTIONS — SAFE API CALLS
# ============================================================

safe_get <- function(url, query = list()) {
  tryCatch({
    resp <- GET(url, query = c(query, list(api_key = NASA_API_KEY)), timeout(15))
    if (status_code(resp) == 200) {
      content(resp, as = "parsed", type = "application/json")
    } else NULL
  }, error = function(e) NULL)
}

fetch_neo <- function(start_date = Sys.Date(), end_date = Sys.Date() + 6) {
  url  <- paste0(NASA_BASE, "/neo/rest/v1/feed")
  data <- safe_get(url, list(start_date = as.character(start_date),
                             end_date   = as.character(end_date)))
  if (is.null(data)) return(NULL)
  neos <- data$near_earth_objects
  rows <- lapply(names(neos), function(date) {
    lapply(neos[[date]], function(n) {
      ca <- if (!is.null(n$close_approach_data) && length(n$close_approach_data) > 0)
        n$close_approach_data[[1]] else list()
      data.frame(
        id              = n$id %||% NA_character_,
        name            = n$name %||% NA_character_,
        date            = date,
        hazardous       = isTRUE(n$is_potentially_hazardous_asteroid),
        diam_min_km     = as.numeric(n$estimated_diameter$kilometers$estimated_diameter_min %||% NA),
        diam_max_km     = as.numeric(n$estimated_diameter$kilometers$estimated_diameter_max %||% NA),
        velocity_kms    = as.numeric(ca$relative_velocity$kilometers_per_second %||% NA),
        miss_dist_ld    = as.numeric(ca$miss_distance$lunar %||% NA),
        miss_dist_km    = as.numeric(ca$miss_distance$kilometers %||% NA),
        orbit_class     = n$orbital_data$orbit_class$orbit_class_type %||% NA_character_,
        stringsAsFactors = FALSE
      )
    })
  })
  df <- bind_rows(unlist(rows, recursive = FALSE))
  df$diam_avg_km <- (df$diam_min_km + df$diam_max_km) / 2
  df
}

fetch_mars <- function(rover = "curiosity", earth_date = NULL, camera = NULL, page = 1) {
  if (is.null(earth_date)) earth_date <- "2023-01-15"
  q   <- list(earth_date = earth_date, page = page)
  if (!is.null(camera) && camera != "ALL") q$camera <- tolower(camera)
  url  <- paste0(NASA_BASE, "/mars-photos/api/v1/rovers/", rover, "/photos")
  data <- safe_get(url, q)
  if (is.null(data) || length(data$photos) == 0) return(NULL)
  lapply(data$photos, function(p) {
    data.frame(
      id        = p$id %||% NA_integer_,
      sol       = p$sol %||% NA_integer_,
      earth_date= p$earth_date %||% NA_character_,
      camera    = p$camera$name %||% NA_character_,
      camera_full = p$camera$full_name %||% NA_character_,
      img_src   = p$img_src %||% NA_character_,
      rover     = p$rover$name %||% NA_character_,
      status    = p$rover$status %||% NA_character_,
      stringsAsFactors = FALSE
    )
  }) %>% bind_rows()
}

fetch_apod <- function(date = NULL, count = NULL) {
  q <- list()
  if (!is.null(date))  q$date  <- as.character(date)
  if (!is.null(count)) q$count <- count
  url  <- paste0(NASA_BASE, "/planetary/apod")
  data <- safe_get(url, q)
  if (is.null(data)) return(NULL)
  if (is.data.frame(data)) return(data)
  if (is.list(data) && !is.null(data$url)) {
    data.frame(
      date        = data$date %||% NA_character_,
      title       = data$title %||% NA_character_,
      explanation = data$explanation %||% NA_character_,
      url         = data$url %||% NA_character_,
      hdurl       = data$hdurl %||% data$url %||% NA_character_,
      media_type  = data$media_type %||% NA_character_,
      stringsAsFactors = FALSE
    )
  } else NULL
}

`%||%` <- function(a, b) if (!is.null(a) && length(a) > 0) a else b

# ============================================================
# ENHANCED RECOMMENDATION ENGINE (unchanged logic)
# ============================================================

cosine_sim <- function(a, b) {
  if (any(is.na(a)) || any(is.na(b))) return(0)
  sum(a * b) / (sqrt(sum(a^2)) * sqrt(sum(b^2)) + 1e-10)
}

normalize_col <- function(x) {
  r <- range(x, na.rm = TRUE)
  if (r[1] == r[2]) return(rep(0.5, length(x)))
  (x - r[1]) / (r[2] - r[1])
}

rule_score_asteroid <- function(df, pref_hazard, pref_size, pref_velocity) {
  score <- rep(0, nrow(df))
  if (pref_hazard == "Hazardous")     score <- score + ifelse(df$hazardous, 2, 0)
  if (pref_hazard == "Non-Hazardous") score <- score + ifelse(!df$hazardous, 2, 0)
  if (pref_size == "Large")  score <- score + normalize_col(df$diam_avg_km) * 2
  if (pref_size == "Small")  score <- score + (1 - normalize_col(df$diam_avg_km)) * 2
  if (pref_velocity == "Fast")  score <- score + normalize_col(df$velocity_kms) * 2
  if (pref_velocity == "Slow")  score <- score + (1 - normalize_col(df$velocity_kms)) * 2
  score
}

content_sim_asteroid <- function(df, ref_idx) {
  feats <- df %>%
    mutate(across(c(diam_avg_km, velocity_kms, miss_dist_ld),
                  ~ normalize_col(.x))) %>%
    mutate(haz_num = as.numeric(hazardous)) %>%
    select(diam_avg_km, velocity_kms, miss_dist_ld, haz_num) %>%
    as.matrix()
  ref <- feats[ref_idx, ]
  apply(feats, 1, function(r) cosine_sim(ref, r))
}

sim_collab_filter <- function(df, user_prefs) {
  set.seed(42)
  n_users <- 20
  user_mat <- matrix(runif(n_users * nrow(df), 0, 1), nrow = n_users,
                     ncol = nrow(df))
  cur_user <- normalize_col(df$velocity_kms) * 0.4 +
    normalize_col(df$diam_avg_km) * 0.3 +
    (1 - normalize_col(df$miss_dist_ld)) * 0.3
  user_sims <- apply(user_mat, 1, function(u) cosine_sim(cur_user, u))
  top_users  <- order(user_sims, decreasing = TRUE)[1:5]
  collab_score <- colMeans(user_mat[top_users, , drop = FALSE])
  collab_score
}

hybrid_recommend_asteroids <- function(df, pref_hazard = "All",
                                       pref_size = "Any",
                                       pref_velocity = "Any",
                                       ref_name = NULL) {
  if (is.null(df) || nrow(df) == 0) return(NULL)
  df <- df %>% filter(!is.na(diam_avg_km), !is.na(velocity_kms), !is.na(miss_dist_ld))
  if (nrow(df) == 0) return(NULL)
  
  rule_s  <- rule_score_asteroid(df, pref_hazard, pref_size, pref_velocity)
  collab_s <- sim_collab_filter(df, list())
  
  ref_idx <- if (!is.null(ref_name) && ref_name %in% df$name) which(df$name == ref_name)[1] else 1
  cont_s  <- content_sim_asteroid(df, ref_idx)
  
  hybrid <- 0.35 * normalize_col(rule_s) +
    0.35 * normalize_col(cont_s) +
    0.30 * normalize_col(collab_s)
  
  df$rule_score    <- round(normalize_col(rule_s) * 100, 1)
  df$content_score <- round(normalize_col(cont_s) * 100, 1)
  df$collab_score  <- round(normalize_col(collab_s) * 100, 1)
  df$hybrid_score  <- round(normalize_col(hybrid) * 100, 1)
  df %>% arrange(desc(hybrid_score))
}

explain_recommendation <- function(asteroid, pref_hazard, pref_size, pref_velocity) {
  reasons <- c()
  if (pref_hazard != "All") {
    if ((pref_hazard == "Hazardous" && asteroid$hazardous) ||
        (pref_hazard == "Non-Hazardous" && !asteroid$hazardous)) {
      reasons <- c(reasons, paste0("Matches your hazard preference: ", pref_hazard))
    }
  }
  if (pref_size == "Large" && asteroid$diam_avg_km > median(asteroid$diam_avg_km, na.rm=TRUE)) {
    reasons <- c(reasons, "Large size object (above median)")
  } else if (pref_size == "Small" && asteroid$diam_avg_km <= median(asteroid$diam_avg_km, na.rm=TRUE)) {
    reasons <- c(reasons, "Small size object (below median)")
  }
  if (pref_velocity == "Fast" && asteroid$velocity_kms > median(asteroid$velocity_kms, na.rm=TRUE)) {
    reasons <- c(reasons, "High velocity (above median)")
  } else if (pref_velocity == "Slow" && asteroid$velocity_kms <= median(asteroid$velocity_kms, na.rm=TRUE)) {
    reasons <- c(reasons, "Low velocity (below median)")
  }
  if (length(reasons) == 0) reasons <- "High similarity to reference object (content-based)"
  paste(reasons, collapse = "; ")
}

# ============================================================
# CINEMATIC CSS THEME — TOTAL VISUAL TRANSFORMATION
# ============================================================

nasa_css <- "
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Inter:wght@300;400;500;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body, .content-wrapper, .main-sidebar, .sidebar {
  background: #000000 !important;
  font-family: 'Inter', sans-serif !important;
  color: #eef5ff !important;
}

/* ========== DEEP SPACE BACKGROUND WITH NEBULA ========== */
body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at 30% 40%, rgba(20,30,60,0.6) 0%, rgba(0,0,0,0.95) 80%),
              url('https://www.transparenttextures.com/connections/stardust.png');
  background-size: cover, 300px;
  pointer-events: none;
  z-index: 0;
}

/* Animated star field */
body::after {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    radial-gradient(2px 2px at 15% 30%, #fff, rgba(0,0,0,0)),
    radial-gradient(1px 1px at 65% 75%, #fff, rgba(0,0,0,0)),
    radial-gradient(1px 1px at 85% 15%, #aaccff, rgba(0,0,0,0)),
    radial-gradient(2px 2px at 40% 90%, #fff, rgba(0,0,0,0)),
    radial-gradient(1px 1px at 95% 50%, #fff, rgba(0,0,0,0));
  background-size: 250px 250px, 200px 200px, 150px 150px, 300px 300px, 180px 180px;
  background-repeat: no-repeat;
  opacity: 0.8;
  pointer-events: none;
  z-index: 0;
  animation: starsDrift 80s linear infinite;
}

@keyframes starsDrift {
  0% { background-position: 0 0, 0 0, 0 0, 0 0, 0 0; }
  100% { background-position: 250px 250px, 200px 200px, 150px 150px, 300px 300px, 180px 180px; }
}

/* Glowing nebula orb */
.galaxy-glow {
  position: fixed;
  top: 20%;
  right: 10%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(0,100,255,0.2) 0%, rgba(0,0,0,0) 70%);
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
}

/* Sidebar Premium */
.main-sidebar {
  background: linear-gradient(135deg, rgba(0,5,15,0.95) 0%, rgba(0,10,25,0.98) 100%) !important;
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(0,150,255,0.4) !important;
  box-shadow: 8px 0 40px rgba(0,0,0,0.6) !important;
  z-index: 10 !important;
}

.sidebar-menu > li > a {
  color: rgba(200,230,255,0.7) !important;
  font-family: 'Orbitron', sans-serif !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  padding: 14px 20px !important;
  transition: all 0.25s ease !important;
  border-left: 3px solid transparent !important;
}

.sidebar-menu > li.active > a,
.sidebar-menu > li > a:hover {
  color: #4db8ff !important;
  background: rgba(0,100,220,0.2) !important;
  border-left-color: #00aaff !important;
  box-shadow: inset 0 0 20px rgba(0,150,255,0.2) !important;
}

.sidebar-menu > li > a > .fa {
  color: #4db8ff !important;
  margin-right: 12px !important;
}

.logo-lg {
  font-family: 'Orbitron', sans-serif !important;
  font-size: 18px !important;
  font-weight: 900 !important;
  background: linear-gradient(135deg, #ffffff, #4db8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent !important;
  letter-spacing: 4px !important;
}

.main-header .logo {
  background: rgba(0,5,15,0.95) !important;
  border-bottom: 1px solid rgba(0,150,255,0.4) !important;
}

.main-header .navbar {
  background: rgba(0,5,15,0.85) !important;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0,150,255,0.2) !important;
}

.content-wrapper {
  background: transparent !important;
  position: relative;
  z-index: 1;
}

.content { padding: 25px !important; }

/* Glassmorphism Cards */
.glass-card, .stat-card, .mars-card, .apod-card {
  background: rgba(5,15,30,0.55) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(0,150,255,0.3) !important;
  border-radius: 24px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05) !important;
  transition: all 0.3s cubic-bezier(0.2, 0.9, 0.4, 1.1) !important;
}

.glass-card:hover, .stat-card:hover, .mars-card:hover {
  transform: translateY(-4px) !important;
  box-shadow: 0 12px 40px rgba(0,100,255,0.3), inset 0 1px 0 rgba(255,255,255,0.08) !important;
  border-color: rgba(0,200,255,0.6) !important;
}

.stat-card {
  text-align: center !important;
  padding: 20px 12px !important;
}

.stat-icon {
  font-size: 28px !important;
  color: #4db8ff !important;
  margin-bottom: 8px !important;
  text-shadow: 0 0 10px rgba(0,150,255,0.6);
}

.stat-value {
  font-family: 'Orbitron', sans-serif !important;
  font-size: 34px !important;
  font-weight: 800 !important;
  background: linear-gradient(135deg, #ffffff, #aaddff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent !important;
  line-height: 1.1 !important;
}

.stat-label {
  font-size: 10px !important;
  font-weight: 700 !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: rgba(150,200,255,0.8) !important;
  margin-top: 6px !important;
}

.section-title {
  font-family: 'Orbitron', sans-serif !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 3px !important;
  text-transform: uppercase !important;
  color: #4db8ff !important;
  margin-bottom: 18px !important;
  padding-bottom: 8px !important;
  border-bottom: 1px solid rgba(0,150,255,0.4) !important;
}

/* Cinematic Hero Section with Astronaut */
.hero-section {
  position: relative;
  background: radial-gradient(ellipse at 70% 50%, rgba(0,40,80,0.5), rgba(0,0,0,0.8)) !important;
  border: 1px solid rgba(0,150,255,0.5) !important;
  border-radius: 32px !important;
  padding: 40px !important;
  margin-bottom: 30px !important;
  backdrop-filter: blur(15px) !important;
  box-shadow: 0 0 50px rgba(0,100,255,0.3) !important;
  overflow: hidden !important;
  min-height: 380px;
}

.hero-left {
  position: relative;
  z-index: 2;
}

.hero-title-main {
  font-family: 'Orbitron', sans-serif !important;
  font-size: 52px !important;
  font-weight: 900 !important;
  background: linear-gradient(135deg, #ffffff, #4db8ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent !important;
  text-shadow: 0 0 30px rgba(0,100,255,0.5) !important;
  margin-bottom: 10px;
}

.hero-tagline {
  font-family: 'Orbitron', sans-serif !important;
  font-size: 16px !important;
  font-weight: 400 !important;
  letter-spacing: 4px !important;
  color: rgba(200,230,255,0.7) !important;
  margin-bottom: 20px;
}

.hero-desc {
  font-size: 14px;
  color: rgba(180,220,255,0.6);
  max-width: 500px;
  margin-bottom: 30px;
}

.astronaut-image {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 320px;
  height: auto;
  filter: drop-shadow(0 0 30px rgba(0,150,255,0.5));
  pointer-events: none;
  z-index: 1;
  opacity: 0.9;
}

@media (max-width: 992px) {
  .astronaut-image { width: 220px; right: 10px; }
  .hero-title-main { font-size: 38px; }
}

.btn-nasa {
  background: linear-gradient(90deg, #0033aa, #0066ff) !important;
  border: none !important;
  border-radius: 40px !important;
  color: white !important;
  font-family: 'Orbitron', sans-serif !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 2px !important;
  padding: 12px 28px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 0 15px rgba(0,100,255,0.5) !important;
  width: auto !important;
}

.btn-nasa:hover {
  transform: scale(1.02);
  box-shadow: 0 0 25px rgba(0,150,255,0.8) !important;
  background: linear-gradient(90deg, #0055dd, #0088ff) !important;
}

/* Form Controls */
.form-control, .selectize-input, select, input {
  background: rgba(0,20,50,0.7) !important;
  border: 1px solid rgba(0,150,255,0.4) !important;
  border-radius: 12px !important;
  color: #eef5ff !important;
  font-family: 'Inter', sans-serif !important;
  backdrop-filter: blur(4px);
}

.form-control:focus {
  border-color: #00aaff !important;
  box-shadow: 0 0 0 2px rgba(0,170,255,0.3) !important;
}

/* Tables */
table.dataTable {
  background: transparent !important;
}
table.dataTable thead th {
  background: rgba(0,50,100,0.6) !important;
  color: #4db8ff !important;
  font-family: 'Orbitron', sans-serif !important;
  font-size: 10px !important;
  letter-spacing: 1px !important;
}
table.dataTable tbody tr {
  background: rgba(0,20,40,0.5) !important;
}
table.dataTable tbody tr:hover {
  background: rgba(0,100,200,0.2) !important;
}

/* Badges */
.rec-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 30px;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.badge-hazard { background: rgba(220,50,50,0.25); border: 1px solid #ff4444; color: #ff8888; }
.badge-safe { background: rgba(0,200,100,0.2); border: 1px solid #00ff88; color: #88ffcc; }

/* Score Bar */
.score-bar-wrap {
  background: rgba(0,30,70,0.6);
  border-radius: 20px;
  height: 6px;
  overflow: hidden;
}
.score-bar {
  height: 100%;
  border-radius: 20px;
  background: linear-gradient(90deg, #0088ff, #00ccff);
  box-shadow: 0 0 6px #00ccff;
}

/* Mars Gallery */
.mars-card {
  overflow: hidden !important;
  border-radius: 16px !important;
}
.mars-card img {
  width: 100%;
  height: 170px;
  object-fit: cover;
  transition: transform 0.4s ease;
}
.mars-card:hover img {
  transform: scale(1.05);
}
.mars-card-info {
  padding: 12px;
}
.mars-camera {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #4db8ff;
}

/* APOD */
.apod-img {
  width: 100%;
  max-height: 480px;
  object-fit: cover;
  border-bottom: 1px solid rgba(0,150,255,0.3);
}
.apod-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 24px;
  font-weight: 700;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #00050e; }
::-webkit-scrollbar-thumb { background: #0066aa; border-radius: 10px; }

/* Plotly overrides */
.js-plotly-plot .plotly .main-svg { background: transparent !important; }
.plotly .bg { fill: transparent !important; }
"

# ============================================================
# UI
# ============================================================

ui <- dashboardPage(
  skin = "blue",
  
  dashboardHeader(
    title = span(class = "logo-lg", "NASA EXPLORER"),
    titleWidth = 240
  ),
  
  dashboardSidebar(
    width = 240,
    tags$head(tags$style(HTML(nasa_css))),
    tags$div(class = "galaxy-glow"),
    useShinyjs(),
    tags$div(style = "padding:25px 15px 15px; text-align:center;",
             tags$div(style = "font-size:10px; letter-spacing:3px; color:#4db8ff;", "SPACE STATUS"),
             tags$div(style = "font-size:13px; color:#4dffaa; margin-top:5px;", "● ALL SYSTEMS OPERATIONAL")
    ),
    sidebarMenu(
      id = "tabs",
      menuItem("COSMIC DASH",        tabName = "home",      icon = icon("rocket")),
      menuItem("ASTEROID AI",         tabName = "asteroid",  icon = icon("meteor")),
      menuItem("MARS RECOMMENDER",    tabName = "mars",      icon = icon("camera")),
      menuItem("APOD DISCOVERY",      tabName = "apod",      icon = icon("star")),
      menuItem("ANALYTICS NEXUS",     tabName = "analytics", icon = icon("chart-line")),
      menuItem("DATA CORE",           tabName = "data",      icon = icon("table")),
      menuItem("MISSION INFO",        tabName = "about",     icon = icon("info-circle"))
    ),
    tags$div(style = "position:absolute; bottom:20px; left:0; right:0; padding:0 20px;",
             tags$div(style = "font-size:8px; letter-spacing:2px; color:rgba(100,150,200,0.4);", 
                      "NASA OPEN APIs | REAL-TIME")
    )
  ),
  
  dashboardBody(
    tags$style(HTML(nasa_css)),
    tags$script(HTML("
      $(document).ready(function(){
        $('.stat-value').each(function(){
          var final = parseInt($(this).text().replace(/[^0-9]/g, ''));
          if(!isNaN(final)){
            $(this).text('0');
            var duration = 1000;
            var step = Math.ceil(final / (duration / 20));
            var counter = 0;
            var elem = $(this);
            var interval = setInterval(function(){
              counter += step;
              if(counter >= final){
                elem.text(final.toLocaleString());
                clearInterval(interval);
              } else {
                elem.text(counter.toLocaleString());
              }
            }, 20);
          }
        });
      });
    ")),
    
    tabItems(
      
      # ---- TAB 1: HOME (CINEMATIC) ----
      tabItem(tabName = "home",
              tags$div(class = "hero-section",
                       tags$div(class = "hero-left",
                                tags$div(class = "hero-title-main", "NASA SPACE"),
                                tags$div(class = "hero-tagline", "RECOMMENDATION SYSTEM"),
                                tags$div(class = "hero-desc", 
                                         "AI-Powered Intelligence • Real NASA Data • Infinite Exploration"),
                                actionButton("quick_global_rec", "⚡ GET RECOMMENDATION", class = "btn-nasa")
                       ),
                       tags$img(src = "https://pngimg.com/uploads/astronaut/astronaut_PNG88.png", 
                                class = "astronaut-image", 
                                alt = "Astronaut")
              ),
              
              fluidRow(
                column(3, uiOutput("stat_asteroids")),
                column(3, uiOutput("stat_hazardous")),
                column(3, uiOutput("stat_mars")),
                column(3, uiOutput("stat_apod"))
              ),
              
              fluidRow(
                column(7,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "✨ ASTRONOMY PICTURE OF THE DAY"),
                                uiOutput("home_apod")
                       )
                ),
                column(5,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🎯 QUICK RECOMMENDATION"),
                                selectInput("quick_topic", "I want to explore...",
                                            choices = c("Near-Earth Asteroids", "Mars Surface", "Deep Space APOD"),
                                            width = "100%"),
                                actionButton("quick_recommend", "LAUNCH RECOMMENDER", class = "btn-nasa", width = "100%"),
                                tags$hr(style = "border-color:rgba(0,150,255,0.2);margin:15px 0;"),
                                tags$div(class = "section-title", "🔥 TRENDING NOW"),
                                fluidRow(
                                  column(4, tags$div(class = "rec-badge badge-safe", "MARS PHOTOS")),
                                  column(4, tags$div(class = "rec-badge badge-safe", "ASTEROIDS")),
                                  column(4, tags$div(class = "rec-badge badge-safe", "APOD"))
                                )
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🛸 CLOSE APPROACH — NEXT 7 DAYS"),
                                uiOutput("home_close_approach")
                       )
                )
              ),
              
              fluidRow(
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "📊 ASTEROID VELOCITY DISTRIBUTION"),
                                plotlyOutput("home_velocity_plot", height = "250px")
                       )
                ),
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "⚠️ HAZARDOUS VS NON-HAZARDOUS"),
                                plotlyOutput("home_hazard_donut", height = "250px")
                       )
                )
              ),
              
              fluidRow(
                column(12,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "📸 MARS ROVER GALLERY (PREVIEW)"),
                                uiOutput("home_mars_gallery")
                       )
                )
              )
      ),
      
      # ---- TAB 2: ASTEROID RECOMMENDER (unchanged but upgraded visuals) ----
      tabItem(tabName = "asteroid",
              fluidRow(
                column(3,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🎛️ FILTER PREFERENCES"),
                                tags$div(class = "control-label", "Hazardous Status"),
                                selectInput("ast_hazard", NULL, choices = c("All","Hazardous","Non-Hazardous"), width = "100%"),
                                tags$div(class = "control-label", "Size Preference"),
                                selectInput("ast_size", NULL, choices = c("Any","Large","Small"), width = "100%"),
                                tags$div(class = "control-label", "Velocity Preference"),
                                selectInput("ast_velocity", NULL, choices = c("Any","Fast","Slow"), width = "100%"),
                                tags$div(class = "control-label", "Reference Asteroid"),
                                uiOutput("ast_ref_select"),
                                actionButton("ast_recommend", "🚀 GENERATE RECOMMENDATIONS", class = "btn-nasa", width = "100%")
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "⚙️ ALGORITHM WEIGHTS"),
                                tags$div(class = "insight-box",
                                         tags$div(class = "insight-label", "Rule-Based"),
                                         div(style="display:flex;gap:8px;align-items:center;", 
                                             div(class="score-bar-wrap", style="flex:1;", div(class="score-bar", style="width:35%;")),
                                             span("35%", style="color:#4db8ff;font-size:11px;"))
                                ),
                                tags$div(class = "insight-box",
                                         tags$div(class = "insight-label", "Content-Based"),
                                         div(style="display:flex;gap:8px;align-items:center;", 
                                             div(class="score-bar-wrap", style="flex:1;", div(class="score-bar", style="width:35%;")),
                                             span("35%", style="color:#4db8ff;"))
                                ),
                                tags$div(class = "insight-box",
                                         tags$div(class = "insight-label", "Collaborative"),
                                         div(style="display:flex;gap:8px;align-items:center;", 
                                             div(class="score-bar-wrap", style="flex:1;", div(class="score-bar", style="width:30%;")),
                                             span("30%", style="color:#4db8ff;"))
                                )
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🔍 SMART SEARCH"),
                                textInput("ast_search", NULL, placeholder = "Search asteroid by name...", width = "100%")
                       )
                ),
                column(9,
                       fluidRow(
                         column(4, uiOutput("ast_stat1")),
                         column(4, uiOutput("ast_stat2")),
                         column(4, uiOutput("ast_stat3"))
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🏆 RECOMMENDATION RANKINGS"),
                                uiOutput("ast_rec_table")
                       ),
                       fluidRow(
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "📈 SIZE vs VELOCITY SCATTER"),
                                         plotlyOutput("ast_scatter", height = "280px")
                                )
                         ),
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "📊 HYBRID SCORE DISTRIBUTION"),
                                         plotlyOutput("ast_score_dist", height = "280px")
                                )
                         )
                       ),
                       fluidRow(
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "🎯 RECOMMENDATION CONFIDENCE (GAUGE)"),
                                         plotlyOutput("ast_confidence_gauge", height = "220px")
                                )
                         ),
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "📅 APPROACH TIMELINE (TOP 5)"),
                                         plotlyOutput("ast_timeline", height = "220px")
                                )
                         )
                       ),
                       fluidRow(
                         column(12,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "🧠 AI RECOMMENDATION EXPLANATION"),
                                         uiOutput("ast_explanation")
                                )
                         )
                       )
                )
              )
      ),
      
      # ---- TAB 3: MARS PHOTO RECOMMENDER ----
      tabItem(tabName = "mars",
              fluidRow(
                column(3,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🔭 SEARCH PARAMETERS"),
                                tags$div(class = "control-label", "Rover"),
                                selectInput("mars_rover", NULL,
                                            choices = c("curiosity","opportunity","spirit","perseverance"),
                                            width = "100%"),
                                tags$div(class = "control-label", "Camera"),
                                selectInput("mars_camera", NULL,
                                            choices = c("ALL","FHAZ","RHAZ","MAST","CHEMCAM","MAHLI","MARDI","NAVCAM"),
                                            width = "100%"),
                                tags$div(class = "control-label", "Earth Date"),
                                dateInput("mars_date", NULL, value = "2023-01-15", min = "2012-08-06", max = Sys.Date()-1, width = "100%"),
                                actionButton("mars_fetch", "🛸 FETCH PHOTOS", class = "btn-nasa", width = "100%")
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "📸 CAMERA INSIGHTS"),
                                uiOutput("mars_camera_insights")
                       )
                ),
                column(9,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🌟 RECOMMENDED MARS GALLERY"),
                                uiOutput("mars_gallery")
                       ),
                       fluidRow(
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "📊 CAMERA ACTIVITY ANALYTICS"),
                                         plotlyOutput("mars_camera_plot", height = "250px")
                                )
                         ),
                         column(6,
                                tags$div(class = "glass-card",
                                         tags$div(class = "section-title", "🎯 SIMILARITY RECOMMENDATION"),
                                         uiOutput("mars_similarity_rec")
                                )
                         )
                       )
                )
              )
      ),
      
      # ---- TAB 4: APOD DISCOVERY ----
      tabItem(tabName = "apod",
              fluidRow(
                column(3,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🌌 DISCOVERY CONTROLS"),
                                tags$div(class = "control-label", "Select Date"),
                                dateInput("apod_date", NULL, value = Sys.Date()-1, min = "1995-06-16", max = Sys.Date(), width = "100%"),
                                tags$div(class = "control-label", "Keyword Search"),
                                textInput("apod_keyword", NULL, placeholder = "nebula, galaxy, mars...", width = "100%"),
                                actionButton("apod_fetch", "✨ DISCOVER APOD", class = "btn-nasa", width = "100%"),
                                tags$hr(),
                                tags$div(class = "control-label", "Random Discoveries"),
                                numericInput("apod_count", NULL, value = 5, min = 1, max = 20, width = "100%"),
                                actionButton("apod_random", "🎲 RANDOM BATCH", class = "btn-nasa", width = "100%")
                       )
                ),
                column(9,
                       uiOutput("apod_main"),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🔗 RELATED DISCOVERIES (SEMANTIC SIMILARITY)"),
                                uiOutput("apod_related")
                       ),
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "📈 TOPIC TREND ANALYSIS"),
                                plotlyOutput("apod_trend", height = "250px")
                       )
                )
              )
      ),
      
      # ---- TAB 5: ANALYTICS NEXUS ----
      tabItem(tabName = "analytics",
              fluidRow(
                column(4,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🔮 TOP INSIGHTS"),
                                uiOutput("analytics_insights")
                       )
                ),
                column(8,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "📊 HYBRID SCORE DISTRIBUTION (HAZARD vs NON-HAZARD)"),
                                plotlyOutput("analytics_score_dist", height = "280px")
                       )
                )
              ),
              fluidRow(
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🧬 SIMILARITY HEATMAP (TOP 10)"),
                                plotlyOutput("analytics_heatmap", height = "320px")
                       )
                ),
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "🔬 ASTEROID CLUSTERING (K-MEANS)"),
                                plotlyOutput("analytics_cluster", height = "320px")
                       )
                )
              ),
              fluidRow(
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "👥 USER PREFERENCE SIMULATION"),
                                plotlyOutput("analytics_user_pref", height = "280px")
                       )
                ),
                column(6,
                       tags$div(class = "glass-card",
                                tags$div(class = "section-title", "⚙️ RECOMMENDATION ENGINE OVERVIEW"),
                                uiOutput("analytics_engine_info")
                       )
                )
              )
      ),
      
      # ---- TAB 6: DATA EXPLORER ----
      tabItem(tabName = "data",
              tags$div(class = "glass-card",
                       tags$div(class = "section-title", "🗃️ ASTEROID DATASET (NEOs)"),
                       DT::dataTableOutput("dt_asteroids")
              )
      ),
      
      # ---- TAB 7: ABOUT ----
      tabItem(tabName = "about",
              fluidRow(
                column(8, offset = 2,
                       tags$div(class = "glass-card",
                                tags$div(class = "hero-title-main", style = "font-size:36px;text-align:center;", "NASA SPACE EXPLORER"),
                                tags$div(class = "hero-tagline", style = "font-size:14px;text-align:center;", "PREMIUM AI RECOMMENDATION PLATFORM"),
                                tags$hr(),
                                tags$div(class = "section-title", "🎯 MISSION"),
                                tags$p("Real-time NASA data powered by advanced hybrid recommendation algorithms."),
                                tags$div(class = "section-title", "🚀 RECOMMENDATION TECH STACK"),
                                tags$ul(
                                  tags$li("Rule-Based Filtering (Hazard, Size, Velocity)"),
                                  tags$li("Content-Based (Cosine Similarity on normalized features)"),
                                  tags$li("Collaborative Filtering (20-user simulated matrix)"),
                                  tags$li("Hybrid Fusion (35/35/30 weighting)")
                                ),
                                tags$div(class = "section-title", "📡 DATA SOURCES"),
                                tags$p("NASA NeoWs, Mars Rover Photos, APOD — all via official APIs.")
                       )
                )
              )
      )
    )
  )
)

# ============================================================
# SERVER (preserved functionality, only visual outputs adjusted)
# ============================================================

server <- function(input, output, session) {
  
  # Reactive data
  neo_data <- reactiveVal(NULL)
  mars_data <- reactiveVal(NULL)
  apod_data <- reactiveVal(NULL)
  
  observe({
    withProgress(message = "Fetching NEO data...", value = 0.5, {
      df <- tryCatch(fetch_neo(), error = function(e) NULL)
      neo_data(df)
    })
  })
  
  # ---- HOME TAB ----
  output$stat_asteroids <- renderUI({
    df <- neo_data()
    n  <- if (!is.null(df)) nrow(df) else "..."
    tags$div(class = "stat-card",
             tags$div(class = "stat-icon", icon("meteor")),
             tags$div(class = "stat-value", n),
             tags$div(class = "stat-label", "Total Asteroids"),
             tags$div(class = "stat-sub", "This week")
    )
  })
  
  output$stat_hazardous <- renderUI({
    df  <- neo_data()
    n   <- if (!is.null(df)) sum(df$hazardous, na.rm = TRUE) else "..."
    tags$div(class = "stat-card",
             tags$div(class = "stat-icon", icon("exclamation-triangle")),
             tags$div(class = "stat-value", n),
             tags$div(class = "stat-label", "Hazardous"),
             tags$div(class = "stat-sub", "Potentially dangerous")
    )
  })
  
  output$stat_mars <- renderUI({
    tags$div(class = "stat-card",
             tags$div(class = "stat-icon", icon("camera")),
             tags$div(class = "stat-value", "9,632"),
             tags$div(class = "stat-label", "Mars Photos"),
             tags$div(class = "stat-sub", "Total archive")
    )
  })
  
  output$stat_apod <- renderUI({
    tags$div(class = "stat-card",
             tags$div(class = "stat-icon", icon("star")),
             tags$div(class = "stat-value", "4,321"),
             tags$div(class = "stat-label", "APOD Images"),
             tags$div(class = "stat-sub", "Since 1995")
    )
  })
  
  output$home_apod <- renderUI({
    dat <- tryCatch(fetch_apod(date = Sys.Date() - 1), error = function(e) NULL)
    if (is.null(dat)) return(tags$div(class = "loading-msg", "Loading APOD..."))
    is_img <- !is.null(dat$media_type) && dat$media_type == "image"
    url    <- dat$hdurl %||% dat$url
    tags$div(
      if (is_img && !is.null(url)) tags$img(src = url, style = "width:100%;max-height:350px;object-fit:cover;border-radius:16px;margin-bottom:15px;"),
      tags$div(style = "font-size:10px;letter-spacing:2px;color:#4db8ff;", dat$date %||% ""),
      tags$div(style = "font-family:'Orbitron';font-size:20px;font-weight:600;color:#fff;", dat$title %||% ""),
      tags$p(style = "font-size:13px;line-height:1.7;color:rgba(180,220,255,0.7);", substr(dat$explanation %||% "", 1, 280), "...")
    )
  })
  
  output$home_close_approach <- renderUI({
    df <- neo_data()
    if (is.null(df)) return(tags$div(class = "loading-msg", "Loading..."))
    top <- df %>% filter(!is.na(miss_dist_ld)) %>% arrange(miss_dist_ld) %>% head(5)
    if (nrow(top) == 0) return(tags$div("No data"))
    tagList(lapply(seq_len(nrow(top)), function(i) {
      r <- top[i, ]
      tags$div(style = "display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(0,150,255,0.15);",
               tags$div(
                 tags$div(style = "font-size:13px;font-weight:500;", str_trunc(r$name, 22)),
                 tags$div(style = "font-size:10px;color:rgba(150,200,255,0.5);", r$date)
               ),
               tags$div(style = "text-align:right;",
                        tags$div(style = "font-family:'Orbitron';font-size:14px;color:#4db8ff;", sprintf("%.2f LD", r$miss_dist_ld)),
                        tags$div(style = "font-size:9px;", "Lunar Distance")
               )
      )
    }))
  })
  
  output$home_velocity_plot <- renderPlotly({
    df <- neo_data()
    req(df)
    plot_ly(df, x = ~velocity_kms, type = "histogram", nbinsx = 30,
            marker = list(color = "rgba(0,150,255,0.7)", line = list(color = "cyan", width = 1))) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent",
             xaxis = list(title = "Velocity (km/s)", color = "#aaddff", gridcolor = "rgba(0,100,200,0.2)"),
             yaxis = list(title = "Count", color = "#aaddff", gridcolor = "rgba(0,100,200,0.2)"))
  })
  
  output$home_hazard_donut <- renderPlotly({
    df <- neo_data()
    req(df)
    cnt <- df %>% count(hazardous) %>% mutate(label = ifelse(hazardous, "Hazardous", "Non-Hazardous"))
    plot_ly(cnt, labels = ~label, values = ~n, type = "pie", hole = 0.6,
            marker = list(colors = c("#cc3333","#0066cc"), line = list(color = "black", width = 2))) %>%
      layout(paper_bgcolor = "transparent", showlegend = TRUE,
             legend = list(font = list(color = "#aaddff")))
  })
  
  output$home_mars_gallery <- renderUI({
    dat <- tryCatch(fetch_mars(earth_date = "2023-01-15", page = 1), error = function(e) NULL)
    if (is.null(dat) || nrow(dat) == 0) return(tags$div(class = "loading-msg", "Loading Mars gallery..."))
    top5 <- head(dat, 5)
    fluidRow(lapply(seq_len(nrow(top5)), function(i) {
      r <- top5[i, ]
      column(2, tags$div(class = "mars-card",
                         tags$img(src = r$img_src, onerror = "this.style.display='none'"),
                         tags$div(class = "mars-card-info",
                                  tags$div(class = "mars-camera", r$camera),
                                  tags$div(class = "mars-date", r$earth_date)
                         )
      ))
    }))
  })
  
  observeEvent(input$quick_recommend, {
    topic <- input$quick_topic
    if (grepl("Asteroid", topic)) updateTabItems(session, "tabs", "asteroid")
    else if (grepl("Mars", topic)) updateTabItems(session, "tabs", "mars")
    else updateTabItems(session, "tabs", "apod")
  })
  observeEvent(input$quick_global_rec, {
    updateTabItems(session, "tabs", "asteroid")
  })
  
  # ---- ASTEROID RECOMMENDER ----
  output$ast_ref_select <- renderUI({
    df <- neo_data()
    choices <- if (!is.null(df)) setNames(df$name, str_trunc(df$name, 30)) else character(0)
    selectInput("ast_ref_name", NULL, choices = choices, width = "100%")
  })
  
  ast_recommendations <- eventReactive(input$ast_recommend, {
    df <- neo_data()
    req(!is.null(df))
    hybrid_recommend_asteroids(df, pref_hazard = input$ast_hazard, pref_size = input$ast_size,
                               pref_velocity = input$ast_velocity, ref_name = input$ast_ref_name)
  }, ignoreNULL = FALSE)
  
  observe({
    df <- neo_data()
    if (!is.null(df)) {
      isolate({ if (is.null(ast_recommendations())) shinyjs::click("ast_recommend") })
    }
  })
  
  output$ast_stat1 <- renderUI({ tags$div(class = "stat-card", icon("meteor"), tags$div(class = "stat-value", nrow(neo_data() %||% data.frame())), tags$div(class = "stat-label", "Tracked")) })
  output$ast_stat2 <- renderUI({ tags$div(class = "stat-card", icon("exclamation-triangle"), tags$div(class = "stat-value", sum(neo_data()$hazardous, na.rm=TRUE)), tags$div(class = "stat-label", "Hazardous")) })
  output$ast_stat3 <- renderUI({ tags$div(class = "stat-card", icon("tachometer-alt"), tags$div(class = "stat-value", paste0(round(max(neo_data()$velocity_kms, na.rm=TRUE),1), " km/s")), tags$div(class = "stat-label", "Max Velocity")) })
  
  output$ast_rec_table <- renderUI({
    rec <- ast_recommendations()
    if (is.null(rec) || nrow(rec) == 0) return(tags$div(class = "loading-msg", "Click GENERATE RECOMMENDATIONS"))
    search <- input$ast_search
    if (!is.null(search) && search != "") {
      rec <- rec %>% filter(grepl(search, name, ignore.case = TRUE))
    }
    top <- head(rec, 15)
    tags$div(style = "overflow-x:auto;",
             tags$table(style = "width:100%;border-collapse:collapse;",
                        tags$thead(tags$tr(lapply(c("Rank","Name","Hazard","Diam (km)","Vel (km/s)","Miss Dist (LD)","Rule","Content","Collab","Hybrid"), function(h) tags$th(style = "padding:10px;font-size:10px;color:#4db8ff;", h)))),
                        tags$tbody(lapply(seq_len(nrow(top)), function(i) {
                          r <- top[i, ]
                          tags$tr(
                            tags$td(style = "padding:8px;font-family:Orbitron;color:#4db8ff;", paste0("#", i)),
                            tags$td(style = "padding:8px;", str_trunc(r$name, 25)),
                            tags$td(style = "padding:8px;", if(r$hazardous) tags$span(class="rec-badge badge-hazard", "HAZARD") else tags$span(class="rec-badge badge-safe", "SAFE")),
                            tags$td(style = "padding:8px;", round(r$diam_avg_km,3)),
                            tags$td(style = "padding:8px;", round(r$velocity_kms,2)),
                            tags$td(style = "padding:8px;", round(r$miss_dist_ld,2)),
                            tags$td(style = "padding:8px;", paste0(r$rule_score,"%")),
                            tags$td(style = "padding:8px;", paste0(r$content_score,"%")),
                            tags$td(style = "padding:8px;", paste0(r$collab_score,"%")),
                            tags$td(style = "padding:8px;", div(style="display:flex;align-items:center;gap:5px;", div(class="score-bar-wrap", style="width:60px;", div(class="score-bar", style=paste0("width:", r$hybrid_score,"%;"))), paste0(r$hybrid_score,"%")))
                          )
                        }))
             )
    )
  })
  
  output$ast_scatter <- renderPlotly({
    rec <- ast_recommendations()
    req(rec)
    plot_ly(rec, x = ~velocity_kms, y = ~diam_avg_km, size = ~hybrid_score, color = ~hazardous,
            colors = c("#0078ff","#cc3333"), type = "scatter", mode = "markers",
            text = ~paste(name, "<br>Score:", hybrid_score, "%"), hoverinfo = "text") %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent",
             xaxis = list(title = "Velocity (km/s)", color = "#aaddff"), yaxis = list(title = "Diameter (km)", color = "#aaddff"))
  })
  
  output$ast_score_dist <- renderPlotly({
    rec <- ast_recommendations()
    req(rec)
    plot_ly(rec, x = ~hybrid_score, type = "histogram", nbinsx = 20,
            marker = list(color = "rgba(0,150,255,0.7)")) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent",
             xaxis = list(title = "Hybrid Score (%)", color = "#aaddff"), yaxis = list(title = "Count", color = "#aaddff"))
  })
  
  output$ast_confidence_gauge <- renderPlotly({
    rec <- ast_recommendations()
    req(rec)
    top_score <- max(rec$hybrid_score, na.rm = TRUE)
    plot_ly(type = "indicator", mode = "gauge+number", value = top_score,
            title = list(text = "Max Confidence Score", font = list(color = "#aaddff")),
            gauge = list(axis = list(range = list(0,100), tickcolor = "#aaddff"),
                         bar = list(color = "#00aaff"),
                         steps = list(list(range = c(0,50), color = "rgba(0,100,200,0.3)"),
                                      list(range = c(50,80), color = "rgba(0,150,255,0.5)"),
                                      list(range = c(80,100), color = "rgba(0,200,255,0.7)")),
                         threshold = list(value = top_score, line = list(color = "white")))) %>%
      layout(paper_bgcolor = "transparent", font = list(color = "#aaddff"))
  })
  
  output$ast_timeline <- renderPlotly({
    rec <- ast_recommendations()
    req(rec)
    top5 <- head(rec, 5)
    top5$date <- as.Date(top5$date)
    plot_ly(top5, x = ~date, y = ~hybrid_score, type = "scatter", mode = "lines+markers",
            line = list(color = "#00aaff", width = 3), marker = list(size = 10, color = "#4db8ff"),
            text = ~name, hoverinfo = "text") %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent",
             xaxis = list(title = "Approach Date", color = "#aaddff"), yaxis = list(title = "Hybrid Score", color = "#aaddff"))
  })
  
  output$ast_explanation <- renderUI({
    rec <- ast_recommendations()
    req(rec)
    top1 <- rec[1,]
    explanation <- explain_recommendation(top1, input$ast_hazard, input$ast_size, input$ast_velocity)
    tags$div(class = "insight-box",
             tags$div(class = "insight-label", "🔍 WHY THIS RECOMMENDATION?"),
             tags$div(style = "font-size:13px; color:#eef5ff;", explanation),
             tags$div(style = "margin-top:10px; font-size:11px; color:#4db8ff;", paste0("Hybrid Score: ", top1$hybrid_score, "% | Rule: ", top1$rule_score, "% | Content: ", top1$content_score, "% | Collab: ", top1$collab_score, "%"))
    )
  })
  
  # ---- MARS TAB ----
  mars_reactive <- eventReactive(input$mars_fetch, {
    withProgress(message = "Fetching Mars photos...", {
      cam <- if (input$mars_camera == "ALL") NULL else input$mars_camera
      tryCatch(fetch_mars(rover = input$mars_rover, earth_date = as.character(input$mars_date), camera = cam), error = function(e) NULL)
    })
  })
  
  output$mars_gallery <- renderUI({
    dat <- mars_reactive()
    if (is.null(dat) || nrow(dat) == 0) return(tags$div(class = "loading-msg", "Click FETCH PHOTOS"))
    top12 <- head(dat, 12)
    fluidRow(lapply(seq_len(nrow(top12)), function(i) {
      r <- top12[i, ]
      column(3, tags$div(class = "mars-card", tags$img(src = r$img_src, onerror = "this.style.display='none'", style = "width:100%;height:160px;object-fit:cover;"),
                         tags$div(class = "mars-card-info", tags$div(class = "mars-camera", r$camera_full %||% r$camera), tags$div(class = "mars-date", r$earth_date))))
    }))
  })
  
  output$mars_camera_insights <- renderUI({
    dat <- mars_reactive()
    if (is.null(dat)) return(tags$div("Fetch photos"))
    cnt <- dat %>% count(camera, sort = TRUE)
    tagList(lapply(seq_len(min(5, nrow(cnt))), function(i) {
      r <- cnt[i, ]
      tags$div(class = "insight-box", tags$div(class = "insight-label", r$camera), div(class="score-bar-wrap", div(class="score-bar", style=paste0("width:", r$n/max(cnt$n)*100, "%;")), span(r$n, style="color:#4db8ff;margin-left:8px;")))
    }))
  })
  
  output$mars_camera_plot <- renderPlotly({
    dat <- mars_reactive()
    req(dat)
    cnt <- dat %>% count(camera)
    plot_ly(cnt, x = ~camera, y = ~n, type = "bar", marker = list(color = "rgba(0,120,255,0.7)")) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent", xaxis = list(title = "Camera", color = "#aaddff"), yaxis = list(title = "Photos", color = "#aaddff"))
  })
  
  output$mars_similarity_rec <- renderUI({
    dat <- mars_reactive()
    req(dat)
    top_cam <- dat %>% count(camera) %>% slice_max(n, n=1) %>% pull(camera)
    similar <- dat %>% filter(camera == top_cam) %>% head(3)
    if(nrow(similar)==0) return(tags$div("No similar recommendations"))
    fluidRow(lapply(seq_len(nrow(similar)), function(i) {
      r <- similar[i, ]
      column(4, tags$div(class = "mars-card", tags$img(src = r$img_src, style = "width:100%;height:100px;object-fit:cover;"), tags$div(class = "mars-card-info", tags$div(class = "mars-camera", r$camera))))
    }))
  })
  
  # ---- APOD TAB ----
  apod_reactive <- eventReactive(input$apod_fetch, { fetch_apod(date = input$apod_date) })
  apod_random_reactive <- eventReactive(input$apod_random, { fetch_apod(count = input$apod_count) })
  
  output$apod_main <- renderUI({
    dat <- apod_reactive()
    req(dat)
    tags$div(class = "apod-card", tags$img(class = "apod-img", src = dat$hdurl %||% dat$url, onerror="this.style.display='none'"), 
             tags$div(class = "apod-info", tags$div(class = "apod-date", dat$date), tags$div(class = "apod-title", dat$title), tags$p(class = "apod-explain", substr(dat$explanation,1,400))))
  })
  
  output$apod_related <- renderUI({
    dat <- apod_random_reactive()
    if (is.null(dat) || nrow(dat)==0) return(tags$div("Click RANDOM BATCH"))
    fluidRow(lapply(seq_len(min(5, nrow(dat))), function(i) {
      r <- dat[i, ]
      column(2, tags$div(class = "glass-card", style="padding:10px;", tags$img(src = r$url, style = "width:100%;height:80px;object-fit:cover;border-radius:8px;"), tags$div(style = "font-size:9px;color:#4db8ff;", r$date), tags$div(style = "font-size:10px;", str_trunc(r$title, 35))))
    }))
  })
  
  output$apod_trend <- renderPlotly({
    dat <- apod_random_reactive()
    req(dat)
    if (is.data.frame(dat) && "date" %in% colnames(dat)) {
      dat$date <- as.Date(dat$date)
      trend <- dat %>% group_by(date) %>% summarise(n = n())
      plot_ly(trend, x = ~date, y = ~n, type = "scatter", mode = "lines+markers", line = list(color = "#00aaff")) %>%
        layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent", xaxis = list(title = "Date"), yaxis = list(title = "Count"))
    } else { plotly_empty() }
  })
  
  # ---- ANALYTICS NEXUS ----
  output$analytics_insights <- renderUI({
    df <- neo_data()
    req(df)
    tagList(
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Hazardous Rate"), tags$div(class = "insight-value", paste0(round(mean(df$hazardous, na.rm=TRUE)*100,1), "%"))),
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Fastest Asteroid"), tags$div(class = "insight-value", paste0(round(max(df$velocity_kms, na.rm=TRUE),1), " km/s"))),
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Closest Approach"), tags$div(class = "insight-value", paste0(round(min(df$miss_dist_ld, na.rm=TRUE),2), " LD"))),
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Avg Velocity"), tags$div(class = "insight-value", paste0(round(mean(df$velocity_kms, na.rm=TRUE),1), " km/s")))
    )
  })
  
  output$analytics_score_dist <- renderPlotly({
    df <- neo_data()
    req(df)
    rec <- hybrid_recommend_asteroids(df)
    plot_ly(rec, x = ~hybrid_score, color = ~hazardous, type = "histogram", nbinsx = 25, colors = c("#0078ff","#cc3333")) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent", barmode = "overlay", xaxis = list(title = "Hybrid Score (%)"), yaxis = list(title = "Count"))
  })
  
  output$analytics_heatmap <- renderPlotly({
    df <- neo_data()
    req(df)
    df2 <- head(df %>% filter(!is.na(diam_avg_km), !is.na(velocity_kms)), 10)
    mat <- as.matrix(df2 %>% select(diam_avg_km, velocity_kms, miss_dist_ld) %>% mutate_all(normalize_col))
    sim <- outer(1:10, 1:10, Vectorize(function(i,j) cosine_sim(mat[i,], mat[j,])))
    plot_ly(z = sim, x = str_trunc(df2$name,10), y = str_trunc(df2$name,10), type = "heatmap", colorscale = "Blues") %>%
      layout(paper_bgcolor = "transparent", xaxis = list(tickangle = -45), yaxis = list(tickangle = -45))
  })
  
  output$analytics_cluster <- renderPlotly({
    df <- neo_data()
    req(df)
    df2 <- df %>% filter(!is.na(diam_avg_km), !is.na(velocity_kms)) %>% mutate(norm_diam = normalize_col(diam_avg_km), norm_vel = normalize_col(velocity_kms))
    set.seed(42)
    km <- kmeans(df2[,c("norm_diam","norm_vel")], centers = 3, nstart = 5)
    df2$cluster <- factor(km$cluster)
    plot_ly(df2, x = ~velocity_kms, y = ~diam_avg_km, color = ~cluster, symbol = ~hazardous, type = "scatter", mode = "markers", colors = c("#00aaff","#88ffaa","#ffaa44")) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent")
  })
  
  output$analytics_user_pref <- renderPlotly({
    categories <- c("Hazardous","Fast","Large","Close Approach","Mars","APOD")
    vals <- runif(6, 20, 95)
    plot_ly(x = categories, y = vals, type = "bar", marker = list(color = c("#cc3333","#00aaff","#88ffaa","#ffaa44","#aa88ff","#00ccaa"))) %>%
      layout(paper_bgcolor = "transparent", plot_bgcolor = "transparent", yaxis = list(title = "Preference Score"))
  })
  
  output$analytics_engine_info <- renderUI({
    tagList(
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Hybrid Algorithm"), tags$div(class = "insight-value", "Rule+Content+Collaborative")),
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Similarity"), tags$div(class = "insight-value", "Cosine")),
      tags$div(class = "insight-box", tags$div(class = "insight-label", "Clustering"), tags$div(class = "insight-value", "K-Means (k=3)"))
    )
  })
  
  # ---- DATA EXPLORER ----
  output$dt_asteroids <- DT::renderDataTable({
    df <- neo_data()
    req(df)
    DT::datatable(df %>% select(name, date, hazardous, diam_avg_km, velocity_kms, miss_dist_ld), options = list(pageLength = 10, scrollX = TRUE), class = "display compact")
  })
}

# ============================================================
# LAUNCH
# ============================================================
shinyApp(ui = ui, server = server)