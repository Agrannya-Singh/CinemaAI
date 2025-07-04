import os
import threading
import time
from dotenv import load_dotenv

# Load environment variables from .env file at the very beginning
# This ensures that OMDB_API_KEY (and NGROK_AUTH_TOKEN if used by pyngrok directly) are available
load_dotenv()

# Import configurations
try:
    import config
except ImportError:
    print("ERROR: config.py not found. Please ensure it exists in the root directory.")
    exit(1)

# Import the Flask app and its start function
try:
    from api.app import app as flask_app  # Import the app instance itself
    from api.app import start_flask_server
except ImportError as e:
    print(f"ERROR: Could not import Flask app components from api.app: {e}")
    print("Ensure api/app.py exists and is correctly structured.")
    exit(1)

# Import the Gradio UI creation function and its app logic class
try:
    from ui.gradio_ui import CinemaCloneAppGradio, create_gradio_interface
except ImportError as e:
    print(f"ERROR: Could not import Gradio UI components from ui.gradio_ui: {e}")
    print("Ensure ui/gradio_ui.py exists and is correctly structured.")
    exit(1)

# Ngrok setup (optional, if needed for exposing Gradio)
# Ensure NGROK_AUTH_TOKEN is in your .env file if you plan to use ngrok
USE_NGROK = False # Set to True if you want to use ngrok for Gradio
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN") # Renamed from "Ngrok" for consistency

if USE_NGROK and NGROK_AUTH_TOKEN:
    try:
        from pyngrok import ngrok, conf
        print("Attempting to configure ngrok...")
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        print("Ngrok authentication token set.")
        # You can also configure region or other ngrok settings here if needed
        # Example: my_config = conf.PyngrokConfig(region="eu"); conf.set_default(my_config);
    except ImportError:
        print("WARNING: pyngrok is not installed, but USE_NGROK is True. Ngrok will not be used.")
        USE_NGROK = False
    except Exception as e:
        print(f"ERROR: Failed to configure ngrok: {e}")
        USE_NGROK = False
elif USE_NGROK and not NGROK_AUTH_TOKEN:
    print("WARNING: USE_NGROK is True, but NGROK_AUTH_TOKEN is not set in environment. Ngrok will not be used.")
    USE_NGROK = False


