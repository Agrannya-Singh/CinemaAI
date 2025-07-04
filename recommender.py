import os
import requests
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Load environment variables at the module level if needed, or ensure API_KEY is passed
load_dotenv()

class MovieRecommendationSystem:
    def __init__(self):
        self.movies_df = None
        self.similarity_matrix = None
        self.vectorizer = CountVectorizer(stop_words='english')
        # Load API key from environment variable
        self.API_KEY = os.getenv("OMDB_API_KEY")
        if not self.API_KEY:
            print("🚨 WARNING: OMDB_API_KEY not found in environment variables.")
        self.BASE_URL = "http://www.omdbapi.com/"
        self.HEADERS = {} # Not currently used, but kept for potential future use

    def fetch_movie_by_title(self, title):
        """Fetch a single movie by title from OMDb API."""
        if not self.API_KEY:
            print("OMDb API key is not set. Cannot fetch movie.")
            return None
        params = {
            "apikey": self.API_KEY,
            "t": title,
            "plot": "full"
        }
        try:
            response = requests.get(self.BASE_URL, headers=self.HEADERS, params=params, timeout=10)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            data = response.json()
            if data.get("Response") == "True":
                return data
            else:
                print(f"OMDb API Error for '{title}': {data.get('Error', 'Unknown error')}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout fetching movie '{title}'.")
            return None
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error fetching movie '{title}': {http_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"Request exception fetching movie '{title}': {req_err}")
            return None
        except Exception as e:
            print(f"Generic error fetching movie '{title}': {e}")
            return None

    def fetch_movies(self, titles=None, limit=400):
        """Fetch a list of movies, either from provided titles or a default list."""
        if titles is None:
            titles = [
                "Inception", "The Dark Knight", "Interstellar", "The Matrix", "Fight Club",
                "Pulp Fiction", "Forrest Gump", "The Shawshank Redemption", "Gladiator", "Titanic",
                "Avatar", "The Avengers", "Jurassic Park", "Star Wars", "The Lord of the Rings",
                "Harry Potter", "Pirates of the Caribbean", "The Godfather", "Back to the Future",
                "Indiana Jones", "The Lion King", "Toy Story", "Finding Nemo", "Up", "WALL-E",
                "The Incredibles", "Coco", "Spider-Man", "Iron Man", "Captain America",
                "Thor", "Black Panther", "Deadpool", "Logan", "X-Men", "Batman Begins",
                "The Dark Knight Rises", "Man of Steel", "Wonder Woman", "Aquaman", "Parasite",
                "Joker", "Once Upon a Time in Hollywood", "Avengers: Endgame", "Toy Story 4",
                "Spider-Man: Into the Spider-Verse", "Green Book", "Bohemian Rhapsody",
                "A Star Is Born", "The Irishman", "1917", "Ford v Ferrari", "Little Women",
                "Marriage Story", "Knives Out", "Us", "Midsommar", "Get Out", "Dunkirk",
                "La La Land", "Moonlight", "Arrival", "Hacksaw Ridge", "Hell or High Water",
                "Manchester by the Sea", "Hidden Figures", "Lion", "Fences", "Zootopia",
                "Moana", "Sing Street", "The Nice Guys", "Captain America: Civil War",
                "Doctor Strange", "Fantastic Beasts and Where to Find Them", "Rogue One: A Star Wars Story",
                "The Martian", "Mad Max: Fury Road", "Inside Out", "Spotlight", "The Revenant",
                "Room", "Brooklyn", "Carol", "Sicario", "Straight Outta Compton", "The Big Short",
                "Bridge of Spies", "Ex Machina", "The Hateful Eight", "Anomalisa", "Son of Saul",
                "The Lobster", "Amy", "Cartel Land", "Winter on Fire: Ukraine's Fight for Freedom",
                "What Happened, Miss Simone?", "Listen to Me Marlon", "The Look of Silence",
                "Shaun the Sheep Movie", "When Marnie Was There", "Boy and the World", "Mustang",
                "Embrace of the Serpent", "Theeb", "A War", "A Bigger Splash", "Florence Foster Jenkins",
                "Hail, Caesar!", "Julieta", "Love & Friendship", "Maggie's Plan", "Miles Ahead",
                "Our Little Sister", "Paterson"
            ] # Simplified default list for brevity, original was very long and repetitive

        movies_data = []
        # Ensure titles are unique to avoid redundant API calls, then take the limit
        unique_titles = list(dict.fromkeys(titles))
        titles_to_fetch = unique_titles[:limit] if limit is not None else unique_titles


        for title in titles_to_fetch:
            movie_data = self.fetch_movie_by_title(title)
            if movie_data:
                movies_data.append(movie_data)
            # Optional: Add a small delay to be respectful to the API
            # time.sleep(0.1)

        return movies_data

    def prepare_movie_data(self):
        """Prepare movie data from OMDb API or fallback if API fetch fails."""
        fetched_api_movies = self.fetch_movies() # Using the default list and limit

        if not fetched_api_movies:
            print("🚨 API returned no movies or API key is missing. Loading fallback dataset.")
            fallback_movies_data = [
                {'id': 'tt0372784', 'title': 'Batman Begins', 'overview': 'A young Bruce Wayne becomes Batman to fight crime in Gotham.', 'genres': 'Action, Adventure, Crime', 'cast': 'Christian Bale, Michael Caine', 'poster_path': 'https://m.media-amazon.com/images/M/MV5BMjE3NDcyNDExNF5BMl5BanBnXkFtZTcwMDYwNDk0OA@@._V1_SX300.jpg', 'vote_average': 8.2, 'release_date': '2005', 'combined_features': 'Action Adventure Crime Christian Bale Michael Caine A young Bruce Wayne becomes Batman to fight crime in Gotham.'},
                {'id': 'tt0468569', 'title': 'The Dark Knight', 'overview': 'Batman faces the Joker, a criminal mastermind.', 'genres': 'Action, Crime, Drama, Thriller', 'cast': 'Christian Bale, Heath Ledger', 'poster_path': 'https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@._V1_SX300.jpg', 'vote_average': 9.0, 'release_date': '2008', 'combined_features': 'Action Crime Drama Thriller Christian Bale Heath Ledger Batman faces the Joker, a criminal mastermind.'},
                {'id': 'tt1345836', 'title': 'The Dark Knight Rises', 'overview': 'Batman returns to save Gotham from Bane.', 'genres': 'Action, Crime, Thriller', 'cast': 'Christian Bale, Tom Hardy', 'poster_path': 'https://m.media-amazon.com/images/M/MV5BMTk4ODQzNDY3Ml5BMl5BanBnXkFtZTcwODA0NTM4Nw@@._V1_SX300.jpg', 'vote_average': 8.4, 'release_date': '2012', 'combined_features': 'Action Crime Thriller Christian Bale Tom Hardy Batman returns to save Gotham from Bane.'},
                {'id': 'tt0144084', 'title': 'American Psycho', 'overview': 'A Wall Street banker leads a double life as a serial killer.', 'genres': 'Crime, Drama, Horror', 'cast': 'Christian Bale, Willem Dafoe', 'poster_path': 'https://m.media-amazon.com/images/M/MV5BZTM2ZGJmNzktNzc3My00ZWMzLTg0MjItZjBlMWJiNDE0NjZiXkEyXkFqcGc@._V1_SX300.jpg', 'vote_average': 7.6, 'release_date': '2000', 'combined_features': 'Crime Drama Horror Christian Bale Willem Dafoe A Wall Street banker leads a double life as a serial killer.'},
                {'id': 'tt0246578', 'title': 'Donnie Darko', 'overview': 'A troubled teenager is plagued by visions of a man in a rabbit costume.', 'genres': 'Drama, Sci-Fi, Thriller', 'cast': 'Jake Gyllenhaal, Maggie Gyllenhaal', 'poster_path': 'https://m.media-amazon.com/images/M/MV5BZjZlZDlkYTktMmU1My00ZDBiLWE0TAQtNjkzZDFiYTY0ZmMyXkEyXkFqcGc@._V1_SX300.jpg', 'vote_average': 8.0, 'release_date': '2001', 'combined_features': 'Drama Sci-Fi Thriller Jake Gyllenhaal Maggie Gyllenhaal A troubled teenager is plagued by visions of a man in a rabbit costume.'}
            ]
            self.movies_df = pd.DataFrame(fallback_movies_data)
        else:
            print(f"✅ Successfully fetched {len(fetched_api_movies)} movies from OMDb API.")
            processed_movie_data = []
            for movie in fetched_api_movies:
                movie_info = {
                    'id': movie.get('imdbID', movie.get('Title', f"unknown_{movie.get('Title', 'id')}")), # Ensure unique ID
                    'title': movie.get('Title', ''),
                    'overview': movie.get('Plot', ''),
                    'genres': movie.get('Genre', ''),
                    'cast': movie.get('Actors', ''),
                    'poster_path': movie.get('Poster', ''),
                    'vote_average': float(movie.get('imdbRating', '0')) if movie.get('imdbRating') not in ['N/A', None, ''] else 0.0,
                    'release_date': movie.get('Year', ''),
                    'combined_features': f"{movie.get('Genre', '')} {movie.get('Actors', '')} {movie.get('Plot', '')}"
                }
                processed_movie_data.append(movie_info)
            self.movies_df = pd.DataFrame(processed_movie_data)

        self.build_similarity_matrix()
        return self.movies_df

    def build_similarity_matrix(self):
        """Build similarity matrix for recommendations based on combined features."""
        if self.movies_df is not None and not self.movies_df.empty:
            # Ensure 'combined_features' exists and handle potential NaN values
            if 'combined_features' not in self.movies_df.columns:
                print("🚨 'combined_features' column missing. Recreating it.")
                self.movies_df['combined_features'] = self.movies_df.apply(
                    lambda x: f"{x.get('genres', '')} {x.get('cast', '')} {x.get('overview', '')}", axis=1
                )

            corpus = self.movies_df['combined_features'].fillna('').astype(str).tolist()

            if not any(corpus): # Check if corpus is all empty strings
                print("🚨 Corpus is empty or contains only empty strings. Cannot build similarity matrix.")
                self.similarity_matrix = None # Explicitly set to None
                return

            max_features = min(5000, len(set(" ".join(corpus).split()))) # Adjust max_features dynamically
            if max_features == 0 : max_features = 1 # Ensure max_features is at least 1 if corpus is not totally empty

            self.vectorizer = CountVectorizer(stop_words='english', max_features=max_features)

            try:
                vectorized_features = self.vectorizer.fit_transform(corpus)
                if vectorized_features.shape[0] > 0 and vectorized_features.shape[1] > 0 :
                    self.similarity_matrix = cosine_similarity(vectorized_features)
                    print(f"✅ Similarity matrix built with shape: {self.similarity_matrix.shape}")
                else:
                    print("🚨 Vectorized features are empty. Cannot build similarity matrix.")
                    self.similarity_matrix = None # Ensure it's None if matrix is not built
            except ValueError as e:
                print(f"🚨 Error building similarity matrix (ValueError): {e}. Corpus might be problematic.")
                self.similarity_matrix = None # Ensure it's None on error
        else:
             print("🚨 Cannot build similarity matrix: movies_df is empty or None.")
             self.similarity_matrix = None # Ensure it's None

    def get_recommendations(self, selected_movie_ids: list, num_recommendations=5) -> list:
        """Get movie recommendations based on selected movie IDs."""
        if self.similarity_matrix is None or self.movies_df is None or self.movies_df.empty:
            print("Debug: Similarity matrix or movies_df is empty/None. Cannot get recommendations.")
            return []

        # Ensure selected_movie_ids contains valid IDs present in the DataFrame
        valid_selected_indices = self.movies_df[self.movies_df['id'].isin(selected_movie_ids)].index.tolist()

        if not valid_selected_indices:
            print(f"Debug: No valid selected movies (IDs: {selected_movie_ids}) found in DataFrame for recommendations.")
            return []

        # Aggregate similarity scores for selected movies
        # Handle cases where some selected IDs might not be in similarity_matrix (if matrix smaller than df)
        # This shouldn't happen if matrix is built from the current df
        avg_similarity_scores = np.mean(self.similarity_matrix[valid_selected_indices, :], axis=0)

        # Get indices of movies sorted by similarity
        # Argsort returns indices that would sort the array. [::-1] reverses for descending.
        sorted_movie_indices = np.argsort(avg_similarity_scores)[::-1]

        recommendations = []
        seen_movie_ids = set(selected_movie_ids) # Keep track of movies already selected or recommended

        for idx in sorted_movie_indices:
            if idx >= len(self.movies_df): # Boundary check
                continue

            movie_candidate = self.movies_df.iloc[idx]
            movie_id = movie_candidate['id']

            if movie_id not in seen_movie_ids:
                recommendations.append(movie_candidate.to_dict())
                seen_movie_ids.add(movie_id) # Add to seen to avoid duplicates in recommendations
                if len(recommendations) >= num_recommendations:
                    break

        if not recommendations:
            print(f"Debug: No recommendations generated for selected IDs: {selected_movie_ids}. All similar movies might have been among selections.")

        return recommendations

