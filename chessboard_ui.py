import streamlit as st
import streamlit.components.v1 as components
import os

def load_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        st.error(f"Error loading file {file_path}: {e}")
        return ""

def create_chess_app():
    st.set_page_config(page_title="Chess Game", layout="wide")
    st.title("Chess Game")

    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Paths to static files
    html_path = os.path.join(current_dir, 'static', 'html', 'chessboard.html')
    js_path = os.path.join(current_dir, 'static', 'js', 'chess_logic.js')
    css_path = os.path.join(current_dir, 'static', 'css', 'chessboard.css')

    # Read file contents
    html_content = load_file(html_path)
    js_content = load_file(js_path)
    css_content = load_file(css_path)

    # Combine HTML, CSS, and JS
    full_html = f"""
    <style>
    {css_content}
    </style>
    {html_content}
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
    {js_content}
    </script>
    """

    # Create columns for layout
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # Render the chessboard
        components.html(full_html, height=600, scrolling=False)

    with col2:
        # New Game and Undo buttons
        st.markdown("### Game Controls")
        if st.button("New Game", key="new_game_btn"):
            components.html("""
            <script>
            // Use the globally exposed resetGame function from chess_logic.js
            if (window.resetGame) {
                window.resetGame();
            } else {
                console.error('resetGame function not found');
            }
            </script>
            """, height=0)

        if st.button("Undo Move", key="undo_btn"):
            components.html("""
            <script>
            // Use the globally exposed undoLastMove function from chess_logic.js
            if (window.undoLastMove) {
                window.undoLastMove();
            } else {
                console.error('undoLastMove function not found');
            }
            </script>
            """, height=0)

    with col3:
        # Game settings
        st.markdown("### Game Settings")
        
        game_mode = st.selectbox(
            "Game Mode", 
            ["Player vs Player", "Player vs AI", "AI vs AI"],
            key="game_mode_select"
        )
        
        difficulty = st.selectbox(
            "Difficulty", 
            ["Easy", "Medium", "Hard"],
            key="difficulty_select",
            disabled=game_mode == "Player vs Player"
        )

def main():
    create_chess_app()

if __name__ == "__main__":
    main()