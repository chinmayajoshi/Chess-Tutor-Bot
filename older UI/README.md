# Streamlit
1) Add `.streamlit/secrets.toml` file and include API Key as below:
    ```toml
    GROQ_API_KEY="gsk_************"
    ```

2) Install Streamlit
    ```sh
    pip install streamlit
    ```

3) Run script:
    ```sh
    streamlit run chessboard_ui.py
    ```

4) Go to `http://192.168.29.3:8501`

    ![](../img/Chess%20UI%20Demo%20Screenshot.jpg)

---

# Gradio
1) Store API Key as environment variable.
2) Install Gradio
    ```sh
    pip install gradio
    ```

3) Run script:
    ```sh
    python chess_tutor.py
    ```
4) Go to `http://127.0.0.1:7860/`

    ![](../img/Gradio%20Chess%20UI%20Demo%20Screenshot.jpg)