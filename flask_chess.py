from flask import Flask, render_template, request, jsonify, session
import chess
import chess.pgn
from groq import Groq
import json
import os
import atexit
import traceback
import logging
import webbrowser

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.secret_key = os.urandom(24)  # For session management

# Initialize Groq client - replace with your API key
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
model_name = "deepseek-r1-distill-llama-70b" # "gemma2-9b-it"

# --- Configuration ---
# Set the correct path to your Stockfish executable
# STOCKFISH_PATH = ".\engine\stockfish\stockfish-windows-x86-64-avx2.exe"
STOCKFISH_PATH = ".\engine\stockfish\stockfish-ubuntu-x86-64-avx2"

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
        session['stockfish_eval'] = get_board_eval(chess.Board(session['board_fen']))
        session['system_prompt'] = "Ask a question to the AI Tutor to generate the system prompt."
    
    return render_template('index.html', 
                          board_fen=session['board_fen'],
                          move_history=session['move_history'],
                          chat_history=session['chat_history'],
                          system_prompt=session['system_prompt'],
                          stockfish_eval=session['stockfish_eval'])

@app.route('/make_move', methods=['POST'])
def make_move():
    data = request.json
    source = data.get('source')
    target = data.get('target')
    
    # Load current board state
    board = chess.Board(session['board_fen'])
    
    # Create and validate the move
    move = chess.Move.from_uci(f"{source}{target}")
    try:
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

            
            result['stockfish_eval'] = get_board_eval(board)
            session['stockfish_eval'] = result['stockfish_eval']
            
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
    except Exception as e:
        result = {'success': False, 'message': f'Error making move: {e}'}
        app.logger.error(f"Error making move: {e}")
    
    return jsonify(result)