# Example usage (optional, for testing this module directly)
if __name__ == '__main__':
    # This part will only run if you execute this file directly (e.g., python core/recommender.py)
    # You'll need a .env file with OMDB_API_KEY in the root of your project for this to work
    print("Testing MovieRecommendationSystem...")
    rec_sys = MovieRecommendationSystem()

    # Test API Key presence
    if not rec_sys.API_KEY:
        print("Cannot run full test without OMDB_API_KEY. Using fallback data for remaining tests.")

    # Test data preparation
    print("\nPreparing movie data...")
    movies_dataframe = rec_sys.prepare_movie_data()
    if movies_dataframe is not None and not movies_dataframe.empty:
        print(f"Movie data prepared. DataFrame shape: {movies_dataframe.shape}")
        # print(movies_dataframe.head())

        # Test similarity matrix
        if rec_sys.similarity_matrix is not None:
            print(f"Similarity matrix shape: {rec_sys.similarity_matrix.shape}")

            # Test recommendations (example with first few movies if available)
            if len(movies_dataframe) >= 5:
                sample_selection_ids = movies_dataframe['id'].head(2).tolist()
                print(f"\nGetting recommendations for: {sample_selection_ids}")
                recommendations_output = rec_sys.get_recommendations(sample_selection_ids, num_recommendations=3)
                if recommendations_output:
                    print("Recommendations found:")
                    for rec in recommendations_output:
                        print(f"- {rec.get('title')} (ID: {rec.get('id')})")
                else:
                    print("No recommendations returned for the sample selection.")
            else:
                print("Not enough movies in DataFrame to test recommendations.")
        else:
            print("Similarity matrix was not built. Cannot test recommendations.")
    else:
        print("Movie DataFrame is empty or None. Cannot proceed with further tests.")

    # Test fetching a single movie (if API key is present)
    if rec_sys.API_KEY:
        print("\nTesting fetch_movie_by_title for 'Inception'...")
        inception_data = rec_sys.fetch_movie_by_title("Inception")
        if inception_data:
            print(f"Successfully fetched 'Inception': {inception_data.get('Title')} ({inception_data.get('Year')})")
        else:
            print("Failed to fetch 'Inception'.")
    else:
        print("\nSkipping fetch_movie_by_title test as API key is missing.")

    print("\nRecommender tests finished.")
