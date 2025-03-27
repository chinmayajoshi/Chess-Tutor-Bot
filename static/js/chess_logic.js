// Global variables
let game = new Chess();
let board;
let moveHistory = [];

// Initialize board configuration
function initializeBoard() {
    const config = {
        draggable: true,
        position: 'start',
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };

    board = Chessboard('myBoard', config);
}

function onDragStart(source, piece, position, orientation) {
    // Only pick up pieces for the side to move
    if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
        (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
        return false;
    }
}

function onDrop(source, target) {
    // Attempt to make the move
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q' // always promote to queen
    });

    // If move is illegal, snapback
    if (move === null) return 'snapback';

    // Update board and move history
    board.position(game.fen());
    updateMoveHistory(move);
    checkGameStatus();
}

function onSnapEnd() {
    board.position(game.fen());
}

function updateMoveHistory(move) {
    moveHistory.push(move.san);
    const historyDiv = document.getElementById('moveHistory');
    if (historyDiv) {
        historyDiv.innerHTML = moveHistory.map((move, index) => 
            `${Math.floor(index/2 + 1)}. ${move}`
        ).join('<br>');
    }
}

function triggerConfetti() {
    function fireConfetti() {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#ff0a54', '#ff477e', '#ff7096', '#ff85a2', '#fbb1bd', '#f9bec7']
        });
    }

    fireConfetti();
    setTimeout(fireConfetti, 500);
    setTimeout(fireConfetti, 1000);
}

function checkGameStatus() {
    const statusDiv = document.getElementById('gameStatus');
    
    if (game.in_checkmate()) {
        const winner = game.turn() === 'w' ? 'Black' : 'White';
        
        triggerConfetti();
        statusDiv.innerHTML = `<span class="winner-text">${winner} Wins!</span>`;
    } else if (game.in_draw()) {
        statusDiv.innerHTML = '🤝 Draw! Game ended in a stalemate.';
    } else if (game.in_stalemate()) {
        statusDiv.innerHTML = '🚫 Stalemate! No legal moves possible.';
    } else if (game.in_threefold_repetition()) {
        statusDiv.innerHTML = '🔄 Threefold Repetition - Draw!';
    } else {
        statusDiv.innerHTML = ''; // Clear status if no special condition
    }
}

// Initialize board when script loads
$(document).ready(function() {
    initializeBoard();
});

// Expose functions globally
window.resetGame = function() {
    console.log('Reset game called');
    if (game && board) {
        game = new Chess();
        board.position('start');
        moveHistory = [];
        var historyDiv = document.getElementById('moveHistory');
        var statusDiv = document.getElementById('gameStatus');
        if (historyDiv) historyDiv.innerHTML = '';
        if (statusDiv) statusDiv.innerHTML = '';
    }
};

window.undoLastMove = function() {
    console.log('Undo move called');
    if (game && moveHistory.length > 0) {
        game.undo();
        board.position(game.fen());
        moveHistory.pop();
        var historyDiv = document.getElementById('moveHistory');
        if (historyDiv) {
            historyDiv.innerHTML = moveHistory.map((move, index) => 
                `${Math.floor(index/2 + 1)}. ${move}`
            ).join('<br>');
        }
    }
};