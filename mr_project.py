
import streamlit as st
import joblib
import requests
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="MovieVerse | Movie Recommendations",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #080d1b, #111b30, #080d1b);
    color: white;
}

.block-container {
    max-width: 1250px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

#MainMenu, footer {
    visibility: hidden;
}

header {
    background: transparent !important;
}

.hero {
    text-align: center;
    padding: 32px 20px;
    margin-bottom: 24px;
    border: 1px solid #263b58;
    border-radius: 22px;
    background: linear-gradient(120deg, #15263e, #101827, #18343c);
    box-shadow: 0 10px 35px rgba(0,0,0,0.25);
}

.hero h1 {
    color: white;
    font-size: 43px;
    margin: 0;
    font-weight: 800;
    letter-spacing: 1px;
}

.hero p {
    color: #b9c9dc;
    font-size: 16px;
    margin-top: 10px;
}

.section-title {
    color: #66e3d2;
    font-size: 25px;
    font-weight: 750;
    margin-top: 12px;
    margin-bottom: 15px;
}

div[data-testid="stSelectbox"] label {
    color: white !important;
    font-size: 17px !important;
    font-weight: 700 !important;
}

div[data-baseweb="select"] > div {
    background-color: #17243a !important;
    border: 1px solid #4c708e !important;
    border-radius: 12px !important;
    min-height: 54px !important;
}

div[data-baseweb="select"] * {
    color: white !important;
}

div.stButton > button {
    width: 100%;
    min-height: 48px;
    border: none;
    border-radius: 12px;
    color: #07111c;
    font-weight: 800;
    font-size: 16px;
    background: linear-gradient(90deg, #61e7d2, #7bb8ff);
    transition: 0.2s ease;
}

div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 18px #49c9c455;
}

.movie-title {
    color: white;
    font-size: 17px;
    font-weight: 750;
    text-align: center;
    min-height: 48px;
    padding: 12px 5px 4px 5px;
    overflow-wrap: anywhere;
}

.movie-label {
    text-align: center;
    color: #83dfd5;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.sidebar-heading {
    color: #65dfd0;
    font-size: 22px;
    font-weight: 800;
}

.contact-box {
    background: #142238;
    border: 1px solid #2b4562;
    border-radius: 12px;
    padding: 13px;
    color: #e2eaf5;
    overflow-wrap: anywhere;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #101b2d;
    border: 1px solid #293e59;
    border-radius: 16px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- LOAD PROJECT FILES ----------------
@st.cache_resource
def load_files():
    model = joblib.load("model.pkl")
    vectors = joblib.load("vectors.pkl")
    df = joblib.load("dataframe.pkl")

    if not hasattr(model, "kneighbors"):
        raise ValueError(
            "model.pkl mein NearestNeighbors model nahi hai. "
            "Model ko training code se dobara save karo."
        )

    if "name" not in df.columns:
        raise ValueError("dataframe.pkl mein 'name' column nahi mila.")

    df = df.reset_index(drop=True)

    if vectors.shape[0] != len(df):
        raise ValueError(
            "Movies aur vectors ki rows match nahi kar rahi hain. "
            "Teeno pickle files same training run se honi chahiye."
        )

    return model, vectors, df


try:
    model, vectors, df = load_files()
except Exception as e:
    st.error(f"Project files load nahi ho paayi: {e}")
    st.stop()


# ---------------- POSTER NOT FOUND IMAGE ----------------
def create_not_found_poster():
    image = Image.new("RGB", (600, 900), (15, 26, 43))
    draw = ImageDraw.Draw(image)

    # Decorative frame
    draw.rounded_rectangle(
        (35, 35, 565, 865),
        radius=25,
        outline=(68, 105, 130),
        width=4
    )

    # Movie icon
    draw.rounded_rectangle(
        (205, 290, 395, 430),
        radius=18,
        outline=(100, 225, 210),
        width=5
    )

    draw.polygon(
        [(275, 325), (275, 395), (335, 360)],
        fill=(100, 225, 210)
    )

    try:
        font = ImageFont.truetype("arial.ttf", 37)
        small_font = ImageFont.truetype("arial.ttf", 23)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    title = "POSTER NOT FOUND"
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]

    draw.text(
        ((600 - text_width) / 2, 485),
        title,
        fill=(255, 255, 255),
        font=font
    )

    subtitle = "Image unavailable"
    bbox = draw.textbbox((0, 0), subtitle, font=small_font)
    text_width = bbox[2] - bbox[0]

    draw.text(
        ((600 - text_width) / 2, 545),
        subtitle,
        fill=(155, 180, 200),
        font=small_font
    )

    return image


# ---------------- FETCH MOVIE POSTER ----------------
def fetch_movie_poster(movie_name):
    api_key = os.getenv("OMDB_API_KEY", "b96c19b8")

    try:
        response = requests.get(
            "https://www.omdbapi.com/",
            params={
                "apikey": api_key,
                "t": str(movie_name),
                "type": "movie"
            },
            timeout=8
        )
        response.raise_for_status()
        data = response.json()

        poster_url = data.get("Poster", "")

        if (
            data.get("Response") == "True"
            and poster_url
            and poster_url != "N/A"
        ):
            image_response = requests.get(
                poster_url,
                timeout=8
            )
            image_response.raise_for_status()

            image = Image.open(
                BytesIO(image_response.content)
            ).convert("RGB")

            # Keep every poster at the same 2:3 ratio.
            canvas = Image.new(
                "RGB",
                (600, 900),
                (13, 22, 38)
            )

            fitted = ImageOps.contain(image, (560, 860))

            x = (600 - fitted.width) // 2
            y = (900 - fitted.height) // 2

            canvas.paste(fitted, (x, y))
            return canvas

    except Exception:
        pass

    # Display a custom poster instead of a blank image.
    return create_not_found_poster()


@st.cache_data(show_spinner=False)
def cached_poster(movie_name):
    return fetch_movie_poster(movie_name)


# ---------------- HEADER ----------------
st.markdown("""
<div class="hero">
    <h1>🎬 MovieVerse</h1>
    <p>Discover your next favourite movie with intelligent recommendations.</p>
</div>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
with st.sidebar:

    # Sidebar image
    if os.path.exists("image.png"):
        st.image("image.png", use_container_width=True)

    st.markdown(
        '<div class="sidebar-heading">🎥 MovieVerse</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown("### ✨ About Us")
    st.write(
        "We explore machine learning and build projects "
        "that make everyday experiences smarter."
    )

    st.markdown("### 🍿 About This Project")
    st.write(
        "MovieVerse recommends movies by finding similarities "
        "between movie content and features."
    )

    st.markdown("### ⚙️ Technology")
    st.write("🐍 Python")
    st.write("🧠 Scikit-learn")
    st.write("📊 Pandas")
    st.write("🌐 Streamlit")

    st.markdown("---")

    st.markdown("### 📞 Contact Us")
    st.markdown("""
    <div class="contact-box">
        <b>📱 Phone</b><br>
        +91 80904 28587
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.caption("Made with ❤️ and Machine Learning")


# ---------------- MOVIE DROPDOWN ----------------
st.markdown(
    '<div class="section-title">🍿 Find Movies You May Like</div>',
    unsafe_allow_html=True
)

left_space, dropdown_col, right_space = st.columns([1, 3, 1])

movie_names = (
    df["name"]
    .dropna()
    .astype(str)
    .tolist()
)

movie_names = list(dict.fromkeys(movie_names))

with dropdown_col:

    selected_movie = st.selectbox(
        "Choose a movie from the list",
        options=movie_names,
        index=None,
        placeholder="🎬 Select your favourite movie...",
        key="movie_dropdown"
    )

    recommend_clicked = st.button(
        "✨ Recommend Similar Movies",
        use_container_width=True
    )


# ---------------- RECOMMENDATIONS ----------------
# No "How it works" box is displayed.

if recommend_clicked:

    if not selected_movie:
        st.warning("Please select a movie from the dropdown first.")
        st.stop()

    movie_indices = df.index[
        df["name"].astype(str) == selected_movie
    ].tolist()

    if not movie_indices:
        st.error("Selected movie was not found.")
        st.stop()

    movie_index = movie_indices[0]

    try:
        distances, indexes = model.kneighbors(
            vectors[movie_index],
            n_neighbors=min(7, len(df))
        )

        recommendations = []

        for idx, distance in zip(indexes[0], distances[0]):
            if idx == movie_index:
                continue

            recommendations.append((idx, distance))

        recommendations = recommendations[:6]

        st.markdown(
            f'<div class="section-title">'
            f'🎯 Movies Similar to {selected_movie}'
            f'</div>',
            unsafe_allow_html=True
        )

        if not recommendations:
            st.info("No similar movies were found.")

        else:
            cols = st.columns(3, gap="large")

            for i, (idx, distance) in enumerate(recommendations):

                movie_name = str(df.iloc[idx]["name"])

                with cols[i % 3]:

                    with st.container(border=True):

                        st.markdown(
                            '<div class="movie-label">'
                            'RECOMMENDED FOR YOU'
                            '</div>',
                            unsafe_allow_html=True
                        )

                        poster = cached_poster(movie_name)

                        st.image(
                            poster,
                            use_container_width=True
                        )

                        st.markdown(
                            f'<div class="movie-title">'
                            f'{movie_name}'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    except Exception as e:
        st.error(
            f"Recommendations generate nahi ho paayi: {e}"
        )
