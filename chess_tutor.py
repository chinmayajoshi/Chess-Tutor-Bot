import os
import gradio as gr
import chess
import chess.svg
import chess.engine
from groq import Groq
import atexit
import traceback # For detailed error logging

# --- Configuration ---
# Set the correct path to your Stockfish executable
STOCKFISH_PATH = ".\engine\stockfish\stockfish-windows-x86-64-avx2.exe"

# Make sure STOCKFISH_PATH is correct!
if not os.path.exists(STOCKFISH_PATH):
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"!!! WARNING: Stockfish executable not found at:           !!!")
    print(f"!!! {STOCKFISH_PATH:<56} !!!")
    print(f"!!! Engine features will be disabled.                     !!!")
    print(f"!!! Please install Stockfish and update STOCKFISH_PATH.   !!!")
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# Time in seconds for engine analysis (adjust as needed)
ANALYSIS_TIME_LIMIT = 0.3 

# Set up Groq client (ensure GROQ_API_KEY environment variable is set)
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    # Test API environment variable 
    if not os.environ.get("GROQ_API_KEY"):
         raise ValueError("GROQ_API_KEY environment variable not set.")
    
except Exception as e:
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"!!! WARNING: Failed to initialize Groq client.            !!!")
    print(f"!!! AI Tutor features will likely fail.                   !!!")
    print(f"!!! Error: {e}                                            !!!")
    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    client = None # Prevent errors later if client is used when None

# --- Global variables ---
board = chess.Board()
move_history = []
engine = None
# Initialize with the correct structure expected by later functions
current_engine_analysis = {"best_score": "N/A", "top_moves": []}

