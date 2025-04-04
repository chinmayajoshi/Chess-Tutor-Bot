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

3. Download stockfish chess engine from [here](https://stockfishchess.org/download/). <br>
Extract it to `./engine/stockfish/` 

4. Run app:
    ```sh
    python chess_tutor.py
    ```

5. Go to `http://127.0.0.1:7860/`

# TODO

- [x] Build a basic chess UI
- [x] Add LLM Integration
- [x] Implement Chess moves into LLM Context
- [x] Implement chess engine support
- [x] Add position engine evaluation score
- [ ] Add drag and drop UI feature
- [x] Optimize Prompt
- [ ] Integrate Langchain for tool-use 
- [ ] Add `think` toggle feature with reasoning model support
- [ ] Add Player vs AI support

# Acknowledgement

- [Groq](https://groq.com/) for fast LLM Support!
- [Gradio](https://www.gradio.app/) for the quick UI setup!
- [Stockfish](https://stockfishchess.org/) for the legendary chess engine!