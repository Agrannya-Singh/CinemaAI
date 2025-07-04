import os
import threading
import time # Keep time if used by start_flask_server or other parts, otherwise remove
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Assuming MovieRecommendationSystem will be initialized and passed or imported
# For this structure, we'll import it.
from core.recommender import MovieRecommendationSystem

# Load environment variables for the Flask app context if not already loaded globally
load_dotenv()

# Initialize the recommender globally or pass it around
# Global initialization is simpler for this structure
recommender = MovieRecommendationSystem()

# --- Flask Application ---
app = Flask(__name__)
CORS(app)  # Enable CORS

@app.route('/')
def index():
    """Health check and info endpoint"""
    return jsonify({
        "message": "CinemaAI Recommendation API is running!",
        "status": "success",
        "endpoints": {
            "/api/movies": "GET - Fetches all available movies.",
            "/api/recommend": "POST - Gets recommendations based on selected movie IDs. Body: {'selected_movies': ['id1', 'id2']}",
            "/api/health": "GET - Detailed health check of the API and recommender system."
        }
    })

@app.route('/api/movies', methods=['GET'])
def get_movies_route(): # Renamed to avoid conflict with any potential local 'get_movies'
    """Get all movies for display"""
    try:
        # Prepare data if not already done (e.g., on first call or if data can expire)
        # For simplicity, we assume prepare_movie_data is called on recommender init or needs to be robustly handled.
        if recommender.movies_df is None or recommender.movies_df.empty:
            print("API: Movie data not present, preparing...")
            recommender.prepare_movie_data() # This might take time on first load
            if recommender.movies_df is None or recommender.movies_df.empty:
                 print("API: Failed to load movies even after prepare_movie_data.")
                 return jsonify({'error': 'Failed to load movies internally'}), 500
            print(f"API: Loaded {len(recommender.movies_df)} movies.")

        movies_list = recommender.movies_df.to_dict('records')
        return jsonify(movies_list)

    except Exception as e:
        print(f"Error in /api/movies: {e}")
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch movies due to an internal server error.'}), 500

@app.route('/api/recommend', methods=['POST'])
def recommend_movies_route(): # Renamed
    """Get recommendations based on selected movies"""
    try:
        data = request.json
        if not data or 'selected_movies' not in data:
            return jsonify({'error': 'Missing selected_movies in request body'}), 400

        selected_movie_ids = data.get('selected_movies', [])

        if not isinstance(selected_movie_ids, list):
            return jsonify({'error': 'selected_movies must be a list of movie IDs'}), 400

        # Basic validation for IDs (e.g., non-empty strings)
        selected_movie_ids = [str(id_val).strip() for id_val in selected_movie_ids if str(id_val).strip()]

        if not selected_movie_ids:
             return jsonify({'error': 'selected_movies list cannot be empty after validation'}), 400


        # The original code had a check for len < 5. This can be handled by client or here.
        # For now, let's keep it if it's a hard requirement for the recommender.
        # However, the UI seems to control this with MIN_RECOMMENDATIONS.
        # If the recommender itself needs a minimum, it should enforce it.
        # For now, I'll trust the recommender's logic.
        # if len(selected_movie_ids) < 1: # Or whatever minimum the recommender can handle
        #     return jsonify({'error': 'Please select at least 1 movie for recommendations.'}), 400


        print(f"API: Getting recommendations for movies: {selected_movie_ids}")
        recommendations = recommender.get_recommendations(selected_movie_ids, num_recommendations=10) # Default to 10 recs

        if not recommendations:
            # It's not necessarily an error if no recommendations are found.
            # Could be due to obscure selections or all similar movies already selected.
            print(f"API: No recommendations found for IDs: {selected_movie_ids}")
            return jsonify([]) # Return empty list, client can handle this

        return jsonify(recommendations)

    except Exception as e:
        print(f"Error in /api/recommend: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get recommendations due to an internal server error.'}), 500

@app.route('/api/health', methods=['GET'])
def health_check_route(): # Renamed
    """Health check endpoint for the API and recommender system"""
    movies_loaded_count = 0
    if recommender.movies_df is not None:
        movies_loaded_count = len(recommender.movies_df)

    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "recommender_status": {
            "movies_loaded": movies_loaded_count,
            "similarity_matrix_built": recommender.similarity_matrix is not None,
            "omdb_api_key_present": recommender.API_KEY is not None
        }
    })

# Function to start Flask server (can be called from the main run.py)
def start_flask_server(host='127.0.0.1', port=5000, debug=False):
    """Start Flask server."""
    # Note: app.run() is blocking. It should be run in a thread if Gradio is in the same process.
    # The debug mode should ideally be False for 'production' or shared spaces.
    print(f"🚀 Starting Flask backend server on http://{host}:{port}")
    try:
        # Prepare movie data on startup to make first API calls faster
        # This can take time, so consider if it's better to do it lazily on first request
        # or show a loading state in the UI.
        print("Flask Server: Initializing and preparing movie data...")
        recommender.prepare_movie_data()
        if recommender.movies_df is not None and not recommender.movies_df.empty:
            print(f"Flask Server: Movie data prepared. {len(recommender.movies_df)} movies loaded.")
        else:
            print("Flask Server: Warning - Movie data could not be prepared on startup. Fallback or API issues might occur.")

        app.run(host=host, port=port, debug=debug, use_reloader=False) # use_reloader=False if running in a thread
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # This allows running the Flask app directly for testing the API
    # e.g., python api/app.py
    # Ensure .env is in the root project directory for OMDB_API_KEY
    print("Running Flask API directly for testing...")
    start_flask_server(debug=True) # Enable debug for direct testing
    # Note: When debug=True, Flask's reloader might cause issues with threaded execution.
    # It's often better to run with debug=False when integrating with Gradio in one script.
    # The use_reloader=False flag in start_flask_server helps when threading.
    # For direct execution 'python api/app.py', debug=True with reloader is fine.
    # To match the threaded environment, you might run:
    # start_flask_server(debug=False, use_reloader=False) if you want to test that specifically.
    # However, for API development, debug=True is usually more helpful.
    # The start_flask_server function is now configured to use use_reloader=False by default.
    # When running this __main__ block, it will use app.run(debug=True) which implies reloader.
    # This is fine for isolated API testing.
    app.run(host='127.0.0.1', port=5000, debug=True)
