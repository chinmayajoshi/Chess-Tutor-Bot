import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import chess # Python-chess library
import time # For simulating typing
from streamlit_js_eval import streamlit_js_eval

# --- Configuration ---
STARTING_FEN = chess.STARTING_FEN
COMPONENT_KEY = "chessboard_comp" # Define key for component

# --- Groq Client Initialization ---
# (Keep the same try-except block as before to load API key)
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    groq_client = Groq(api_key=GROQ_API_KEY)
    GROQ_MODEL = "llama3-8b-8192" # Or mixtral-8x7b-32768
    print("Groq client initialized.")
except (KeyError, FileNotFoundError):
    st.error("Groq API Key not found. Please add it to Streamlit secrets (secrets.toml).")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Groq client: {e}")
    st.stop()

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = [] # Chat history
if "current_fen" not in st.session_state:
    st.session_state.current_fen = STARTING_FEN # For reference/display
if "current_history_san" not in st.session_state:
    st.session_state.current_history_san = []
if "move_history" not in st.session_state:
    st.session_state.move_history = []

# --- Helper Functions ---
def format_moves_for_llm(history_san_list):
    if not history_san_list:
        return "No moves made yet."
    move_string = ""
    move_number = 1
    for i, move in enumerate(history_san_list):
        if i % 2 == 0:
            move_string += f"{move_number}. {move} "
        else:
            move_string += f"{move}\n"
            move_number += 1
    return move_string.strip()

def get_groq_response(user_prompt: str, game_moves_str: str, chat_history: list):
    """Gets a response from Groq LLM based on prompt, moves, and history."""
    if not groq_client:
        return "Error: Groq client not initialized."

    # Create a board object from the history to determine whose turn it is (optional, but helpful)
    board = chess.Board()
    turn_info = "It's White's turn."
    try:
        for move_san in game_moves_str.replace('\n', ' ').split():
            if '.' in move_san: # Skip move numbers
                continue
            if move_san:
                print("F3") # throws error at next line
                move = board.parse_san(move_san)
                board.push(move)
        turn_info = "It's Black's turn." if board.turn == chess.BLACK else "It's White's turn."
    except Exception as e:
        print(f"Error parsing SAN history for turn info: {e}")
        # Continue without accurate turn info if parsing fails

    system_prompt = f"""You are a helpful and friendly chess tutor observing a game.
Your goal is to help the user understand the current chess position resulting from the game's moves so far. \
Explain potential threats, opportunities, and general strategic ideas for the player whose turn it is. \
Avoid just giving the 'best' move. Keep explanations concise for a beginner/intermediate player. \
Keep your responses to under 200 words, unless the user asks for a longer response.

Game History (Standard Algebraic Notation):
{game_moves_str}

Current Situation: {turn_info}
"""

    messages_for_api = [
        {"role": "system", "content": system_prompt}
    ] + chat_history + [
        {"role": "user", "content": user_prompt}
    ]

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_for_api,
            model=GROQ_MODEL,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False,
        )
        response_content = chat_completion.choices[0].message.content
        return response_content
    except Exception as e:
        st.error(f"Error communicating with Groq: {e}")
        print(f"Error details: {e}")
        return f"Sorry, I encountered an error: {e}"

