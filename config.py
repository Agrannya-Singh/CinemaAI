# Configuration settings for CinemaAI application

# API Configuration
API_BASE_URL = "http://127.0.0.1:5000"  # Base URL for the Flask backend API

# Gradio UI Configuration
MAX_SELECTIONS = 10  # Maximum number of movies a user can select for recommendations
MIN_SELECTIONS_FOR_RECOMMENDATIONS = 3 # Minimum movies to select before recommendations can be generated (was 5) - adjusted for potentially faster testing/demo

# Recommender System Configuration
DEFAULT_NUM_RECOMMENDATIONS = 10 # Default number of recommendations to return by the API
OMDB_API_FETCH_LIMIT = 50 # Limit for fetching movies from OMDB API in one go by default list (original was 400, can be high for startup)
# Note: The long list of default movie titles is in core/recommender.py

# Server Configuration (for main run.py)
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = False # Set to True for development, False for 'production'

GRADIO_SERVER_NAME = "0.0.0.0" # Makes Gradio accessible on the network
GRADIO_SERVER_PORT = 7860
GRADIO_DEBUG = True # For Gradio specific debugging

# Ngrok (optional, if used)
# NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN") # Loaded via dotenv in specific modules if needed

# Fallback data path (if loading from a local file was an option)
# FALLBACK_MOVIE_DATA_PATH = "data/fallback_movies.json"

print("Config loaded: API_BASE_URL={}, MAX_SELECTIONS={}, MIN_SELECTIONS_FOR_RECOMMENDATIONS={}".format(API_BASE_URL, MAX_SELECTIONS, MIN_SELECTIONS_FOR_RECOMMENDATIONS))
