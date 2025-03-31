# Chess Tutor Bot
A chess app with an integrated LLM bot as a real-time assistant.

![](img/Chess%20UI%20Demo%20Screenshot.jpg)

# Setup and Run

1. Install dependencies:
    ```sh
    pip install requirements.txt
    ```

2. Store Groq API Key in `.streamlit/secrets.toml`:
    ```sh
    GROQ_API_KEY="gsk_******"
    ```

3. Run app:
    ```sh
    streamlit run chessboard_ui.py
    ```

# TODO

[x] Build a basic chess UI<br>
[x] Add LLM Integration<br>
[ ] Implement Chess moves into LLM Context<br>
[ ] Implement chess engine support<br>
[ ] Add position evaluation bar (toggle)<br>
[ ] Add Player vs AI support<br>
[ ] Optimize Prompt<br>