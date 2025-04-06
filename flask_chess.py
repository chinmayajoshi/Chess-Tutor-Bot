from flask import Flask, render_template, request, jsonify, session
import chess
import chess.pgn
import json
import os
from groq import Groq

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize Groq client - replace with your API key
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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

@app.route('/ask_tutor', methods=['POST'])
def ask_tutor():
    data = request.json
    user_message = data.get('message', '')
    
    # Load current board state
    board = chess.Board(session['board_fen'])
    move_history = session.get('move_history', [])
    
    # Create system prompt with current game state
    system_prompt = f"""You are a helpful chess tutor. 
Current board state (FEN): {board.fen()}
Move history: {', '.join(move_history)}

Analyze the position and provide helpful advice based on the user's question.
Be specific about pieces, threats, opportunities, and strategic considerations.
"""
    
    # Get chat history and add user message
    chat_history = session.get('chat_history', [])
    chat_history.append({"role": "user", "content": user_message})
    
    # Call Groq API
    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",  # Use appropriate model
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