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

    # Create columns for layout
    col1, col2 = st.columns([3, 1])

    with col1:
        # Render the chessboard with full initialization and buttons
        chess_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
            body {
                font-family: sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4; /* Softer background */
                display: flex;
                justify-content: center;
                align-items: flex-start; /* Align items to the top */
                min-height: 100vh; /* Consider removing if not needed */
            }

            .chess-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 20px;
                width: 100%;
                max-width: 900px; /* Slightly wider container */
                padding: 20px;
                background-color: #fff; /* White container background */
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .game-area {
                display: flex;
                flex-direction: row;
                gap: 30px;
                align-items: flex-start; /* Align board and history to the top */
            }

            #myBoard {
                width: 500px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15); /* Slightly stronger shadow */
                border-radius: 4px;
            }

            #moveHistory {
                width: 200px; /* Reduced width for a sleeker look */
                max-height: 400px; /* Reduced max height */
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                background-color: #f9f9f9; /* Light gray background for history */
                border-radius: 4px;
                font-size: 0.9em; /* Slightly smaller font */
            }

            #gameStatus {
                margin-top: 10px;
                font-size: 1.2em;
                font-weight: bold;
                text-align: center;
            }

            .controls-container {
                display: flex;
                gap: 30px;
                margin-top: 5px;
            }

            .controls-container button {
                padding: 10px 20px;
                cursor: pointer;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #eee;
                font-size: 1em;
            }

            .controls-container button:hover {
                background-color: #ddd;
            }

            .winner-text {
                color: #2e75b6; /* A nice blue color */
                text-shadow: 0 0 10px rgba(46, 117, 182, 0.5);
                animation: none; /* Removed flashy animation for a cleaner look */
                transform: scale(1.0); /* Removed scaling animation */
            }

            @keyframes flash {
                0%, 50%, 100% { opacity: 1; }
                25%, 75% { opacity: 0; }
            }

            @keyframes scale {
                0% { transform: scale(0.5); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }
            </style>

            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        </head>
        <body>
            <div class="chess-container">
                <div class="game-area">
                    <div id="myBoard" style="width: 500px;"></div>
                    <div id="moveHistory"></div>
                </div>
                <div id="gameStatus"></div>
                <div class="controls-container">
                    <button id="newGameBtn">New Game</button>
                    <button id="undoMoveBtn">Undo Move</button>
                </div>
            </div>

            <script>
            // Global variables
            let game = new Chess();
            let board;
            let moveHistory = [];

            // Initialize board
            $(document).ready(function() {
                const config = {
                    draggable: true,
                    position: 'start',
                    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png', // Add piece theme URL
                    onDragStart: onDragStart,
                    onDrop: onDrop,
                    onSnapEnd: onSnapEnd
                };
                board = Chessboard('myBoard', config);

                // Set up button event listeners
                document.getElementById('newGameBtn').addEventListener('click', resetGame);
                document.getElementById('undoMoveBtn').addEventListener('click', undoMove);
            });

            // Drag and drop chess logic
            function onDragStart(source, piece, position, orientation) {
                if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
                    (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
                    return false;
                }
            }

            function onDrop(source, target) {
                const move = game.move({
                    from: source,
                    to: target,
                    promotion: 'q'
                });

                if (move === null) return 'snapback';

                board.position(game.fen());
                updateMoveHistory(move);
                checkGameStatus();
            }

            function onSnapEnd() {
                board.position(game.fen());
            }

            // Update move history
            function updateMoveHistory(move) {
                moveHistory.push(move.san);
                const historyDiv = document.getElementById('moveHistory');
                if (historyDiv) {
                    historyDiv.innerHTML = moveHistory.map((move, index) =>
                        `${Math.floor(index/2 + 1)}. ${move}`
                    ).join('<br>');
                }
            }

            // Modify reset function to force re-render
            function resetGame() {
                // Create a new Chess game instance
                game = new Chess();

                // Reset board position and force re-render
                board.position('start');

                // Clear move history
                moveHistory = [];

                // Clear move history display
                const historyDiv = document.getElementById('moveHistory');
                if (historyDiv) historyDiv.innerHTML = '';

                // Clear game status
                const statusDiv = document.getElementById('gameStatus');
                if (statusDiv) statusDiv.innerHTML = '';

                console.log('Game fully reset');
            }

            // Undo move function
            function undoMove() {
                if (moveHistory.length > 0) {
                    game.undo();
                    board.position(game.fen());
                    moveHistory.pop();

                    const historyDiv = document.getElementById('moveHistory');
                    if (historyDiv) {
                        historyDiv.innerHTML = moveHistory.map((move, index) =>
                            `${Math.floor(index/2 + 1)}. ${move}`
                        ).join('<br>');
                    }

                    console.log('Move undone');
                }
            }

            // Game status checking
            function checkGameStatus() {
                const statusDiv = document.getElementById('gameStatus');

                if (game.in_checkmate()) {
                    const winner = game.turn() === 'w' ? 'Black' : 'White';
                    statusDiv.innerHTML = `<span class="winner-text">${winner} Wins!</span>`;
                } else if (game.in_draw()) {
                    statusDiv.innerHTML = 'Draw!';
                } else {
                    statusDiv.innerHTML = ''; // Clear status if game is ongoing
                }
            }
            </script>
        </body>
        </html>
        """
        components.html(chess_html, height=700, scrolling=False)

    with col2:
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