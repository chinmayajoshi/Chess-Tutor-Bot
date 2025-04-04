# Chess Tutor Bot
A chess app with an integrated LLM bot as a real-time assistant.

<!-- ![](img/Chess%20UI%20Demo%20Screenshot.jpg) -->
![](img/Gradio%20Chess%20UI%20Demo%20Screenshot.jpg)

# Setup and Run

1. Install dependencies:
    ```sh
    pip install requirements.txt
    ```

2. Store Groq API Key as environment variable:
    - Linux:
        ```sh
        export GROQ_API_KEY="gsk_******"
        ```
    - Windows:
        ```sh
        $env:GROQ_API_KEY="gsk_******"
        ```

3. Run app:
    ```sh
    python chess_tutor.py
    ```

4. Go to `http://127.0.0.1:7860/`

# TODO

- [x] Build a basic chess UI
- [x] Add LLM Integration
- [x] Implement Chess moves into LLM Context
- [ ] Implement chess engine support
- [ ] Add position evaluation bar (toggle)
- [ ] Add Player vs AI support
- [ ] Optimize Prompt