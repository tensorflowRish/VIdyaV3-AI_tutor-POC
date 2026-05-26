import gradio as gr
from src.tutor_session import TutorSession

session = TutorSession()

def chat_with_tutor(message, history):
    if not message.strip():
        return history, ""

    response = session.process_turn(message)

    history.append((message, response))
    return history, ""

with gr.Blocks() as demo:
    gr.Markdown("# Vidya Realtime AI Tutor Demo")
    gr.Markdown("Ask a Python functions question and test the tutor response.")

    chatbot = gr.Chatbot()
    user_input = gr.Textbox(
        placeholder="Example: I don't understand return in functions...",
        label="Learner message"
    )

    user_input.submit(
        chat_with_tutor,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input]
    )

demo.launch()