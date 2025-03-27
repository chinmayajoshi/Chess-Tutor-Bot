import streamlit as st
import streamlit.components.v1 as components

def create_chess_app():
    st.title("Chess Game")

    # Enhanced HTML and JavaScript for piece dragging
    chess_board_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.css">
        <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/chessboard-js/1.0.0/chessboard-1.0.0.min.js"></script>
        <script src="https://unpkg.com/chess.js@0.10.3/chess.js"></script>
    </head>
    <body>
        <div id="myBoard" style="width: 500px; margin: 0 auto;"></div>
        <div id="moveHistory" style="margin-top: 20px;"></div>
        <script>
            // Initialize chess game logic
            var game = new Chess();

            // Configuration for the chessboard
            var config = {
                draggable: true,
                position: 'start',
                pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                onDragStart: onDragStart,
                onDrop: onDrop,
                onSnapEnd: onSnapEnd
            };

            // Initialize the board
            var board = Chessboard('myBoard', config);

            function onDragStart (source, piece, position, orientation) {
                // Only pick up pieces for the side to move
                if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
                    (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
                    return false;
                }
            }

            function onDrop (source, target) {
                // see if the move is legal
                var move = game.move({
                    from: source,
                    to: target,
                    promotion: 'q' // always promote to a queen for simplicity
                });

                // illegal move
                if (move === null) return 'snapback';

                // update the board to the new position
                board.position(game.fen());
            }

            function onSnapEnd () {
                // update the board position after a piece snap
                board.position(game.fen());
            }

            // Add a move history display
            var moveHistory = [];

            function onDrop (source, target) {
                var move = game.move({
                    from: source,
                    to: target,
                    promotion: 'q'
                });

                if (move !== null) {
                    // Record move in history
                    moveHistory.push(move.san);
                    
                    // Update move history display
                    updateMoveHistory();
                }
            }

            function updateMoveHistory() {
                var historyDiv = document.getElementById('moveHistory');
                if (historyDiv) {
                    historyDiv.innerHTML = moveHistory.map((move, index) => 
                        `${Math.floor(index/2 + 1)}. ${move}`
                    ).join('<br>');
                }
            }
        </script>
    </body>
    </html>
    """

    # Render the chessboard with increased height
    components.html(chess_board_html, height=700, scrolling=False)

    # Game controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("New Game"):
            st.rerun()
    
    with col2:
        game_mode = st.selectbox("Game Mode", 
                                 ["Player vs Player", 
                                  "Player vs AI", 
                                  "AI vs AI"])

def main():
    create_chess_app()

if __name__ == "__main__":
    main()