# --- Main App Structure ---
# load_file function remains the same (assuming it's correct)
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
        # Chess HTML + CSS + JS
        chess_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
            body {
                font-family: sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                /* min-height: 100vh; /* Maybe remove if causing issues */
            }

            .chess-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 20px;
                width: 100%;
                max-width: 900px;
                padding: 20px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            .game-area {
                display: flex;
                flex-direction: row;
                gap: 30px;
                align-items: flex-start;
            }

            #myBoard {
                width: 500px; /* Ensure width is sufficient */
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
                border-radius: 4px;
            }

            /* Make sure nothing here hides the board */
            #moveHistory {
                width: 200px;
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 4px;
                font-size: 0.9em;
            }

            #gameStatus {
                margin-top: 10px;
                font-size: 1.2em;
                font-weight: bold;
                text-align: center;
                min-height: 1.5em; /* Ensure space even when empty */
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
                color: #2e75b6;
                text-shadow: 0 0 10px rgba(46, 117, 182, 0.5);
            }

            .highlight-legal {
                /* Using a subtle dot via pseudo-element is often safer */
                position: relative;
            }
            .highlight-legal::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 15px; /* Size of the dot */
                height: 15px; /* Size of the dot */
                background-color: rgba(0, 0, 0, 0.3); /* Dot color */
                border-radius: 50%;
                transform: translate(-50%, -50%);
                pointer-events: none; /* Allow clicking through the dot */
            }

            @keyframes flash { 0%, 50%, 100% { opacity: 1; } 25%, 75% { opacity: 0; } }
            @keyframes scale { 0% { transform: scale(0.5); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
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
            let board = null; // Initialize board to null initially
            let moveHistory = [];

            // --- Check Streamlit ---
            setTimeout(() => { 
                window.parent.postMessage({ moveHistory: ["move1", "move2"] }, "*"); 
                console.log("🔥 sent move history!");
            }, 500);

            // --- CORRECTED: Function to remove highlight class ---
            function removeGreySquares () {
                // Select ALL squares and remove the highlight class from them
                $('#myBoard .square-55d63').removeClass('highlight-legal');
            }

            // --- Function to add highlight class (Unchanged) ---
            function greySquare (square) {
                const $square = $('#myBoard .square-' + square);
                $square.addClass('highlight-legal');
            }
            // --------------------------------------------

            // Initialize board
            $(document).ready(function() {
                console.log("Document ready. Initializing Chessboard..."); // Debug log
                try {
                    const config = {
                        draggable: true,
                        position: 'start',
                        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                        onDragStart: onDragStart,
                        onDrop: onDrop,
                        onSnapEnd: onSnapEnd,
                        // --- Remove highlights if drag is invalid/cancelled ---
                        // onDragMove: onDragMove, // Not needed explicitly
                        onSnapbackEnd: removeGreySquares // Clean up if move is invalid
                    };
                    board = Chessboard('myBoard', config); // Initialize the board here
                    console.log("Chessboard initialized successfully."); // Debug log

                    // Set up button event listeners AFTER board is initialized
                    $('#newGameBtn').on('click', resetGame); // Use jQuery for consistency
                    $('#undoMoveBtn').on('click', undoMove); // Use jQuery for consistency
                    console.log("Button listeners attached.");// Debug log


                    // Add resize listener to redraw board if container size changes
                    $(window).on('resize', function() {
                        if (board) { // Check if board exists
                           // board.resize(); // Call resize method if available/needed
                           // Or re-initialize if resize isn't smooth
                        }
                    }).trigger('resize'); // Trigger resize initially


                } catch (e) {
                    console.error("Error initializing chessboard:", e); // Catch initialization errors
                    $('#gameStatus').text("Error loading chessboard. Check console.");
                }
            });

            // Drag and drop chess logic
            function onDragStart(source, piece, position, orientation) {
                if (!board || !game) return false; // Make sure board/game are initialized

                // Do not pick up pieces if the game is over
                if (game.game_over()) return false

                // Only pick up pieces for the side to move
                if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
                    (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
                    return false;
                }

                // --- Highlight legal moves ---
                removeGreySquares(); // Clear previous highlights

                const moves = game.moves({
                    square: source,
                    verbose: true
                });

                // Exit if there are no moves available for this square
                if (moves.length === 0) {
                    console.log("No legal moves for " + piece + " on " + source);
                    return false; // Prevent dragging if no moves
                }

                // Highlight the squares this piece can move to
                for (let i = 0; i < moves.length; i++) {
                    greySquare(moves[i].to);
                }
                return true; // Allow drag
            }

            function onDrop(source, target) {
                removeGreySquares(); // Remove highlights immediately on drop attempt
                if (!board || !game) return 'snapback'; // Basic check

                // see if the move is legal
                const move = game.move({
                    from: source,
                    to: target,
                    promotion: 'q' // NOTE: always promote to a queen for example simplicity
                });

                // illegal move
                if (move === null) return 'snapback';

                // Update history and check status AFTER successful move
                updateMoveHistory(move);
                checkGameStatus();

                // Send the move in SAN to Streamlit
                if (typeof Streamlit !== 'undefined' && Streamlit.setComponentValue) {
                    Streamlit.setComponentValue({'last_move_san': move.san});
                }

                // The board position update happens in onSnapEnd
            }

            // Called after the move animation is complete
            function onSnapEnd() {
                if (!board || !game) return; // Basic check
                // Update the board position after the piece snap animation
                board.position(game.fen());
                // Ensure highlights are removed after any snap (legal or illegal)
                removeGreySquares();
            }

            // Update move history
            function updateMoveHistory(move) {
                if (!game) return; // Check game exists
                moveHistory = game.history({ verbose: true }); // Get full history from chess.js
                const historyDiv = $('#moveHistory'); // Use jQuery
                if (historyDiv.length) { // Check if element exists
                    let historyHTML = "";
                    let moveNumber = 1;
                    for (let i = 0; i < moveHistory.length; i++) {
                        if (moveHistory[i].color === 'w') {
                            historyHTML += `${moveNumber}. ${moveHistory[i].san} `;
                        } else {
                            historyHTML += `${moveHistory[i].san}<br>`;
                            moveNumber++; // Increment move number after black's move
                        }
                    }
                    // If the last move was white, add a line break placeholder if needed
                    // if (moveHistory.length > 0 && moveHistory[moveHistory.length - 1].color === 'w') {
                    //     historyHTML += ''; // Or add space
                    // }
                    historyDiv.html(historyHTML); // Use .html() with jQuery
                    historyDiv.scrollTop(historyDiv[0].scrollHeight); // Auto-scroll
                }

                // Send the move history to Streamlit
                if (typeof Streamlit !== 'undefined' && Streamlit.setComponentValue) {
                    console.log("Sending move to Streamlit.");
                    Streamlit.setComponentValue({'move_history': moveHistory});
                }
            }

            // Reset game function
            function resetGame() {
                console.log("Resetting game...");
                try {
                    game = new Chess();
                    if (board) { // Check if board was initialized
                        board.position('start'); // Resets the board visuals
                    } else {
                        console.error("Board not initialized, cannot reset position.");
                    }
                    moveHistory = []; // Clear internal history tracking
                    $('#moveHistory').html(''); // Clear display
                    $('#gameStatus').html(''); // Clear display
                    removeGreySquares(); // Ensure no highlights
                    console.log('Game reset.');
                } catch(e) {
                    console.error("Error resetting game:", e);
                }
            }

            // Undo move function
            function undoMove() {
                if (!game) return;
                const undoneMove = game.undo();
                if (undoneMove !== null) { // Check if undo was successful
                    console.log('Move undone');
                    if (board) {
                        board.position(game.fen());
                    }
                    updateMoveHistory(); // Update history display based on new game state
                    $('#gameStatus').html(''); // Clear status after undoing
                    removeGreySquares();
                } else {
                    console.log('Nothing to undo.');
                }
            }

            // Game status checking
            function checkGameStatus() {
                if (!game) return; // Check game exists
                const statusDiv = $('#gameStatus'); // Use jQuery
                let statusMsg = ''; // Build status message

                if (game.in_checkmate()) {
                    const winner = game.turn() === 'w' ? 'Black' : 'White';
                    statusMsg = `<span class="winner-text">${winner} Wins by Checkmate!</span>`;
                    // Add confetti
                    if (typeof confetti === 'function') { // Check if confetti loaded
                        confetti({ particleCount: 150, spread: 90, origin: { y: 0.6 } });
                    }
                } else if (game.in_draw()) {
                    if (game.in_stalemate()) {
                        statusMsg = "Draw by Stalemate";
                    } else if (game.in_threefold_repetition()) {
                        statusMsg = "Draw by Threefold Repetition";
                    } else if (game.insufficient_material()) {
                        statusMsg = "Draw by Insufficient Material";
                    } else if (game.in_fifty_moves()) {
                        statusMsg = "Draw by Fifty Move Rule";
                    } else {
                        statusMsg = "Draw"; // Generic draw
                    }
                } else if (game.in_check()){
                    const player = game.turn() === 'w' ? 'White' : 'Black';
                    statusMsg = `${player} is in Check!`;
                } else {
                    // Game is ongoing, no specific status needed unless you want 'White to move' etc.
                    // statusMsg = (game.turn() === 'w' ? 'White' : 'Black') + ' to move';
                    statusMsg = ''; // Keep it clean
                }
                statusDiv.html(statusMsg); // Update status display
            }
            </script>
        </body>
        </html>
        """
        # Use scrolling=True temporarily for debugging if content overflows
        components.html("""
            <script>
                console.log("🔍 Checking Streamlit in iframe...");
                console.log("window.Streamlit:", window.Streamlit);
            </script>
        """, height=0)
                
        components.html(chess_html, height=700, scrolling=True)

        # --- Try accessing 'last_move_san' directly from session state ---
        if "last_move_san" in st.session_state:
            last_move = st.session_state["last_move_san"]
            print("flag2", last_move)
            st.session_state.current_history_san.append(last_move)
            try:
                board = chess.Board(st.session_state.current_fen)
                board.push_san(last_move)
                st.session_state.current_fen = board.fen()
                print("F5", st.session_state.current_fen)
            except Exception as e:
                print(f"Error updating FEN: {e}")
            # Remove the key to prevent processing the same move multiple times
            del st.session_state["last_move_san"]
            # st.rerun() # Explicitly trigger a rerun

        # --- Try accessing 'moveHistory' directly from session state ---
        if "move_history" in st.session_state:
            print("F9")
            move_history = st.session_state["move_history"]
            # Debugging: Print the content of the session state
            print("Move History:", move_history)     

    # === Column 2: Chat Tutor ===
    with col2:
        st.markdown("### Chess Tutor")
        st.caption(f"Using {GROQ_MODEL}")

        # Container for chat history
        chat_container = st.container(height=450) # Set fixed height for scrolling
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input area
        if prompt := st.chat_input("Ask the tutor about the position..."):
            # Add user message immediately to history and display
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container: # Display new message within the container
                with st.chat_message("user"):
                    st.markdown(prompt)

            # Prepare data for LLM
            move_list_str = format_moves_for_llm(st.session_state.move_history)
            print("flag1", move_list_str)
            history_for_api = [m for m in st.session_state.messages if m["role"] != "system"]

            # Display Assistant response within the container
            with chat_container:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    with st.spinner("Analyzing..."):
                        assistant_response = get_groq_response(
                            user_prompt=prompt,
                            game_moves_str=move_list_str,
                            chat_history=history_for_api
                        )

                    # Simulate typing for better UX
                    full_response = ""
                    for chunk in assistant_response.split():
                        full_response += chunk + " "
                        time.sleep(0.03)
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)

            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            # No need to rerun here usually, the display updates automatically

        # Add a clear chat button below the input area
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.session_state.current_history_san = [] # Also clear the move history
            st.session_state.current_fen = STARTING_FEN # Reset the board to the start
            st.rerun() # Rerun to reflect the cleared chat

        # Display current move list for user reference
        with st.expander("Current Game Moves (for Tutor)"):
            # st.text(format_moves_for_llm(st.session_state.current_history_san))
            # js_result = streamlit_js_eval("window.payload", want_output=True)
            js_result = streamlit_js_eval(
                js_expressions="""
                new Promise(resolve => {
                    window.addEventListener('message', (event) => {
                        if (event.data.moveHistory) {
                            resolve(event.data.moveHistory);
                        }
                    }, { once: true });
                })
                """,
                want_output=True,
                key="get_move_history"
            )
            st.write(f"Move history: {js_result}")

# main function remains the same
def main():
    create_chess_app()

if __name__ == "__main__":
    main()