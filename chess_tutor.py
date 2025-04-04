import os
import gradio as gr
import chess
import chess.svg
from groq import Groq

# Set up Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Global variables
board = chess.Board()
selected_square = None
move_history = []

def get_board_svg():
    """Generate SVG of current board with selected square highlighted"""
    squares = None
    if selected_square is not None:
        squares = chess.SquareSet([selected_square])
    
    last_move = None
    if len(board.move_stack) > 0:
        last_move = board.peek()
    
    return chess.svg.board(board=board, size=400, squares=squares, lastmove=last_move)

def handle_click(square_name):
    """Handle clicks on the chessboard"""
    global selected_square, board, move_history
    
    # Invalid square name
    if not square_name or len(square_name) != 2:
        return get_board_svg(), "\n".join(move_history), "Invalid square"
    
    try:
        clicked_square = chess.parse_square(square_name)
    except ValueError:
        return get_board_svg(), "\n".join(move_history), "Invalid square"
    
    # First click (select piece)
    if selected_square is None:
        piece = board.piece_at(clicked_square)
        if piece and piece.color == board.turn:
            selected_square = clicked_square
            return get_board_svg(), "\n".join(move_history), f"Selected {square_name}"
        else:
            return get_board_svg(), "\n".join(move_history), "Select your piece"
    
    # Second click (make move)
    else:
        from_square = selected_square
        to_square = clicked_square
        
        # Try to make move
        move = chess.Move(from_square, to_square)
        
        # Handle promotion
        if (board.piece_type_at(from_square) == chess.PAWN and
            ((board.turn == chess.WHITE and chess.square_rank(to_square) == 7) or
             (board.turn == chess.BLACK and chess.square_rank(to_square) == 0))):
            move.promotion = chess.QUEEN
        
        # Make move if legal
        if move in board.legal_moves:
            san_move = board.san(move)
            board.push(move)
            move_color = "White" if board.turn == chess.BLACK else "Black"  # The color who just moved
            move_history.append(f"{move_color}: {san_move}")
            selected_square = None
            
            status = "Check" if board.is_check() else ""
            if board.is_checkmate():
                status = "Checkmate! " + move_color + " wins!"
            elif board.is_stalemate():
                status = "Stalemate! Draw."
                
            return get_board_svg(), "\n".join(move_history), status
        else:
            selected_square = None  # Deselect on illegal move
            return get_board_svg(), "\n".join(move_history), "Illegal move"

def new_game():
    """Reset the chess board and history"""
    global board, move_history, selected_square
    board = chess.Board()
    move_history = []
    selected_square = None
    return get_board_svg(), "", "New game started"

def undo_move():
    """Undo the last move"""
    global board, move_history, selected_square
    if board.move_stack:
        board.pop()
        if move_history:
            move_history.pop()
        selected_square = None
        return get_board_svg(), "\n".join(move_history), "Move undone"
    else:
        return get_board_svg(), "", "No moves to undo"

def get_ai_analysis(message, chat_history):
    """Get AI analysis from Groq based on the current board state"""
    global board, move_history
    
    if not message.strip():
        return "", chat_history
    
    # Prepare system prompt with current board state
    turn = "White" if board.turn == chess.WHITE else "Black"
    system_prompt = f"""You are a chess tutor. The current chess position is:
FEN: {board.fen()}

Move history:
{chr(10).join(move_history)}

Game state:
- {turn} to move
- Check: {'Yes' if board.is_check() else 'No'}
- Checkmate: {'Yes' if board.is_checkmate() else 'No'}
- Stalemate: {'Yes' if board.is_stalemate() else 'No'}

Provide thoughtful chess analysis based on the current position.
"""
    
    try:
        # Send request to Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": m[0], "content": m[1]} for m in chat_history],
                {"role": "user", "content": message}
            ],
            model="llama-3.1-8b-instant"
        )
        
        response = chat_completion.choices[0].message.content
        chat_history.append(("user", message))
        chat_history.append(("assistant", response))
    except Exception as e:
        chat_history.append(("user", message))
        chat_history.append(("assistant", f"Error: {str(e)}"))
    
    return "", chat_history

# Create the Gradio interface
with gr.Blocks() as app:
    gr.Markdown("# Chess Tutor with AI Analysis")
    
    with gr.Row():
        # Left column: Chess board
        with gr.Column():
            # Chess board display
            board_display = gr.HTML(get_board_svg())
            
            # Square selection input
            square_input = gr.Textbox(label="Enter square (e.g., e2, e4)", placeholder="e2")
            square_btn = gr.Button("Select Square / Make Move")
            
            # Control buttons
            with gr.Row():
                new_game_btn = gr.Button("New Game")
                undo_btn = gr.Button("Undo Move")
            
            # Status and history
            status_display = gr.Textbox(label="Status", interactive=False)
            history_display = gr.Textbox(label="Move History", interactive=False, lines=10)
        
        # Right column: AI chat
        with gr.Column():
            chatbot = gr.Chatbot(label="Chess Tutor")
            msg_input = gr.Textbox(label="Ask for advice", placeholder="What should I consider for my next move?")
            clear_btn = gr.Button("Clear Chat")
    
    # Set up event handlers
    square_btn.click(handle_click, inputs=[square_input], outputs=[board_display, history_display, status_display])
    new_game_btn.click(new_game, None, [board_display, history_display, status_display])
    undo_btn.click(undo_move, None, [board_display, history_display, status_display])
    
    msg_input.submit(get_ai_analysis, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
    clear_btn.click(lambda: ([], []), None, [chatbot, msg_input])

# Launch the app
if __name__ == "__main__":
    app.launch()