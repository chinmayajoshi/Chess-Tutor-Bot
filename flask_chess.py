from flask import Flask, render_template, request, jsonify, session
import chess
import chess.pgn
from groq import Groq
import json
import os
import atexit
import traceback
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.secret_key = os.urandom(24)  # For session management

# Initialize Groq client - replace with your API key
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
model_name = "llama-3.1-8b-instant" # "llama3-70b-8192"

# --- Configuration ---
# Set the correct path to your Stockfish executable
STOCKFISH_PATH = ".\engine\stockfish\stockfish-windows-x86-64-avx2.exe"

# Time in seconds for engine analysis (adjust as needed)
ANALYSIS_TIME_LIMIT = 0.3 

# Initialize with the correct structure expected by later functions
current_engine_analysis = {"best_score": "N/A", "top_moves": []}

# Initialize default display message  
system_prompt = "Send the first message to the AI Tutor to generate system prompt."

# Make sure STOCKFISH_PATH is correct!
if not os.path.exists(STOCKFISH_PATH):
    app.logger.info(f"WARNING: Stockfish executable not found at: {STOCKFISH_PATH:<56}")
    app.logger.info("Please install Stockfish and update STOCKFISH_PATH.")

# --- Engine Initialization & Cleanup ---
def initialize_engine():
    """Initializes the Stockfish engine process."""
    global engine
    if not os.path.exists(STOCKFISH_PATH):
        app.logger.info("Engine initialization skipped: Stockfish path invalid.")
        engine = None
        return

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        # Configure basic UCI options if needed 
        # engine.configure({"Skill Level": 10}) # Example: Adjust skill level (0-20)
        app.logger.info(f"Stockfish engine initialized successfully from: {STOCKFISH_PATH}")
        # Ensure engine is closed properly when the script exits
        atexit.register(close_engine)
    except chess.engine.EngineTerminatedError:
         app.logger.info(f"ERROR: Stockfish engine terminated unexpectedly after starting.")
         app.logger.info(f"Check if the executable at {STOCKFISH_PATH} is corrupted or incompatible.")
         engine = None
    except Exception as e:
        app.logger.info(f"ERROR: Failed to initialize Stockfish engine: {e}")
        app.logger.info(f"Traceback: {traceback.format_exc()}")
        engine = None

def close_engine():
    """Closes the engine process gracefully."""
    global engine
    if engine:
        app.logger.info("Closing Stockfish engine...")
        try:
            engine.quit()
        except chess.engine.EngineTerminatedError:
            app.logger.info("Engine already terminated.")
        except Exception as e:
            app.logger.info(f"Error closing engine: {e}")
        engine = None
    elif engine: # Engine object exists but process might be dead
        app.logger.info("Engine process was not alive. Setting engine object to None.")
        engine = None

# Initialize Stockfish 
initialize_engine()
app.logger.info(engine)

@app.route('/')
def index():
    # Initialize a new game if none exists
    if 'board_fen' not in session:
        session['board_fen'] = chess.Board().fen()
        session['move_history'] = []
        session['chat_history'] = []
    
    return render_template('index.html', 
                          board_fen=session['board_fen'],
                          move_history=session['move_history'],
                          chat_history=session['chat_history'])

@app.route('/make_move', methods=['POST'])
def make_move():
    data = request.json
    source = data.get('source')
    target = data.get('target')
    
    # Load current board state
    board = chess.Board(session['board_fen'])
    
    # Create and validate the move
    move = chess.Move.from_uci(f"{source}{target}")
    
    if move in board.legal_moves:
        # Get move in algebraic notation before making the move
        san_move = board.san(move)
        
        # Make the move
        board.push(move)
        
        # Update session
        session['board_fen'] = board.fen()
        session['move_history'] = session.get('move_history', []) + [san_move]
        
        result = {
            'success': True,
            'fen': board.fen(),
            'move': san_move,
            'is_game_over': board.is_game_over(),
            'is_check': board.is_check()
        }
        
        if board.is_game_over():
            if board.is_checkmate():
                result['game_result'] = 'Checkmate!'
            elif board.is_stalemate():
                result['game_result'] = 'Stalemate!'
            elif board.is_insufficient_material():
                result['game_result'] = 'Draw due to insufficient material!'
            else:
                result['game_result'] = 'Game over!'
    else:
        result = {'success': False, 'message': 'Invalid move'}
    
    return jsonify(result)

@app.route('/new_game', methods=['POST'])
def new_game():
    session['board_fen'] = chess.Board().fen()
    session['move_history'] = []
    
    return jsonify({
        'success': True,
        'fen': session['board_fen'],
        'move_history': session['move_history']
    })

@app.route('/undo_move', methods=['POST'])
def undo_move():
    # Load current board state
    board = chess.Board()
    
    # Replay all moves except the last one
    move_history = session.get('move_history', [])
    
    if not move_history:
        return jsonify({'success': False, 'message': 'No moves to undo'})
    
    # Remove the last move
    move_history.pop()
    
    # Replay remaining moves
    for san_move in move_history:
        board.push_san(san_move)
    
    # Update session
    session['board_fen'] = board.fen()
    session['move_history'] = move_history
    
    return jsonify({
        'success': True,
        'fen': board.fen(),
        'move_history': move_history
    })

@app.route('/get_game_status', methods=['POST'])
def get_game_status(board):
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

# --- Helper Functions ---
@app.route('/format_score', methods=['POST'])
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
    
