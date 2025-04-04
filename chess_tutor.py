import os
import gradio as gr
import chess
import chess.svg
from groq import Groq

# Set up Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Global variables
board = chess.Board()
move_history = []

def get_board_svg():
    """Generate SVG of current board with last move highlighted"""
    last_move = None
    if len(board.move_stack) > 0:
        last_move = board.peek()
    
    return chess.svg.board(board=board, size=400, lastmove=last_move)

def make_move(from_square, to_square):
    """Process a chess move"""
    global board, move_history
    
    if not from_square or not to_square:
        return get_board_svg(), "\n".join(move_history), "Invalid move"
    
    try:
        # Parse square coordinates
        from_sq = chess.parse_square(from_square)
        to_sq = chess.parse_square(to_square)
        
        # Create move object
        move = chess.Move(from_sq, to_sq)
        
        # Handle promotion (always to queen for simplicity)
        if (board.piece_type_at(from_sq) == chess.PAWN and
            ((board.turn == chess.WHITE and chess.square_rank(to_sq) == 7) or
             (board.turn == chess.BLACK and chess.square_rank(to_sq) == 0))):
            move.promotion = chess.QUEEN
        
        # Make move if legal
        if move in board.legal_moves:
            san_move = board.san(move)
            board.push(move)
            move_color = "White" if board.turn == chess.BLACK else "Black"
            move_history.append(f"{move_color}: {san_move}")
            
            status = "Check" if board.is_check() else ""
            if board.is_checkmate():
                status = "Checkmate! " + move_color + " wins!"
            elif board.is_stalemate():
                status = "Stalemate! Draw."
                
            return get_board_svg(), "\n".join(move_history), status
        else:
            return get_board_svg(), "\n".join(move_history), "Illegal move"
    except Exception as e:
        return get_board_svg(), "\n".join(move_history), f"Error: {str(e)}"

def new_game():
    """Reset the chess board and history"""
    global board, move_history
    board = chess.Board()
    move_history = []
    return get_board_svg(), "", "New game started"

def undo_move():
    """Undo the last move"""
    global board, move_history
    if board.move_stack:
        board.pop()
        if move_history:
            move_history.pop()
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
with gr.Blocks(css="""
    #board { 
        width: 400px;
        height: 400px;
        margin: 0 auto;
    }
""") as app:
    gr.Markdown("# Chess Tutor with AI Analysis")
    
    # Hidden fields for move coordination
    from_square = gr.Textbox(visible=False)
    to_square = gr.Textbox(visible=False)
    move_trigger = gr.Button("Make Move", visible=False)
    
    with gr.Row():
        # Left column: Chess board
        with gr.Column():
            # Chess board display (SVG version as fallback)
            board_display = gr.HTML(get_board_svg())
            
            # Temporary solution - square input while JS loads
            with gr.Row():
                input_from = gr.Textbox(label="From square (e.g. e2)", max_lines=1)
                input_to = gr.Textbox(label="To square (e.g. e4)", max_lines=1)
                submit_move = gr.Button("Move")
            
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
    submit_move.click(
        make_move, 
        inputs=[input_from, input_to], 
        outputs=[board_display, history_display, status_display]
    )
    
    new_game_btn.click(
        new_game, 
        None, 
        [board_display, history_display, status_display]
    )
    
    undo_btn.click(
        undo_move, 
        None, 
        [board_display, history_display, status_display]
    )
    
    msg_input.submit(get_ai_analysis, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
    clear_btn.click(lambda: ([], []), None, [chatbot, msg_input])

# Launch the app
if __name__ == "__main__":
    app.launch()