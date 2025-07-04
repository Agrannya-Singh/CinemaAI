import gradio as gr
import requests
import html
import re
import json # Added for robust error parsing
from typing import List, Dict, Any, Optional

# Configuration (These could be moved to a central config.py later)
# API_BASE_URL = "http://127.0.0.1:5000" # This will be defined in run.py or config.py
# MAX_SELECTIONS = 10
# MIN_RECOMMENDATIONS = 5 # Renamed from MIN_SELECTIONS_FOR_REC

# --- Gradio Application ---

class CinemaCloneAppGradio: # Renamed to avoid conflict if another CinemaCloneApp exists
    def __init__(self, api_base_url: str, max_selections: int, min_recommendations: int):
        self.api_base_url = api_base_url
        self.max_selections = max_selections
        self.min_recommendations = min_recommendations # Min selections needed for recommendations

        self.selected_movie_ids: List[str] = [] # Store IDs directly
        self.all_movies_cache: List[Dict[str, Any]] = [] # Cache for movies to avoid re-fetching constantly
        # self.recommendations_cache: List[Dict[str, Any]] = [] # If needed

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent XSS attacks and clean up."""
        if not isinstance(text, str):
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]*>', '', text)
        # Escape special HTML characters
        text = html.escape(text)
        return text.strip()

    def validate_movie_data(self, movie: Dict[str, Any]) -> bool:
        """Validate essential movie data structure."""
        if not isinstance(movie, dict):
            return False
        required_fields = ['id', 'title'] # 'poster_path' is good but might be missing
        return all(field in movie and movie[field] is not None for field in required_fields)

    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Helper function for making API requests."""
        url = f"{self.api_base_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=(10, 60), **kwargs) # connect, read timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                print(f"Warning: Received non-JSON response from {url} (status {response.status_code}). Content: {response.text[:200]}...")
                # Try to parse as JSON anyway, or handle as error
                try:
                    return response.json() # Or return an error structure
                except json.JSONDecodeError:
                    raise ValueError(f"API returned non-JSON response and failed to parse. Status: {response.status_code}, URL: {url}")

            return response.json()
        except requests.exceptions.Timeout:
            print(f"Timeout error: {method.upper()} request to {url}")
        except requests.exceptions.ConnectionError:
            print(f"Connection error: Could not connect to API at {url}. Ensure the backend is running.")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e.response.status_code} for {url}. Response: {e.response.text[:200]}")
        except ValueError as e: # For JSON parsing or content type issues
            print(f"Value error (e.g. JSON decoding): {e} for {url}")
        except Exception as e:
            print(f"An unexpected error occurred with API request to {url}: {e}")
        return None


    def fetch_movies_from_backend(self) -> List[Dict[str, Any]]:
        """Fetch all movies from the Flask backend."""
        print("UI: Fetching movies from backend...")
        movies_response = self._make_api_request("GET", "/api/movies", headers={'Accept': 'application/json'})

        if movies_response is not None and isinstance(movies_response, list):
            validated_movies = []
            for movie in movies_response:
                if self.validate_movie_data(movie):
                    # Sanitize fields that will be displayed in HTML
                    movie['title'] = self.sanitize_input(str(movie.get('title', '')))
                    movie['overview'] = self.sanitize_input(str(movie.get('overview', '')))
                    movie['genres'] = self.sanitize_input(str(movie.get('genres', '')))
                    movie['cast'] = self.sanitize_input(str(movie.get('cast', '')))
                    movie['id'] = str(movie.get('id')) # Ensure ID is a string
                    validated_movies.append(movie)
                else:
                    print(f"Warning: Invalid movie data received and skipped: {str(movie)[:100]}")

            self.all_movies_cache = validated_movies
            print(f"UI: Successfully fetched and validated {len(validated_movies)} movies.")
            return validated_movies
        else:
            print("UI: Failed to fetch movies or response was not a list. Using empty list.")
            self.all_movies_cache = [] # Clear cache on failure
            return []


    def get_recommendations_from_backend(self, selected_ids: List[str]) -> List[Dict[str, Any]]:
        """Get recommendations from Flask backend."""
        if not selected_ids:
            print("UI: No movie IDs provided for recommendations.")
            return []

        print(f"UI: Getting recommendations for IDs: {selected_ids}")
        # Ensure IDs are strings, as expected by API (though API also stringifies)
        sanitized_ids = [str(id_val) for id_val in selected_ids]

        recommendations_response = self._make_api_request(
            "POST", "/api/recommend",
            json={"selected_movies": sanitized_ids},
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )

        if recommendations_response is not None and isinstance(recommendations_response, list):
            validated_recs = []
            for rec in recommendations_response:
                if self.validate_movie_data(rec):
                    rec['title'] = self.sanitize_input(str(rec.get('title', '')))
                    rec['overview'] = self.sanitize_input(str(rec.get('overview', '')))
                    rec['genres'] = self.sanitize_input(str(rec.get('genres', '')))
                    rec['cast'] = self.sanitize_input(str(rec.get('cast', '')))
                    rec['id'] = str(rec.get('id'))
                    validated_recs.append(rec)
                else:
                    print(f"Warning: Invalid recommendation data received: {str(rec)[:100]}")
            print(f"UI: Successfully received and validated {len(validated_recs)} recommendations.")
            return validated_recs
        else:
            # Handle specific error messages from backend if possible
            if recommendations_response and isinstance(recommendations_response, dict) and 'error' in recommendations_response:
                 print(f"UI: API error getting recommendations: {recommendations_response['error']}")
            else:
                print("UI: Failed to get recommendations or unexpected format. Returning empty list.")
            return []

    def create_movie_card_html(self, movie: Dict[str, Any], is_selected: bool = False, is_recommendation: bool = False) -> str:
        """Create HTML for a movie card."""
        # Ensure all fields are present with default empty strings to avoid None or KeyError
        title = html.escape(str(movie.get('title', 'Unknown Title')))
        overview_raw = str(movie.get('overview', 'No overview available.'))
        overview = html.escape(overview_raw[:150] + "..." if len(overview_raw) > 150 else overview_raw)
        genres_raw = str(movie.get('genres', 'N/A'))
        genres = html.escape(genres_raw)
        cast_raw = str(movie.get('cast', 'N/A'))
        cast = html.escape(cast_raw[:100] + "..." if len(cast_raw) > 100 else cast_raw)

        try:
            rating = float(movie.get('vote_average', 0.0))
        except (ValueError, TypeError):
            rating = 0.0

        year = html.escape(str(movie.get('release_date', 'N/A')))
        movie_id = html.escape(str(movie.get('id', ''))) # Ensure ID is also sanitized and present

        poster_url = movie.get('poster_path', '')
        if not poster_url or not isinstance(poster_url, str) or not poster_url.startswith(('http://', 'https://')):
            poster_url = 'https://via.placeholder.com/300x450/1a1a1a/fff?text=No+Image'
        else:
            poster_url = html.escape(poster_url)


        selected_class = "selected" if is_selected else ""
        rec_class = "recommendation" if is_recommendation else ""
        selection_indicator_symbol = "✓" if is_selected else "＋" # Using a different plus

        genre_list = [g.strip() for g in genres_raw.split(',') if g.strip()] if genres_raw != 'N/A' else []
        genre_tags_html = "".join(f'<span class="genre-tag">{html.escape(genre)}</span>' for genre in genre_list[:3])

        # IMPORTANT: The onclick function name `selectMovieById_gradio` should match the one in CSS_JS_CRIPT
        # It now passes the movie_id directly.
        return f"""
        <div class="movie-card {selected_class} {rec_class}" data-movie-id="{movie_id}" onclick="handleMovieCardClick_gradio('{movie_id}')">
            <div class="movie-poster-container">
                <img src="{poster_url}" alt="{title} Poster" class="movie-poster" onerror="this.src='https://via.placeholder.com/300x450/1a1a1a/fff?text=Image+Error'">
                <div class="movie-overlay"></div>
                <div class="selection-indicator">{selection_indicator_symbol}</div>
            </div>
            <div class="movie-info">
                <h3 class="movie-title">{title}</h3>
                <div class="movie-meta">
                    <div class="movie-rating">
                        <span class="star">⭐</span>
                        <span class="rating-value">{rating:.1f}</span>
                    </div>
                    <span class="movie-year">{year}</span>
                </div>
                <div class="genre-tags">{genre_tags_html if genre_tags_html else '<span class="genre-tag">N/A</span>'}</div>
                <p class="movie-cast"><strong>Cast:</strong> {cast}</p>
                <p class="movie-overview">{overview}</p>
            </div>
        </div>
        """

    def create_movies_grid_html(self, movies_list: List[Dict[str, Any]], is_recommendation: bool = False) -> str:
        """Create HTML grid of movie cards."""
        if not movies_list:
            message_type = 'recommendations' if is_recommendation else 'movies'
            action_text = 'Select more movies to discover new gems!' if is_recommendation else 'Try loading movies or check your connection.'
            return f"""
            <div class="no-movies">
                <div class="no-movies-icon">🎬</div>
                <h3>No {message_type} found</h3>
                <p>{action_text}</p>
            </div>
            """

        cards_html = []
        for movie_data in movies_list[:100]: # Limit display for performance
            if not self.validate_movie_data(movie_data): # Ensure movie data is valid before creating card
                print(f"Skipping invalid movie data for card: {str(movie_data)[:50]}")
                continue
            # Check selection status using the movie's ID against self.selected_movie_ids
            is_selected = movie_data.get('id') in self.selected_movie_ids
            cards_html.append(self.create_movie_card_html(movie_data, is_selected, is_recommendation))

        grid_class = "recommendations-grid" if is_recommendation else "movies-grid"
        return f'<div class="{grid_class}">{"".join(cards_html)}</div>'