# --- Engine Initialization & Cleanup ---
def initialize_engine():
    """Initializes the Stockfish engine process."""
    global engine
    if not os.path.exists(STOCKFISH_PATH):
        print("Engine initialization skipped: Stockfish path invalid.")
        engine = None
        return

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        # Configure basic UCI options if needed 
        # engine.configure({"Skill Level": 10}) # Example: Adjust skill level (0-20)
        print(f"Stockfish engine initialized successfully from: {STOCKFISH_PATH}")
        # Ensure engine is closed properly when the script exits
        atexit.register(close_engine)
    except chess.engine.EngineTerminatedError:
         print(f"ERROR: Stockfish engine terminated unexpectedly after starting.")
         print(f"Check if the executable at {STOCKFISH_PATH} is corrupted or incompatible.")
         engine = None
    except Exception as e:
        print(f"ERROR: Failed to initialize Stockfish engine: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        engine = None

def close_engine():
    """Closes the engine process gracefully."""
    global engine
    if engine:
        print("Closing Stockfish engine...")
        try:
            engine.quit()
        except chess.engine.EngineTerminatedError:
            print("Engine already terminated.")
        except Exception as e:
            print(f"Error closing engine: {e}")
        engine = None
    elif engine: # Engine object exists but process might be dead
        print("Engine process was not alive. Setting engine object to None.")
        engine = None


# --- Helper Functions ---
def format_score(score_obj):
    """Formats the engine's chess.engine.Score object for display."""
    if score_obj is None:
        return "N/A"
    if score_obj.is_mate():
        mate_in = score_obj.mate()
        # Show mate from the perspective of the side delivering mate
        return f"Mate in {abs(mate_in)}"
    else:
        # Score from White's perspective (+ favors White, - favors Black)
        # Use mate_score to prevent extreme values if mate is near but not forced
        cp = score_obj.score(mate_score=10000)
        if cp is None: # Handle cases where score calculation might fail
             return "N/A"
        pawn_units = cp / 100.0
        return f"Stockfish Evaluation: {pawn_units:+.2f}" # Format like +1.23 or -0.50

def get_board_svg():
    """Generates SVG of the current board with the last move highlighted."""
    last_move = board.peek() if board.move_stack else None
    try:
        return chess.svg.board(board=board, size=400, lastmove=last_move)
    except Exception as e:
        print(f"Error generating board SVG: {e}")
        return f"<p>Error generating board: {e}</p>" # Return HTML error

def get_game_status():
    """Determines and returns the current game status string."""
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate! {winner} wins!"
    elif board.is_stalemate():
        return "Stalemate! Draw."
    elif board.is_insufficient_material():
        return "Draw: Insufficient Material."
    elif board.is_seventyfive_moves():
        return "Draw: 75-move rule."
    elif board.is_fivefold_repetition():
        return "Draw: Fivefold Repetition."
    elif board.is_variant_draw(): # Handles other draw types if applicable
        return "Draw."
    elif board.is_check():
        turn_str = "White" if board.turn == chess.WHITE else "Black"
        return f"{turn_str} to move (in Check)"
    else:
        turn_str = "White" if board.turn == chess.WHITE else "Black"
        return f"{turn_str} to move"

# --- Core Logic Functions ---

def get_engine_analysis(current_board):
    """Runs engine analysis for top N moves on the current board position."""
    global engine, current_engine_analysis
    # Default structure in case of errors or no engine
    analysis_results = {"best_score": "Engine N/A", "top_moves": []}

    if not engine:
        analysis_results["best_score"] = "Engine N/A" if not engine else "Engine Dead"
        current_engine_analysis = analysis_results
        return current_engine_analysis

    try:
        # Request top 3 variations (MultiPV)
        infos = engine.analyse(
            current_board,
            chess.engine.Limit(time=ANALYSIS_TIME_LIMIT),
            multipv=3
        )

        if not isinstance(infos, list): # Ensure we have a list
             infos = [infos]

        if not infos:
            analysis_results["best_score"] = "No analysis"
            current_engine_analysis = analysis_results
            return current_engine_analysis

        processed_moves = []
        for i, info in enumerate(infos):
            # Score from White's perspective
            score_obj = info.get("score")
            if score_obj is None: continue # Skip if score is missing
            white_score = score_obj.white()
            formatted_score = format_score(white_score)

            best_move = None
            move_san = "N/A"

            if "pv" in info and info["pv"]:
                move = info["pv"][0]
                if move in current_board.legal_moves:
                    try:
                        move_san = current_board.san(move)
                        best_move = move
                    except Exception as e:
                        print(f"Error getting SAN for move {move}: {e}")
                        move_san = "Error"
                else:
                     # Engine suggested an illegal move (can happen at low depth/time)
                     move_uci = "N/A"
                     try: # Try getting UCI even if illegal, for context
                         move_uci = current_board.uci(move)
                     except: pass
                     move_san = f"Invalid ({move_uci})"

            processed_moves.append({
                "score": formatted_score,
                "move_san": move_san,
                # Store UCI in case SAN fails or for other uses
                "move_uci": current_board.uci(best_move) if best_move else "N/A"
            })

            if i == 0: # Set the best score from the top result
                analysis_results["best_score"] = formatted_score

        analysis_results["top_moves"] = processed_moves
        current_engine_analysis = analysis_results
        return current_engine_analysis

    except chess.engine.EngineTerminatedError:
        print("ERROR: Engine terminated during analysis.")
        close_engine() # Try to cleanup
        analysis_results["best_score"] = "Engine Died"
        current_engine_analysis = analysis_results
        return current_engine_analysis
    except Exception as e:
        print(f"ERROR: Engine analysis failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        analysis_results["best_score"] = "Analysis Error"
        # Keep empty list structure for top_moves on error
        analysis_results["top_moves"] = []
        current_engine_analysis = analysis_results
        return current_engine_analysis


def update_ui_state():
    """Updates all relevant UI components based on the current board state."""
    global board, move_history
    svg = get_board_svg()
    history_str = "\n".join(move_history)
    status = get_game_status()
    # Get new analysis (includes top_moves list and best_score)
    analysis = get_engine_analysis(board)
    # Extract the score of the BEST move for the main display
    score_str = analysis.get("best_score", "N/A")

    # Return updates for the UI components defined in common_outputs
    return svg, history_str, status, score_str

def make_move(from_square, to_square):
    """Processes a chess move, updates state, and returns UI updates."""
    global board, move_history

    # Basic validation of input format
    if not from_square or not to_square or len(from_square) != 2 or len(to_square) != 2:
         print(f"Invalid input format: from='{from_square}', to='{to_square}'")
         # Return current state with an error message
         svg, history_str, _, score_str = update_ui_state() # Get current state
         return svg, history_str, "Invalid input format (e.g., 'e2')", score_str

    try:
        from_sq_str = from_square.lower()
        to_sq_str = to_square.lower()
        from_sq = chess.parse_square(from_sq_str)
        to_sq = chess.parse_square(to_sq_str)

        # Determine if promotion is possible and set to Queen by default
        promotion = None
        piece = board.piece_type_at(from_sq)
        if piece == chess.PAWN:
            rank = chess.square_rank(to_sq)
            is_white_promo = (board.turn == chess.WHITE and rank == 7)
            is_black_promo = (board.turn == chess.BLACK and rank == 0)
            if is_white_promo or is_black_promo:
                promotion = chess.QUEEN

        move = chess.Move(from_sq, to_sq, promotion=promotion)

        if move in board.legal_moves:
            san_move = board.san(move)
            board.push(move)

            # Format move history entry
            move_color = "White" if board.turn == chess.BLACK else "Black" # Player who just moved
            move_number_str = ""
            if move_color == "White":
                 move_number_str = f"{board.fullmove_number}. "
            else:
                 # Add ellipsis for Black's move if it's not the first move
                 if board.fullmove_number > 1 or len(move_history) > 0:
                      move_number_str = f"{board.fullmove_number}... "
                 else: # Black's first move, just use number
                      move_number_str = f"{board.fullmove_number}. "


            move_history.append(f"{move_number_str}{san_move}")

            # Return the full updated UI state after successful move
            return update_ui_state()
        else:
            # Illegal move attempted, return current state with message
            print(f"Illegal move attempt: {from_sq_str}{to_sq_str}")
            svg, history_str, _, score_str = update_ui_state() # Get current state
            return svg, history_str, f"Illegal move: {from_sq_str}{to_sq_str}", score_str

    except ValueError: # Handles errors from parse_square
         print(f"Invalid square format: from='{from_square}', to='{to_square}'")
         svg, history_str, _, score_str = update_ui_state() # Get current state
         return svg, history_str, "Invalid square format (use e.g., 'e2', 'h8')", score_str
    except Exception as e:
         print(f"ERROR during move execution: {e}")
         print(f"Traceback: {traceback.format_exc()}")
         svg, history_str, status, score_str = update_ui_state() # Get current state
         return svg, history_str, f"Error: {str(e)}", score_str


def new_game():
    """Resets the board, history, and returns the updated UI state."""
    global board, move_history, current_engine_analysis
    print("Starting new game...")
    board = chess.Board()
    move_history = []
    # Reset analysis, it will be recalculated by update_ui_state
    current_engine_analysis = {"best_score": "N/A", "top_moves": []}
    # Return the full updated UI state for the new game
    return update_ui_state()

def undo_move():
    """Undoes the last move and returns the updated UI state."""
    global board, move_history, current_engine_analysis
    if board.move_stack:
        print("Undoing last move...")
        board.pop()
        if move_history:
            move_history.pop()
        # Reset analysis, it will be recalculated
        current_engine_analysis = {"best_score": "N/A", "top_moves": []}
        # Return the full updated UI state
        return update_ui_state()
    else:
        print("Undo failed: No moves to undo.")
        # No moves to undo, return current state with message
        svg, history_str, _, score_str = update_ui_state() # Get current state
        return svg, history_str, "No moves to undo", score_str

def get_ai_analysis(message, chat_history):
    """Gets analysis from Groq AI, including engine context in the prompt."""
    global board, move_history, current_engine_analysis, client

    if not message.strip():
        print("AI analysis request skipped: Empty message.")
        return "", chat_history # Return empty input, unchanged history

    if not client:
        print("AI analysis failed: Groq client not initialized.")
        # Return error message in chat
        error_msg = "ERROR: AI Service client not available."
        chat_history = chat_history or []
        chat_history.append([message, error_msg])
        return "", chat_history

    # Ensure engine analysis is available
    if not current_engine_analysis or "top_moves" not in current_engine_analysis:
         print("Analysis missing for AI prompt, recalculating...")
         get_engine_analysis(board)

    # Format the top N engine moves for the prompt
    engine_suggestions_list = []
    if current_engine_analysis and current_engine_analysis.get("top_moves"):
        for i, move_info in enumerate(current_engine_analysis["top_moves"]):
            # Ensure values exist before accessing
            san = move_info.get('move_san', 'N/A')
            score = move_info.get('score', 'N/A')
            engine_suggestions_list.append(f"  {i+1}. {san} ({score})")
    if not engine_suggestions_list: # Add placeholder if list is empty
        engine_suggestions_list.append("  No engine moves found.")

    engine_suggestions_str = "\n".join(engine_suggestions_list)
    engine_best_score_str = current_engine_analysis.get("best_score", "N/A")

    # Prepare system prompt
    turn = "White" if board.turn == chess.WHITE else "Black"
    system_prompt = f"""You are a helpful and friendly chess tutor observing a game.
Your goal is to help the user understand the current chess position resulting from the game's moves so far. \
Explain potential threats, opportunities, and general strategic ideas for the player whose turn it is. \
Avoid just giving the 'best' move. Keep explanations concise for a beginner/intermediate player. \
Keep your responses to under 200 words, unless the user asks for a longer response.\
DO NOT TALK about Stockfish and the engine evaluation scores unless users asks specifically.\

Current Position (FEN):
{board.fen()}

Move History:
{chr(10).join(move_history) if move_history else 'No moves yet.'}

Current Game State:
- {turn} to move
- Status: {get_game_status()}

Engine Analysis (Stockfish ~{ANALYSIS_TIME_LIMIT}s - Top 3):
- Best Move Score: {engine_best_score_str} (Score relative to White: + favors White, - favors Black. M=Mate)
- Top 3 Suggested Moves (Score):
{engine_suggestions_str}

Based on this context and the user's question below, provide thoughtful chess analysis. Explain key positional elements, threats, potential plans, and the reasoning behind good moves (including why the engine might suggest certain lines). Do not just repeat the engine moves; offer explanations and alternatives.
"""

    # Format chat history for Groq API
    formatted_history = []
    if chat_history: # Check if history exists
        for item in chat_history:
            # Expecting item = [user_msg, assistant_response]
            if isinstance(item, (list, tuple)) and len(item) == 2:
                # Add messages ensuring content is string
                formatted_history.append({"role": "user", "content": str(item[0])})
                formatted_history.append({"role": "assistant", "content": str(item[1])})
            else:
                 print(f"WARNING: Skipping malformed history item: {item}")

    try:
        print(f"Sending request to AI for: '{message[:50]}...'")
        messages_to_send = [
             {"role": "system", "content": system_prompt},
             *formatted_history,
             {"role": "user", "content": message}
         ]

        chat_completion = client.chat.completions.create(
            messages=messages_to_send,
            model="llama-3.1-8b-instant" # Or consider "llama3-70b-8192" for potentially deeper analysis
            # model="llama3-8b-8192" # Standard Llama3 8b
            # Add parameters like temperature if desired: temperature=0.7
        )
        response = chat_completion.choices[0].message.content
        print("AI response received.")
        # Append the new exchange to chat history for Gradio display
        # Ensure chat_history is initialized if it was None
        chat_history = chat_history or []
        chat_history.append([message, response])

    except Exception as e:
        print(f"ERROR: Failed to get AI analysis: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        error_message = f"Error communicating with AI Tutor: {str(e)}"
        # Append user message and error message to history
        chat_history = chat_history or []
        chat_history.append([message, error_message])

    # Clear the input message box, update the chatbot display
    return "", chat_history


# --- Gradio Interface Definition ---
initialize_engine() # Initialize the engine when the script starts

# Get initial UI state *after* initializing engine (which might populate analysis)
initial_svg, initial_history, initial_status, initial_score = update_ui_state()

with gr.Blocks(css="""
    #board_container {
        width: 400px; height: 400px; margin: 10px auto; position: relative;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1); /* Add subtle shadow */
    }
    #engine_score_display {
        text-align: center !important; font-size: 1.1em !important; font-weight: bold !important;
        margin-bottom: 8px !important; color: #333 !important; padding: 4px !important;
        border: none !important; background: none !important;
    }
    #engine_score_display p { margin: 0 !important; padding: 0 !important; }
    .status-text { font-weight: bold; padding: 5px; border-radius: 4px;}
    .move-input input { text-align: center; } /* Center text in move inputs */
    .history-display textarea { font-family: monospace; font-size: 0.9em; } /* Monospace font for history */
""", title="Chess Tutor AI") as app:

    gr.Markdown("## Chess Tutor with AI Analysis & Engine Eval")

    with gr.Row():
        # --- Left Column: Board, Controls, History ---
        with gr.Column(scale=2):
            # Engine Score Display (using Markdown)
            score_display = gr.Markdown(
                value=initial_score,
                label=None,
                elem_id="engine_score_display"
            )

            # Chess Board
            with gr.Column(elem_id="board_container"):
                 board_display = gr.HTML(initial_svg) # Display the SVG board

            # Move Input
            with gr.Row(elem_classes="move-input"):
                input_from = gr.Textbox(label="From", placeholder="move from (eg. e2)", scale=1, max_lines=1, container=False)
                input_to = gr.Textbox(label="To", placeholder="move to (eg. e4)", scale=1, max_lines=1, container=False)
                submit_move = gr.Button("Make Move", scale=1, variant="primary", min_width=100)

            # Control Buttons
            with gr.Row():
                new_game_btn = gr.Button("New Game")
                undo_btn = gr.Button("Undo Move")

            # Status Display
            status_display = gr.Textbox(
                label="Game Status",
                value=initial_status,
                interactive=False,
                elem_classes="status-text" # Apply styling
            )

            # Move History
            history_display = gr.TextArea(
                label="Move History",
                value=initial_history,
                interactive=False,
                lines=10,
                max_lines=20,
                elem_classes="history-display" # Apply styling
            )

        # --- Right Column: AI Chat ---
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Chess Tutor AI", height=550) # Increased height
            msg_input = gr.Textbox(
                label="Ask the AI Tutor",
                placeholder="e.g., What should I focus on? Why is Nf3 a good move?",
                lines=2,
                interactive=True
                )
            with gr.Row():
                send_btn = gr.Button("Send to AI", variant="secondary")
                clear_btn = gr.Button("Clear Chat")

    # --- Event Handlers ---
    # Define outputs updated by board changes (move, undo, new game)
    common_outputs = [board_display, history_display, status_display, score_display]

    # Handle making a move
    submit_move.click(
        make_move,
        inputs=[input_from, input_to],
        outputs=common_outputs
    ).then(lambda: ("", ""), outputs=[input_from, input_to]) # Clear input fields after attempt

    # Handle starting a new game
    new_game_btn.click(
        new_game,
        inputs=None,
        outputs=common_outputs
    # Clear chat and AI input on new game
    ).then(lambda: ([], ""), outputs=[chatbot, msg_input])

    # Handle undoing a move
    undo_btn.click(
        undo_move,
        inputs=None,
        outputs=common_outputs
    )

    # --- AI Chat Interactions ---
    # Handle pressing Enter in the message input box
    msg_input.submit(
        get_ai_analysis,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot] # Clears input, updates chat
        )

    # Handle clicking the "Send to AI" button
    send_btn.click(
        get_ai_analysis,
        inputs=[msg_input, chatbot],
        outputs=[msg_input, chatbot] # Clears input, updates chat
        )

    # Handle clearing the chat
    clear_btn.click(lambda: ([], None), None, [chatbot, msg_input]) # Clears chat and input box

# --- Launch the App ---
if __name__ == "__main__":
    print("Starting Gradio app...")
    try:
        # Set share=True if you need to access it from another device on your network
        # or want a temporary public link for debugging.
        app.launch(share=False)
    except Exception as e:
         print(f"ERROR launching Gradio app: {e}")
         print(f"Traceback: {traceback.format_exc()}")
    finally:
        # Ensure engine is closed when app stops (including crashes)
        print("Gradio app closing...")
        close_engine()