@app.route('/new_game', methods=['POST'])
def new_game():
    session['board_fen'] = chess.Board().fen()
    session['move_history'] = []
    session['chat_history'] = []
    session['system_prompt'] = "Ask a question to the AI Tutor to generate the system prompt."
    
    return jsonify({
        'success': True,
        'fen': session['board_fen'],
        'move_history': session['move_history'],
        'system_prompt': session['system_prompt'],
        'stockfish_eval': session['stockfish_eval']
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
    session['stockfish_eval'] = get_board_eval(board)
    
    return jsonify({
        'success': True,
        'fen': board.fen(),
        'move_history': move_history,
        'system_prompt': session['system_prompt'],
        'stockfish_eval': session['stockfish_eval']
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
    
@app.route('/board_eval_score', methods=['POST'])
def get_board_eval(current_board):
    """Analyzes current board position and returns top line engine evaluation."""
    global engine, current_engine_analysis

    eval_score = "N/A"

    # Engine initialization logic
    if not engine:
        app.logger.info("No engine available, trying to set up engine...")
        initialize_engine()
        if not engine:
            app.logger.info("Unable to setup engine.")
        else: 
            app.logger.info("Engine set up successfully.")

    try:
        # Request analysis with Stockfish
        app.logger.info("Requesting engine analysis...")
        infos = engine.analyse(
            current_board,
            chess.engine.Limit(time=ANALYSIS_TIME_LIMIT),
            multipv=1  # Get top 1 line
        )

        if not isinstance(infos, list):
            infos = [infos]

        app.logger.info(f"Formating score...")
        eval_score = format_score(infos[0]['score'].white())
        # eval_score = format_score(infos[0])
    except Exception as e:
        app.logger.info(f"Error during engine evaluation: {e}")

    return eval_score

@app.route('/get_engine_analysis', methods=['POST'])
def get_engine_analysis(current_board):
    """Analyzes current position and returns top 3 lines with up to 4 moves each."""
    global engine, current_engine_analysis
    analysis_results = {"best_score": "Engine N/A", "top_moves": []}

    # Engine initialization logic
    if not engine:
        app.logger.info("No engine available, trying to set up engine...")
        initialize_engine()
        if not engine:
            app.logger.info("Unable to setup engine.")
            analysis_results["best_score"] = "Engine Dead" if engine else "Engine N/A"
            current_engine_analysis = analysis_results
            return current_engine_analysis
        else: 
            app.logger.info("Engine set up successfully.")

    try:
        # Request analysis with MultiPV
        infos = engine.analyse(
            current_board,
            chess.engine.Limit(time=ANALYSIS_TIME_LIMIT),
            multipv=3  # Get top 3 lines
        )

        if not isinstance(infos, list):
            infos = [infos]

        processed_lines = []
        for i, info in enumerate(infos):
            # Score processing
            score_obj = info.get("score")
            if not score_obj:
                continue
            white_score = score_obj.white()
            formatted_score = format_score(white_score)

            # Process principal variation (PV)
            move_line = []
            temp_board = current_board.copy()
            
            # Extract up to 4 moves from PV
            for move_in_pv in info.get("pv", [])[:4]:  # Limit to first 4 moves
                try:
                    if not temp_board.is_legal(move_in_pv):
                        break
                    
                    san = temp_board.san(move_in_pv)
                    move_line.append(san)
                    temp_board.push(move_in_pv)  # Update board state
                except Exception as e:
                    app.logger.error(f"Error processing move {move_in_pv}: {e}")
                    break

            if move_line:  # Only add lines with valid moves
                processed_lines.append({
                    "score": formatted_score,
                    "move_line": move_line
                })

            # Set best score from top line
            if i == 0 and processed_lines:
                analysis_results["best_score"] = formatted_score

        analysis_results["top_moves"] = processed_lines[:3]  # Ensure max 3 lines
        current_engine_analysis = analysis_results
        return current_engine_analysis

    except chess.engine.EngineTerminatedError:
        app.logger.error("Engine terminated during analysis")
        close_engine()
        analysis_results["best_score"] = "Engine Died"
        return analysis_results
    except Exception as e:
        app.logger.error(f"Analysis failed: {str(e)}")
        app.logger.debug(traceback.format_exc())
        analysis_results["best_score"] = "Analysis Error"
        return analysis_results

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

    # Format the top N engine lines for the prompt
    engine_suggestions_list = []
    if current_engine_analysis and current_engine_analysis.get("top_moves"):
        for i, line_info in enumerate(current_engine_analysis["top_moves"]):
            # Get move sequence and score
            move_sequence = line_info.get('move_line', [])
            score = line_info.get('score', 'N/A')
            
            # Format moves as "e4, e5, Nf3"
            moves_str = ", ".join(move_sequence) if move_sequence else '(no moves)'
            
            engine_suggestions_list.append(f"### Move Lines {i+1}: {moves_str} ({score})<br>")
            
    if not engine_suggestions_list:  # Add placeholder if empty
        engine_suggestions_list.append("No engine analysis available.")


    engine_suggestions_str = "\n".join(engine_suggestions_list)
    engine_best_score_str = current_engine_analysis.get("best_score", "N/A")

    board_unicode = board.unicode()
    board_rows = board_unicode.split('\n')
    board_rows = board_rows[::-1]
    # ranks = ".....a...b...c...d...e...f...g...h<br>"
    # board_unicode_str = ["|"+ranks] + [f"| {i+1}: {board_rows[i]}<br>" for i in range(len(board_rows))] + ["|"+ranks]
        
    ranks = "| | a | b | c | d | e | f | g | h | |<br>"
    table_divider = "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |<br>"
    board_unicode_str = [f"| {i+1} | {' | '.join(board_rows[i].replace(' ', ''))}| {i+1} |<br>" for i in range(len(board_rows))]
    board_unicode_str = [ranks] + [table_divider] + board_unicode_str + [ranks]

    system_prompt = f"""You are a helpful and friendly chess tutor observing a game.
Your goal is to help the user understand the current chess position resulting from the game's moves so far. \
Explain potential threats, opportunities, and general strategic ideas for the player whose turn it is. \
Avoid just giving the 'best' move. Keep explanations concise for a beginner/intermediate player. \
Keep your responses to under 100 words, unless the user asks for a longer response. \
DO NOT TALK about `Stockfish` or `chess engine evaluation scores` unless users asks directly.\

<br><br>
# Current Position (FEN):<br>
{board.fen()}

<br><br>
# Move History:<br>
{chr(10).join(move_history) if move_history else 'No moves yet.'}

<br><br>
# Current Game State:<br>
- {turn} to move
- Status: {get_game_status(board)}

<br><br>
# Board:<br>
{"".join(board_unicode_str)}

<br>
Whenever looking at where a particular piece is, check with this board unicode. If the piece is missing, it's not there.
- ♖ = white rook
- ♘ = white knight
- ♗ = white bishop
- ♕ = white queen
- ♔ = white king
- ♙ = black pawn
- ♟ = black pawn
- ♜ = black rook
- ♞ = black knight
- ♝ = black bishop
- ♛ = black queen
- ♚ = black king
- ⭘ = empty square

<br><br>
# Chess Engine Analysis (Stockfish ~{ANALYSIS_TIME_LIMIT}s - Top 3):<br>
## Stockfish Chess Engine gives the BEST MOVES. ALWAYS stick to these moves (especially top Line-1 moves) as advice (UNLESS USERS SPECIFIES OTHERWISE).<br>
## Best Move Score: {engine_best_score_str} (Score relative to White: + favors White, - favors Black. M=Mate)<br>
## Top 3 BEST MOVE LINES below (Higher Scores are better for white):<br>
{engine_suggestions_str}<br><br>

---
<br><br>

Based on this context, the engine analysis and top best move lines, and the user's question below- provide thoughtful and accurate chess advice for the position. \
Explain key positional elements, threats, potential plans, and the reasoning behind good moves (including why the engine might suggest certain lines). \
For eg. if the top engine suggests a move, is it because it improves the position? Does that move save a piece from a current threat? Does that move build an attack? etc.
Do not just repeat the engine moves; offer explanations and alternatives.
"""

    # Get chat history and add user message
    chat_history = session.get('chat_history', [])
    chat_history.append({"role": "user", "content": user_message})
    
    # Call Groq API
    try:       
        # Prepare messages for Groq API (without custom fields)
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            if msg['role'] == 'user':
                api_messages.append({"role": "user", "content": msg['content']})
            else:
                # For assistants, use the original undivided content
                api_messages.append({"role": "assistant", "content": msg['content']})

        # Call Groq API
        response = groq_client.chat.completions.create(
            model=model_name, 
            messages=api_messages,
            temperature=0,
            max_tokens=1024
        )
        
        tutor_response = response.choices[0].message.content
        if "<think>" in tutor_response:
            app.logger.info("1")
            tutor_response_split = tutor_response.split("<think>")[1].split("</think>")
            tutor_response_think = tutor_response_split[0]
            if len(tutor_response_split) > 1:
                app.logger.info("2")
                tutor_response_main = tutor_response_split[1]
            else:
                app.logger.info("3")
                tutor_response_main = tutor_response
        else:
            app.logger.info("4")
            tutor_response_think = ""
            tutor_response_main = tutor_response
        
        # Add assistant response to chat history
        chat_history.append({
            "role": "assistant",
            "content": tutor_response,
            "think": tutor_response_think,
            "main": tutor_response_main
        })
        session['chat_history'] = chat_history
        
        # Save system prompt in session
        session['system_prompt'] = system_prompt
        
        return jsonify({
            'success': True,
            'reasoning': tutor_response_think,
            'response': tutor_response_main,
            'chat_history': chat_history,
            'system_prompt': system_prompt
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        })

if __name__ == '__main__':
    # webbrowser.open_new('http://127.0.0.1:2000/')
    # app.run(debug=True, port=2000)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)