# Chess Tutor Bot
A chess app with an integrated LLM bot as a real-time assistant tutor. 
Check out the [deployed app on render here](https://chess-tutor-bot.onrender.com/).

![](img/Flask%20Chess%20UI%20Demo%20Screenshot.jpg)

### Unicode Board state for System Prompt:
| | a | b | c | d | e | f | g | h | |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | ♖ | ♘ | ♗ | ⭘ | ♔ | ⭘ | ♘ | ♛| 1 |
| 2 | ♙ | ♙ | ♙ | ♙ | ♕ | ♙ | ⭘ | ♙| 2 |
| 3 | ⭘ | ⭘ | ⭘ | ⭘ | ⭘ | ⭘ | ♙ | ⭘| 3 |
| 4 | ⭘ | ⭘ | ♗ | ⭘ | ⭘ | ⭘ | ⭘ | ⭘| 4 |
| 5 | ⭘ | ⭘ | ⭘ | ⭘ | ♟ | ⭘ | ⭘ | ⭘| 5 |
| 6 | ⭘ | ⭘ | ⭘ | ⭘ | ⭘ | ⭘ | ⭘ | ⭘| 6 |
| 7 | ♟ | ♟ | ♟ | ♟ | ⭘ | ♟ | ♟ | ♟| 7 |
| 8 | ♜ | ♞ | ♝ | ⭘ | ♚ | ♝ | ♞ | ♜| 8 |
| | a | b | c | d | e | f | g | h | |

Reverse Unicode Chessboard seems to work better for LLM (as white pieces are given first to the LLM context).<br>
Check out the system prompt generated at this board state [here](demo-system-prompt.md).

# Setup and Run

1. Clone github repo: 
    ```sh
    git clone https://github.com/chinmayajoshi/Chess-Tutor-Bot/
    cd Chess-Tutor-Bot
    ```

2. Install dependencies:
    ```sh
    pip install requirements.txt
    ```

3. Store Groq API Key as environment variable:
    - Linux:
        ```sh
        export GROQ_API_KEY="gsk_******"
        ```
    - Windows:
        ```sh
        $env:GROQ_API_KEY="gsk_******"
        ```

4. Download stockfish chess engine from [here](https://stockfishchess.org/download/).<br>
Extract it to `./engine/stockfish/` 

5. Run app:
    ```sh
    python flask_chess.py
    ```

6. Open browser and go to `http://0.0.0.0:2000/`

# TODO

- [x] Build a basic chess UI
- [x] Add LLM Integration
- [x] Implement Chess moves into LLM Context
- [x] Implement chess engine support
- [x] Add position engine evaluation score toggle on UI
- [x] Add drag and drop UI feature
- [x] Optimize Prompt
- [x] Add `think` feature with reasoning model support
- [ ] Add Player vs AI support

# Acknowledgement

- [Groq](https://groq.com/) for fast LLM Support!
- [Flask](https://flask.palletsprojects.com/) for quick UI setup!
- [Stockfish](https://stockfishchess.org/) for the legendary chess engine!
- [Render](https://render.com/) for web service deployment!