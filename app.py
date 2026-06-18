"""
HarnessLoop — The Last Prompt You'll Ever Write.

A self-evolving AI system that discovers its own optimal prompt
through iterative Harness evaluation → Loop improvement cycles.

Entry point for the application.
"""

import gradio as gr
from ui.components import create_ui


import os


def main():
    demo, css, js, head = create_ui()
    is_hf = "SPACE_ID" in os.environ
    port = 7860 if is_hf else 7861
    server_name = "0.0.0.0" if is_hf else "127.0.0.1"
    demo.launch(
        server_name=server_name,
        server_port=port,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()