# --- Gradio UI Functions (Callbacks) ---
# These functions will interact with an instance of CinemaCloneAppGradio

# This instance will be created in run.py and passed to Gradio setup
# For now, define placeholder functions or assume an instance `gradio_app_instance` is available globally in this module
# For cleaner separation, these functions should take `gradio_app_instance` as an argument if possible,
# or Gradio's state management should be used. For simplicity, we'll assume it's created and accessible.

# Placeholder for the app instance. This will be properly initialized in run.py.
# gradio_app_instance: Optional[CinemaCloneAppGradio] = None

# CSS and JavaScript (Combined for simplicity, can be split)
# Note: The JavaScript function `handleMovieCardClick_gradio` now needs to interact with Gradio components
# by finding the hidden input and button for selection.
CSS_JS_SCRIPT = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    .gradio-container {
        background: linear-gradient(135deg, #0B0F19 0%, #1A1D24 50%, #0F121C 100%);
        color: #EAEAEA;
        font-family: 'Inter', sans-serif;
        min-height: 100vh;
    }
    .app-header { text-align: center; padding: 40px 20px; }
    .app-title {
        font-size: clamp(2.8rem, 6vw, 4.5rem); font-weight: 900; letter-spacing: -3px;
        background: linear-gradient(135deg, #E50914 0%, #FF6B6B 50%, #B45AF8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        text-shadow: 0 0 40px rgba(229, 9, 20, 0.35); margin-bottom: 10px;
    }
    .app-subtitle { font-size: clamp(1rem, 2.5vw, 1.3rem); opacity: 0.85; font-weight: 400; color: #B0B8C4;}

    .controls-container { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; align-items: center; padding: 20px; margin-bottom: 20px; background: rgba(26, 29, 36, 0.7); border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.3); backdrop-filter: blur(10px); }
    .status-display-html { padding: 15px; border-radius: 10px; text-align: center; font-weight: 500; margin: 15px auto; max-width: 90%; }
    .status-display-html.success { background: rgba(76, 175, 80, 0.2); color: #6fcf97; border: 1px solid rgba(76, 175, 80, 0.4); }
    .status-display-html.error { background: rgba(229, 9, 20, 0.15); color: #ff6b6b; border: 1px solid rgba(229, 9, 20, 0.3); }
    .status-display-html.info { background: rgba(47, 128, 237, 0.15); color: #5D9CEC; border: 1px solid rgba(47, 128, 237, 0.3); }

    .selection-counter-html { /* Style for HTML component showing selection count */
        background: linear-gradient(135deg, #3A3F4B, #2C2F37); padding: 15px 25px; border-radius: 30px; text-align: center; font-weight: 600; margin: 20px auto; max-width: 350px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); font-size: 1.05rem;
    }

    .movies-grid, .recommendations-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; padding: 25px;
        max-height: 70vh; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #E50914 #1A1D24;
        border-radius: 15px; background: rgba(11, 15, 25, 0.3);
    }
    .movies-grid::-webkit-scrollbar, .recommendations-grid::-webkit-scrollbar { width: 8px; }
    .movies-grid::-webkit-scrollbar-track, .recommendations-grid::-webkit-scrollbar-track { background: #1A1D24; border-radius: 4px; }
    .movies-grid::-webkit-scrollbar-thumb, .recommendations-grid::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #E50914, #B45AF8); border-radius: 4px; }

    .movie-card {
        position: relative; border-radius: 18px; overflow: hidden; background: linear-gradient(145deg, #20242C, #2D323C);
        box-shadow: 0 12px 35px rgba(0,0,0,0.4); transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1); cursor: pointer;
        border: 2px solid transparent; backdrop-filter: blur(8px);
    }
    .movie-card:hover { transform: translateY(-12px) scale(1.03); box-shadow: 0 20px 45px rgba(229,9,20,0.3); border-color: rgba(229,9,20,0.4); }
    .movie-card.selected { border-color: #E50914; box-shadow: 0 0 25px rgba(229,9,20,0.5); transform: scale(1.02); }
    .movie-card.recommendation { background: linear-gradient(145deg, #2A1A2A, #3A2A3A); border-color: rgba(180,90,248,0.4); }
    .movie-card.recommendation:hover { box-shadow: 0 20px 45px rgba(180,90,248,0.3); border-color: #B45AF8; }

    .movie-poster-container { position: relative; width: 100%; height: 380px; overflow: hidden; }
    .movie-poster { width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s ease-in-out; }
    .movie-card:hover .movie-poster { transform: scale(1.08); }
    .movie-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(11,15,25,0.85) 0%, transparent 60%); }
    .selection-indicator {
        position: absolute; top: 12px; right: 12px; width: 32px; height: 32px; border-radius: 50%;
        background: rgba(229,9,20,0.85); display: flex; align-items: center; justify-content: center;
        color: white; font-weight: bold; font-size: 17px; backdrop-filter: blur(8px);
        border: 1.5px solid rgba(255,255,255,0.15); transition: all 0.3s ease;
    }
    .movie-card.selected .selection-indicator { background: linear-gradient(135deg, #E50914, #FF3B3B); transform: scale(1.05); }

    .movie-info { padding: 20px; background: linear-gradient(to top, #14171F, #1A1D27); }
    .movie-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 10px; color: #F0F0F0; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.6em; }
    .movie-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .movie-rating { display: flex; align-items: center; gap: 6px; font-weight: 600; }
    .star { font-size: 1.1rem; color: #FFD700; } .rating-value { color: #FFD700; font-size: 0.95rem; }
    .movie-year { color: #A0A8B4; font-size: 0.85rem; font-weight: 500; background: rgba(255,255,255,0.07); padding: 3px 10px; border-radius: 15px; }
    .genre-tags { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 12px; min-height: 26px; }
    .genre-tag {
        background: linear-gradient(135deg, #E50914, #FF6B6B); padding: 3px 10px; border-radius: 15px;
        font-size: 0.7rem; font-weight: 600; color: white; border: 1px solid rgba(255,255,255,0.1);
    }
    .movie-card.recommendation .genre-tag { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }
    .movie-cast, .movie-overview { color: #B0B8C4; font-size: 0.8rem; line-height: 1.5; margin-bottom: 8px; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
    .movie-cast { -webkit-line-clamp: 2; } .movie-overview { -webkit-line-clamp: 3; }
    .movie-cast strong { color: #E50914; font-weight: 600; }

    .no-movies { text-align: center; color: #A0A8B4; padding: 60px 30px; background: rgba(26,29,36,0.5); border-radius: 18px; margin: 30px; border: 2px dashed rgba(255,255,255,0.1); }
    .no-movies-icon { font-size: 3.5rem; margin-bottom: 18px; opacity: 0.6; }
    .no-movies h3 { font-size: 1.4rem; margin-bottom: 8px; color: #EAEAEA; } .no-movies p { font-size: 0.95rem; opacity: 0.75; }

    .recommendations-section { margin-top: 50px; padding: 30px; background: linear-gradient(135deg, rgba(139,92,246,0.08), rgba(229,9,20,0.08)); border-radius: 25px; border: 1px solid rgba(139,92,246,0.15); backdrop-filter: blur(15px); }
    .section-title { font-size: 2.2rem; font-weight: 800; margin-bottom: 25px; background: linear-gradient(135deg, #B45AF8, #E50914); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-align: center; }

    /* Gradio Button Styling */
    .gr-button { /* Default Gradio button style override */
        background: linear-gradient(135deg, #E50914, #FF6B6B) !important;
        border: none !important; color: white !important; font-weight: 600 !important;
        border-radius: 25px !important; padding: 12px 25px !important; transition: all 0.3s ease !important;
        box-shadow: 0 8px 20px rgba(229,9,20,0.25) !important;
    }
    .gr-button:hover { transform: translateY(-2px) !important; box-shadow: 0 12px 30px rgba(229,9,20,0.4) !important; background: linear-gradient(135deg, #FF1A25, #FF7B7B) !important; }
    button.secondary { /* For secondary actions like clear or add/remove */
         background: linear-gradient(135deg, #4A505B, #3C3F47) !important;
         box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
    }
    button.secondary:hover {
        background: linear-gradient(135deg, #5A606B, #4C4F57) !important;
        box-shadow: 0 12px 30px rgba(0,0,0,0.3) !important;
    }

    /* Ensure dropdowns and textboxes are visible */
    .gr-dropdown, .gr-textbox, .gr-checkboxgroup .gr-input-label, .gr-radio .gr-input-label {
      background-color: rgba(40, 40, 50, 0.8) !important;
      color: #EAEAEA !important;
      border: 1px solid rgba(255, 255, 255, 0.2) !important;
      border-radius: 8px !important;
    }
    .gr-input-label, .gr-slider + label { color: #C0C8D4 !important; font-weight: 500 !important; }


    /* Hidden elements for JS interaction */
    .hidden-gradio-input { display: none !important; }
    .hidden-gradio-button { display: none !important; }

</style>
<script>
function handleMovieCardClick_gradio(movieId) {
    console.log("Card clicked for movie ID:", movieId);
    // 1. Find the hidden Textbox for movie ID
    const hiddenMovieIdTextbox = document.getElementById('hidden_movie_id_input');
    // 2. Find the hidden Button that triggers the Gradio Python function
    const hiddenSelectButton = document.getElementById('hidden_select_trigger_button');

    if (hiddenMovieIdTextbox && hiddenSelectButton) {
        // Set the value of the hidden textbox
        // Gradio's JS might not pick up direct .value change for textboxes,
        // so we may need to dispatch an input event.
        hiddenMovieIdTextbox.value = movieId;
        const event = new Event('input', { bubbles: true });
        hiddenMovieIdTextbox.dispatchEvent(event);

        // Click the hidden button
        hiddenSelectButton.click();
        console.log("Set hidden_movie_id_input to:", movieId, "and clicked hidden_select_trigger_button");
    } else {
        if (!hiddenMovieIdTextbox) console.error("Could not find the hidden_movie_id_input element.");
        if (!hiddenSelectButton) console.error("Could not find the hidden_select_trigger_button element.");
    }
}

// Optional: Function to scroll to recommendations when they appear
function scrollToRecommendations_gradio() {
    const recSection = document.querySelector('.recommendations-section');
    if (recSection) {
        recSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Call this after recommendations are rendered if you want auto-scroll
// Example: In your get_recommendations Python, if it returns HTML, and also a JS call.
// Or, use a MutationObserver in JS to watch for the recommendations_display div to become visible/populated.
</script>
"""

# Gradio Interface building function
def create_gradio_interface(app_instance: CinemaCloneAppGradio):
    with gr.Blocks(css=CSS_JS_SCRIPT, title="CinemaAI - Movie Recommendations", theme=gr.themes.Base(primary_hue=gr.themes.colors.red, secondary_hue=gr.themes.colors.purple, neutral_hue=gr.themes.colors.slate)) as demo:
        gr.HTML(f"""
        <header class="app-header">
            <h1 class="app-title">🎬 CINEMA AI</h1>
            <p class="app-subtitle">Discover Your Next Cinematic Adventure. Select your favorites & let AI curate recommendations!</p>
        </header>
        """)

        # Hidden components for JavaScript interaction
        with gr.Row(visible=False): # Keep this row itself visible but components inside are logically hidden by CSS or direct visible=False
            hidden_movie_id_input = gr.Textbox(label="Hidden Movie ID", elem_id="hidden_movie_id_input")
            hidden_select_trigger_button = gr.Button("Hidden Select Trigger", elem_id="hidden_select_trigger_button")

        status_display = gr.HTML("<div class='status-display-html info'>✨ Click 'Load Movie Collection' to begin your journey!</div>", elem_id="status_display")
        selection_counter_display = gr.HTML(f"<div class='selection-counter-html'>Selected: 0 / {app_instance.max_selections}</div>", elem_id="selection_counter_display")

        with gr.Row(elem_classes="controls-container"):
            load_btn = gr.Button("🎬 Load Movie Collection", variant="primary", scale=1)
            clear_btn = gr.Button("🔄 Clear Selections", variant="secondary", scale=1)
            search_bar = gr.Textbox(label="🔍 Search Movies", placeholder="Type to search by title...", interactive=True, scale=2)

        movies_display = gr.HTML("<div class='no-movies'><div class='no-movies-icon'>🎞️</div><h3>Your Movie Universe Awaits</h3><p>Load movies to start exploring.</p></div>", elem_id="movies_display")

        rec_btn = gr.Button("🎯 Get My Personal Recommendations!", variant="primary", visible=False, size="lg", elem_id="get_recommendations_button")
        recommendations_display = gr.HTML("", visible=False, elem_id="recommendations_display_html")

        # --- Event Handlers ---
        def handle_load_movies():
            movies = app_instance.fetch_movies_from_backend()
            if not movies:
                movies_html = app_instance.create_movies_grid_html([], is_recommendation=False)
                status_html = "<div class='status-display-html error'>❌ Failed to load movies. Backend might be down or no movies available.</div>"
                app_instance.selected_movie_ids.clear() # Clear selections
            else:
                movies_html = app_instance.create_movies_grid_html(movies, is_recommendation=False)
                status_html = f"<div class='status-display-html success'>✨ Loaded {len(movies)} movies! Start selecting your favorites.</div>"
                app_instance.selected_movie_ids.clear() # Clear selections on new load

            selection_count_html = f"<div class='selection-counter-html'>Selected: {len(app_instance.selected_movie_ids)} / {app_instance.max_selections}</div>"
            return movies_html, status_html, gr.update(visible=False), "", selection_count_html # Clear search, hide recs

        load_btn.click(
            fn=handle_load_movies,
            outputs=[movies_display, status_display, recommendations_display, search_bar, selection_counter_display]
        )

        def handle_toggle_movie_selection(clicked_movie_id: str):
            if not clicked_movie_id or not clicked_movie_id.strip():
                # This case should ideally not happen if JS is working, but good to have a fallback
                status_html = "<div class='status-display-html error'>⚠️ Invalid movie ID clicked.</div>"
                # No change to movies_html, rec_btn_visibility, selection_counter_html
                return gr.update(), status_html, gr.update(), gr.update()


            movie_id_str = str(clicked_movie_id).strip()
            movie_title = "this movie" # Default title
            # Try to find movie title for better message
            found_movie = next((m['title'] for m in app_instance.all_movies_cache if m.get('id') == movie_id_str), None)
            if found_movie: movie_title = f"'{found_movie}'"


            action_taken = ""
            if movie_id_str in app_instance.selected_movie_ids:
                app_instance.selected_movie_ids.remove(movie_id_str)
                status_html = f"<div class='status-display-html info'>➖ {movie_title} removed from your selections.</div>"
                action_taken = "removed"
            else:
                if len(app_instance.selected_movie_ids) >= app_instance.max_selections:
                    status_html = f"<div class='status-display-html error'>🚫 Max {app_instance.max_selections} movies can be selected.</div>"
                else:
                    app_instance.selected_movie_ids.append(movie_id_str)
                    status_html = f"<div class='status-display-html success'>➕ {movie_title} added to your selections!</div>"
                    action_taken = "added"

            # Re-render the movies grid to update visual selection status
            current_search_query = "" # We need to get this from the search_bar's current state if we want to preserve search
                                      # For now, re-rendering all movies. A more advanced setup would pass search_bar value.

            # Filter movies if search query exists (this part needs access to search_bar value, tricky with current Gradio flow for hidden button)
            # For now, we refresh based on all_movies_cache.
            # A more robust way: the JS could also pass the current search term to another hidden input.
            movies_to_display = app_instance.all_movies_cache
            # This is a simplification: if search is active, it should re-filter based on search
            # For now, clicking a card will refresh the view with all movies (or current search if search_bar.change is smart)

            movies_html_output = app_instance.create_movies_grid_html(movies_to_display, is_recommendation=False)

            selection_count_html = f"<div class='selection-counter-html'>Selected: {len(app_instance.selected_movie_ids)} / {app_instance.max_selections}</div>"
            rec_btn_visibility = len(app_instance.selected_movie_ids) >= app_instance.min_recommendations

            return movies_html_output, status_html, gr.update(visible=rec_btn_visibility), selection_count_html

        # This is the Python function triggered by the hidden button
        hidden_select_trigger_button.click(
            fn=handle_toggle_movie_selection,
            inputs=[hidden_movie_id_input], # Input from the hidden textbox
            outputs=[movies_display, status_display, rec_btn, selection_counter_display]
        )

        def handle_get_recommendations():
            if len(app_instance.selected_movie_ids) < app_instance.min_recommendations:
                status_html = f"<div class='status-display-html error'>🎯 Select at least {app_instance.min_recommendations} movies for recommendations.</div>"
                return gr.update(visible=False), status_html # Keep recommendations hidden

            recommendations = app_instance.get_recommendations_from_backend(app_instance.selected_movie_ids)
            if not recommendations:
                rec_html_output = "<div class='no-movies'><div class='no-movies-icon'>🤔</div><h3>No recommendations found</h3><p>Try selecting a different set of movies or more diverse ones!</p></div>"
                status_html = "<div class='status-display-html info'>🤔 No recommendations found. Try different movies!</div>"
            else:
                rec_html_output = f"""
                <section class="recommendations-section">
                    <h2 class="section-title">✨ Curated For You ✨</h2>
                    {app_instance.create_movies_grid_html(recommendations, is_recommendation=True)}
                </section>
                """
                status_html = f"<div class='status-display-html success'>🌟 Found {len(recommendations)} recommendations based on your {len(app_instance.selected_movie_ids)} selections! Scroll down to see them.</div>"
                # Add a script call to scroll if desired and available
                # rec_html_output += "<script>scrollToRecommendations_gradio();</script>"


            return gr.update(value=rec_html_output, visible=True), status_html

        rec_btn.click(
            fn=handle_get_recommendations,
            outputs=[recommendations_display, status_display]
        )

        def handle_clear_selections():
            app_instance.selected_movie_ids.clear()
            movies_html_output = app_instance.create_movies_grid_html(app_instance.all_movies_cache, is_recommendation=False) # Re-render full grid
            status_html = "<div class='status-display-html info'>🔄 Selections cleared! Ready for a new cinematic journey.</div>"
            selection_count_html = f"<div class='selection-counter-html'>Selected: 0 / {app_instance.max_selections}</div>"
            # Clear search bar, hide recommendations and rec button
            return movies_html_output, status_html, gr.update(visible=False), gr.update(visible=False), "", selection_count_html

        clear_btn.click(
            fn=handle_clear_selections,
            outputs=[movies_display, status_display, rec_btn, recommendations_display, search_bar, selection_counter_display]
        )

        def handle_search_movies(query: str):
            query_sanitized = app_instance.sanitize_input(query).lower()
            if not query_sanitized:
                # If search is cleared, show all movies from cache
                movies_html_output = app_instance.create_movies_grid_html(app_instance.all_movies_cache, is_recommendation=False)
            else:
                filtered_movies = [
                    movie for movie in app_instance.all_movies_cache
                    if query_sanitized in str(movie.get('title', '')).lower() or \
                       query_sanitized in str(movie.get('genres', '')).lower() or \
                       query_sanitized in str(movie.get('cast', '')).lower()
                ]
                movies_html_output = app_instance.create_movies_grid_html(filtered_movies, is_recommendation=False)
            return movies_html_output

        search_bar.change( # Using change for dynamic search as user types
            fn=handle_search_movies,
            inputs=[search_bar],
            outputs=[movies_display]
        )
    return demo

if __name__ == '__main__':
    # This is for testing the Gradio UI independently (requires a running API backend)
    print("Running Gradio UI directly for testing...")
    # Ensure the API (Flask app) is running on http://127.0.0.1:5000 separately

    # --- Configuration for standalone UI test ---
    TEST_API_BASE_URL = "http://127.0.0.1:5000" # Make sure Flask API is running here
    TEST_MAX_SELECTIONS = 10
    TEST_MIN_RECOMMENDATIONS = 3 # Adjusted for testing, original was 5

    # Create an instance of the app logic class
    # This replaces the global `gradio_app_instance` for the scope of this test
    test_app_instance = CinemaCloneAppGradio(
        api_base_url=TEST_API_BASE_URL,
        max_selections=TEST_MAX_SELECTIONS,
        min_recommendations=TEST_MIN_RECOMMENDATIONS
    )

    # Create the Gradio interface using the test instance
    gradio_interface = create_gradio_interface(test_app_instance)

    print(f"Attempting to launch Gradio. Ensure Flask API is running at {TEST_API_BASE_URL}")
    gradio_interface.launch(server_name="0.0.0.0", server_port=7860) # Use a different port than Flask
    # Note: If Flask is not running, fetching movies will fail.
    # This __main__ block is primarily for UI layout testing.
    # Full functionality testing is better done via the main run.py.