def main():
    print("-----------------------------------------")
    print("🚀 Launching CinemaAI Application 🚀")
    print("-----------------------------------------")

    # Initialize the Gradio application logic handler
    # It needs API base URL and other settings from config
    gradio_app_handler = CinemaCloneAppGradio(
        api_base_url=config.API_BASE_URL,
        max_selections=config.MAX_SELECTIONS,
        min_recommendations=config.MIN_SELECTIONS_FOR_RECOMMENDATIONS
    )

    # Create the Gradio interface, passing the handler
    gradio_interface = create_gradio_interface(gradio_app_handler)

    # Start Flask server in a separate thread
    # The start_flask_server function in api.app now includes preparing movie data
    print("\n[THREAD_LAUNCHER] Preparing to start Flask server...")
    flask_thread = threading.Thread(
        target=start_flask_server,
        args=(config.FLASK_HOST, config.FLASK_PORT, config.FLASK_DEBUG),
        daemon=True # Daemon threads exit when the main program exits
    )
    flask_thread.start()
    print("[THREAD_LAUNCHER] Flask server thread started.")

    # Give Flask a moment to start up and prepare initial data
    # Adjust sleep time as necessary, especially if prepare_movie_data is slow
    initial_wait_time = 15 # Increased from 5, can be up to 30-60s if API calls are slow
    print(f"\n[MAIN_APP] Waiting {initial_wait_time} seconds for Flask server to initialize and load data...")
    time.sleep(initial_wait_time)
    print("[MAIN_APP] Presumed Flask server is up and data loaded (or fallback used).")

    # Check if Flask is responsive (optional but good)
    try:
        health_url = f"{config.API_BASE_URL}/api/health"
        print(f"[MAIN_APP] Checking Flask API health at {health_url}...")
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print(f"[MAIN_APP] ✅ Flask API is healthy: {response.json().get('status', 'unknown status')}")
            recommender_status = response.json().get('recommender_status', {})
            print(f"    Movies loaded: {recommender_status.get('movies_loaded', 'N/A')}")
            print(f"    Similarity matrix built: {recommender_status.get('similarity_matrix_built', 'N/A')}")
            print(f"    OMDb API key present: {recommender_status.get('omdb_api_key_present', 'N/A')}")
        else:
            print(f"[MAIN_APP] ⚠️ Flask API health check failed or non-200 status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[MAIN_APP] ❌ CRITICAL: Could not connect to Flask API at {config.API_BASE_URL}. Gradio UI might not work correctly.")
        print("    Please check if the Flask server started correctly and there are no port conflicts.")
    except Exception as e:
        print(f"[MAIN_APP] ⚠️ Error during Flask API health check: {e}")


    # Launch Gradio interface
    print("\n[GRADIO_LAUNCHER] Preparing to launch Gradio interface...")
    public_url = None
    if USE_NGROK:
        try:
            # ngrok.connect takes the port Gradio will run on.
            # Ensure share=True is NOT used if Gradio's share=True is used, to avoid conflict.
            # Gradio's internal ngrok handling is usually preferred if share=True is used in demo.launch().
            # If using pyngrok directly, Gradio's share should be False.
            print(f"[NGROK] Attempting to create tunnel for port {config.GRADIO_SERVER_PORT}...")
            # tunnel = ngrok.connect(config.GRADIO_SERVER_PORT, "http") # pyngrok < 5
            # For pyngrok >= 5, you might specify a PyngrokConfig or let it use defaults.
            # If Gradio's share=True is used, it handles ngrok itself.
            # We will use Gradio's share=True for simplicity if USE_NGROK is true.
            # public_url = tunnel.public_url
            # print(f"[NGROK] ✅ Ngrok tunnel established: {public_url}")
            # print(f"[NGROK] Gradio will be accessible at this public URL.")
            pass # Rely on Gradio's share=True for ngrok handling
        except Exception as e:
            print(f"[NGROK] ❌ Failed to start ngrok tunnel: {e}. Gradio will only be available locally.")
            USE_NGROK = False # Fallback to local if ngrok fails

    try:
        print(f"[GRADIO_LAUNCHER] Launching Gradio on {config.GRADIO_SERVER_NAME}:{config.GRADIO_SERVER_PORT}")
        print(f"    Debug mode: {config.GRADIO_DEBUG}")
        print(f"    Sharing via ngrok (if enabled by share=True and NGROK_AUTH_TOKEN is set): {USE_NGROK}")

        gradio_interface.launch(
            server_name=config.GRADIO_SERVER_NAME,
            server_port=config.GRADIO_SERVER_PORT,
            debug=config.GRADIO_DEBUG,
            share=USE_NGROK  # Use Gradio's built-in ngrok if USE_NGROK is True
        )
        # If share=True and it succeeds, it will print the public URL.
        # If USE_NGROK was true and pyngrok was used manually:
        # print(f"Gradio is running. If local: http://{config.GRADIO_SERVER_NAME}:{config.GRADIO_SERVER_PORT}. Public (ngrok): {public_url if public_url else 'Not available'}")

    except Exception as e:
        print(f"❌ CRITICAL: Failed to launch Gradio interface: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if USE_NGROK:
            try:
                ngrok.disconnectall() # Disconnect all tunnels pyngrok might have opened
                ngrok.kill() # Kill the ngrok process
                print("[NGROK] Ngrok tunnels disconnected and process killed.")
            except Exception as e:
                print(f"[NGROK] Error while shutting down ngrok: {e}")
        print("\n[MAIN_APP] CinemaAI Application shutting down or launch completed.")


if __name__ == "__main__":
    # Ensure .env file is in the root directory where run.py is located
    # Example .env content:
    # OMDB_API_KEY="your_omdb_api_key"
    # NGROK_AUTH_TOKEN="your_ngrok_auth_token" (optional)

    # Check for critical environment variables
    if not os.getenv("OMDB_API_KEY"):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("! WARNING: OMDB_API_KEY is not set in your .env file or environment.         !")
        print("! The application will rely on fallback data and cannot fetch live movies.   !")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    main()