@app.route('/get_engine_analysis', methods=['POST'])
def get_engine_analysis(current_board):
    """Runs engine analysis for top N moves on the current board position."""
    global engine, current_engine_analysis
    # Default structure in case of errors or no engine
    analysis_results = {"best_score": "Engine N/A", "top_moves": []}
    app.logger.info(engine)

    if not engine:
        app.logger.info("No engine available, trying to set up engine...")
        # Initialize Stockfish 
        initialize_engine()
    
        if not engine:
            app.logger.info("Unable to setup engine.")
            analysis_results["best_score"] = "Engine N/A" if not engine else "Engine Dead"
            current_engine_analysis = analysis_results
            return current_engine_analysis
        else: app.logger.info("Engine set up successfully.")

    try:
        app.logger.info("F1")
        # Request top 3 variations (MultiPV)
        infos = engine.analyse(
            current_board,
            chess.engine.Limit(time=ANALYSIS_TIME_LIMIT),
            multipv=3
        )

        if not isinstance(infos, list): # Ensure we have a list
            infos = [infos]
            app.logger.info("F1")

        if not infos:
            analysis_results["best_score"] = "No analysis"
            current_engine_analysis = analysis_results
            app.logger.info("F1")

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
                        app.logger.info(f"Error getting SAN for move {move}: {e}")
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

        app.logger.info("F2", processed_moves)
        analysis_results["top_moves"] = processed_moves
        current_engine_analysis = analysis_results
        return current_engine_analysis

    except chess.engine.EngineTerminatedError:
        app.logger.info("ERROR: Engine terminated during analysis.")
        close_engine() # Try to cleanup
        analysis_results["best_score"] = "Engine Died"
        current_engine_analysis = analysis_results
        return current_engine_analysis
    except Exception as e:
        app.logger.info(f"ERROR: Engine analysis failed: {e}")
        app.logger.info(f"Traceback: {traceback.format_exc()}")
        analysis_results["best_score"] = "Analysis Error"
        # Keep empty list structure for top_moves on error
        analysis_results["top_moves"] = []
        current_engine_analysis = analysis_results
        return current_engine_analysis

@app.route('/ask_tutor', methods=['POST'])
def ask_tutor():
    app.logger.info("Generating tutor response...")
    data = request.json
    user_message = data.get('message', '')
    
    # Load current board state
    board = chess.Board(session['board_fen'])
    move_history = session.get('move_history', [])
    turn = "White" if board.turn == chess.WHITE else "Black"

    # Get current engine analysis
    current_engine_analysis = get_engine_analysis(board)

    # Ensure engine analysis is available
    if not current_engine_analysis or "top_moves" not in current_engine_analysis:
         app.logger.info("Analysis missing for AI prompt, recalculating...")

    # Format the top N engine moves for the prompt
    engine_suggestions_list = []
    if current_engine_analysis and current_engine_analysis.get("top_moves"):
        for i, move_info in enumerate(current_engine_analysis["top_moves"]):
            # Ensure values exist before accessing
            san = move_info.get('move_san', 'N/A')
            score = move_info.get('score', 'N/A')
            engine_suggestions_list.append(f"  {i+1}. {san} ({score})")
    if not engine_suggestions_list: # Add placeholder if list is empty
        engine_suggestions_list.append("No engine moves found.")

    engine_suggestions_str = "\n".join(engine_suggestions_list)
    engine_best_score_str = current_engine_analysis.get("best_score", "N/A")

    board_unicode = board.unicode()
    board_rows = board_unicode.split('\n')
    ranks = ".....a...b...c...d...e...f...g...h<br>"
    board_unicode_str = ["|"+ranks] + [f"| {8-i}: {board_rows[i]}<br>" for i in range(len(board_rows))] + ["|"+ranks]
        
    system_prompt = f"""You are a helpful and friendly chess tutor observing a game.
Your goal is to help the user understand the current chess position resulting from the game's moves so far. \
Explain potential threats, opportunities, and general strategic ideas for the player whose turn it is. \
Avoid just giving the 'best' move. Keep explanations concise for a beginner/intermediate player. \
Keep your responses to under 200 words, unless the user asks for a longer response.\
DO NOT TALK about `Stockfish` or `chess engine evaluation scores` unless users asks directly.\

<br><br>
### Current Position (FEN):<br>
{board.fen()}

<br>
### Move History:<br>
{chr(10).join(move_history) if move_history else 'No moves yet.'}

<br>
### Current Game State:<br>
- {turn} to move
- Status: {get_game_status(board)}

<br>
### Board:<br>
{"".join(board_unicode_str)}

<br>
### Engine Analysis (Stockfish ~{ANALYSIS_TIME_LIMIT}s - Top 3):<br>
- Best Move Score: {engine_best_score_str} (Score relative to White: + favors White, - favors Black. M=Mate)<br>
- Top 3 Suggested Moves (Score):<br>
{engine_suggestions_str})<br>

Based on this context and the user's question below, provide thoughtful chess analysis. Explain key positional elements, threats, potential plans, and the reasoning behind good moves (including why the engine might suggest certain lines). Do not just repeat the engine moves; offer explanations and alternatives.
"""

    # Save system prompt in session
    session['system_prompt'] = system_prompt

    # Get chat history and add user message
    chat_history = session.get('chat_history', [])
    chat_history.append({"role": "user", "content": user_message})
    
    # Call Groq API
    try:
        response = groq_client.chat.completions.create(
            model=model_name,  # Use appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        tutor_response = response.choices[0].message.content
        
        # Add assistant response to chat history
        chat_history.append({"role": "assistant", "content": tutor_response})
        session['chat_history'] = chat_history
        session['system_prompt'] = system_prompt
        
        return jsonify({
            'success': True,
            'response': tutor_response,
            'chat_history': chat_history
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=True)