import os
import gradio as gr
import chess
import chess.pgn
import json
from groq import Groq
import chess.svg
import cairosvg
import io
from PIL import Image
import numpy as np

# Initialize the Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Initialize a chess board
board = chess.Board()
move_history = []

# Function to render the chess board as an image
def render_board_image():
    global board
    svg = chess.svg.board(board=board, size=400)
    png_data = cairosvg.svg2png(bytestring=svg.encode('utf-8'))
    img = Image.open(io.BytesIO(png_data))
    return np.array(img)

def make_move(fen, source, target, promotion="q"):
    """Make a move on the chess board"""
    global board, move_history
    
    # Parse the FEN string to update the board
    if fen:
        board.set_fen(fen)
    
    # Create the move
    move = chess.Move.from_uci(f"{source}{target}{promotion if promotion else ''}")
    
    # Check if move is legal
    if move in board.legal_moves:
        # Store the position before the move
        previous_position = board.fen()
        
        # Make the move
        san_move = board.san(move)
        board.push(move)
        
        # Add to move history
        move_number = (len(move_history) // 2) + 1
        if len(move_history) % 2 == 0:
            move_history.append(f"{move_number}. {san_move}")
        else:
            move_history.append(f"{move_number}... {san_move}")
        
        # Check if game is over
        game_status = get_game_status()
        
        return {
            "fen": board.fen(),
            "history": " ".join(move_history),
            "game_status": game_status
        }
    else:
        # Return the current state if move is illegal
        return {
            "fen": board.fen(),
            "history": " ".join(move_history),
            "game_status": get_game_status()
        }

def get_game_status():
    """Get the current status of the game"""
    if board.is_checkmate():
        return "Checkmate! " + ("Black" if board.turn == chess.WHITE else "White") + " wins."
    elif board.is_stalemate():
        return "Draw by stalemate."
    elif board.is_insufficient_material():
        return "Draw due to insufficient material."
    elif board.is_fifty_moves():
        return "Draw by fifty-move rule."
    elif board.is_repetition():
        return "Draw by repetition."
    elif board.is_check():
        return "Check!"
    else:
        return "Ongoing. " + ("White" if board.turn == chess.WHITE else "Black") + " to move."

def reset_board():
    """Reset the chess board to the starting position"""
    global board, move_history
    board = chess.Board()
    move_history = []
    return {
        "fen": board.fen(),
        "history": "",
        "game_status": get_game_status()
    }

def undo_move():
    """Undo the last move"""
    global board, move_history
    if len(board.move_stack) > 0:
        board.pop()
        if move_history:
            move_history.pop()
        return {
            "fen": board.fen(),
            "history": " ".join(move_history),
            "game_status": get_game_status()
        }
    else:
        return {
            "fen": board.fen(),
            "history": " ".join(move_history),
            "game_status": get_game_status()
        }

def chat_with_ai(message, chat_history):
    """Send the current game state and user message to Groq and get a response"""
    global board, move_history
    
    # Prepare the system prompt with the current game state
    system_prompt = f"""
    You are a chess tutor helping a player improve their game. 
    
    Current board state (FEN): {board.fen()}
    Move history: {' '.join(move_history)}
    Game status: {get_game_status()}
    
    Piece positions:
    {board}
    
    Based on this board state, provide helpful advice, analyze positions, suggest moves,
    or answer any chess-related questions. Be specific about positions using algebraic notation.
    """
    
    # Call the Groq API
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        model="llama3-70b-8192",  # Using Llama 3 model
        temperature=0.5,
    )
    
    response = chat_completion.choices[0].message.content
    
    # Update chat history
    chat_history.append((message, response))
    return "", chat_history

# Create the Gradio interface
with gr.Blocks() as demo:
    gr.HTML("<h1>Chess Tutor with AI</h1>")
   
    with gr.Row():
        # Left column - Chessboard
        with gr.Column(scale=1):
            # Display the chess board as an image
            board_image = gr.Image(render_board_image(), label="Chess Board")
            status_text = gr.Textbox(get_game_status(), label="Game Status")
            history_text = gr.Textbox("", label="Move History")
            
            with gr.Row():
                source_square = gr.Textbox(label="Source Square (e.g., e2)")
                target_square = gr.Textbox(label="Target Square (e.g., e4)")
            
            with gr.Row():
                move_btn = gr.Button("Make Move")
                reset_btn = gr.Button("New Game")
                undo_btn = gr.Button("Undo Move")
            
            # Connect UI elements to backend
            def process_move(source, target):
                result = make_move("", source, target)
                return render_board_image(), result["game_status"], result["history"]
            
            move_btn.click(
                process_move, 
                [source_square, target_square], 
                [board_image, status_text, history_text]
            )
            
            reset_btn.click(
                lambda: (render_board_image(), get_game_status(), ""),
                None,
                [board_image, status_text, history_text],
                preprocess=reset_board
            )
            
            undo_btn.click(
                lambda: (render_board_image(), get_game_status(), " ".join(move_history)),
                None,
                [board_image, status_text, history_text],
                preprocess=undo_move
            )

            
        # Right column - Chat interface
        with gr.Column(scale=1):
            gr.HTML("<h3>Chat with your Chess Tutor</h3>")
            
            chatbot = gr.Chatbot(height=400)
            msg = gr.Textbox(
                placeholder="Ask for advice, analysis, or chess questions...",
                label="Your message"
            )
            
            msg.submit(chat_with_ai, [msg, chatbot], [msg, chatbot])
    
    # Add routes for chess moves
    demo.load(lambda: {"fen": board.fen(), "history": "", "game_status": get_game_status()})
    
    # Set up API endpoints that the JavaScript will call
    demo.queue()

# Launch the app
if __name__ == "__main__":
    demo.launch()