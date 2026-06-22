"""
HarnessLoop — The Last Prompt You'll Ever Write.

A self-evolving AI system that discovers its own optimal prompt
through iterative Harness evaluation → Loop improvement cycles.

Entry point for the application.
"""

import os
import warnings

from starlette.exceptions import StarletteDeprecationWarning

# Gradio 6.19 still uses Starlette's deprecated HTTP_422_UNPROCESSABLE_ENTITY.
warnings.filterwarnings(
    "ignore",
    category=StarletteDeprecationWarning,
    module="gradio.routes",
)

import gradio as gr
from ui.components import create_ui

demo, css, js, head = create_ui()


def launch_app() -> None:
    is_hf = "SPACE_ID" in os.environ
    port = 7860 if is_hf else 7861
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        theme=gr.themes.Base(),
        css=css,
        js=js,
        head=head,
    )


if __name__ == "__main__":
    launch_app()
