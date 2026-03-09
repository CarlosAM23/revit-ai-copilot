import json
import os
import re
import clr
import System

# Load WPF assemblies
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')
clr.AddReference('System.Net.Http')

from System.Windows import Window, Thickness, GridLength, TextWrapping
from System.Windows.Controls import Grid, RowDefinition
from System.Windows.Controls import TextBox, Button, ScrollViewer
from System.Windows.Controls import StackPanel, DockPanel, Dock
from System.Windows.Media import SolidColorBrush, Color
from System.Windows.Input import Key
from System.Net.Http import HttpClient, StringContent
from System.Text import Encoding
from config import OPENAI_API_KEY

# Path to save chat history between sessions
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")

def clean_markdown(text):
    """Remove markdown symbols from AI response for clean display."""
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def load_history():
    """Load chat history from JSON file if it exists."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(messages):
    """Save chat history to JSON file, excluding system messages."""
    history = [m for m in messages if m['role'] != 'system']
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

class CopilotWindow(Window):
    def __init__(self):
        self.Title = "AI Copilot - Revit"
        self.Width = 420
        self.Height = 580

        # Load model context for AI awareness
        try:
            from context import get_model_context, get_selected_element_context
            model_context = get_model_context()
            element_context = get_selected_element_context()
        except:
            model_context = "No model context available."
            element_context = ""

        # System prompt with model context injected
        system_prompt = """You are a senior Autodesk Revit specialist with 15 years of BIM experience.

When a user reports a problem, follow this reasoning process:
1. Identify what Revit element or setting is most likely causing it
2. List the 2-3 most common causes for that specific problem
3. Give clear numbered steps to verify and fix each cause
4. Mention the exact parameter name and where to find it in Revit

You have deep knowledge of:
- Revit families (doors, windows, walls, floors, ceilings, roofs)
- View settings (View Range, Visibility/Graphics, Detail Level, Phase)
- Family parameters (instance and type parameters)
- Wall joins, geometry connections and hosted elements
- Sheets, views, annotations and documentation
- Revit 2026 interface and workflows

Rules:
- Never use markdown (no ###, no **, no -)
- Use plain numbered lists (1. 2. 3.)
- For simple questions: 2-3 sentences
- For technical problems: up to 250 words with numbered steps
- Always name the exact Revit parameter and its location
- If you are not sure, say so and suggest where to verify

""" + model_context

        # Initialize conversation with system prompt, model context and selected element
        full_context = model_context
        if element_context:
            full_context += "\n" + element_context

        self.conversation = [
            {"role": "system", "content": system_prompt + "\n\n" + full_context}
        ]

        # Show context indicator in window title
        if element_context:
            self.Title = "AI Copilot - Revit (Element selected)"
        else:
            self.Title = "AI Copilot - Revit"

        # Load previous chat history and append to conversation
        self.chat_log = load_history()
        for msg in self.chat_log:
            self.conversation.append(msg)

        self._build_ui()

        # Show previous messages or welcome message
        if self.chat_log:
            for msg in self.chat_log:
                sender = "You" if msg['role'] == 'user' else "AI"
                self._add_message(sender, msg['content'])
        else:
            self._add_message("AI", "Hello! I am your Revit AI Copilot. How can I help you today?")

    def _build_ui(self):
        grid = Grid()
        r1 = RowDefinition()
        r2 = RowDefinition()
        r2.Height = GridLength(60)
        grid.RowDefinitions.Add(r1)
        grid.RowDefinitions.Add(r2)

        self.chat_panel = StackPanel()
        self.chat_panel.Margin = Thickness(8)

        self.scroll = ScrollViewer()
        self.scroll.Content = self.chat_panel
        Grid.SetRow(self.scroll, 0)
        grid.Children.Add(self.scroll)

        dock = DockPanel()
        dock.Margin = Thickness(8, 4, 8, 8)
        dock.LastChildFill = True

        self.send_btn = Button()
        self.send_btn.Content = "Send"
        self.send_btn.Width = 75
        self.send_btn.Margin = Thickness(4, 0, 0, 0)
        self.send_btn.Click += self._on_send
        DockPanel.SetDock(self.send_btn, Dock.Right)

        self.input_box = TextBox()
        self.input_box.FontSize = 13
        self.input_box.Padding = Thickness(8)
        self.input_box.KeyDown += self._on_key_down

        dock.Children.Add(self.send_btn)
        dock.Children.Add(self.input_box)

        Grid.SetRow(dock, 1)
        grid.Children.Add(dock)

        self.Content = grid

    def _add_message(self, sender, text):
        """Add a selectable message bubble using readonly TextBox."""
        block = TextBox()
        block.Text = sender + ": " + text
        block.TextWrapping = TextWrapping.Wrap
        block.Padding = Thickness(10, 8, 10, 8)
        block.Margin = Thickness(4, 3, 4, 3)
        block.FontSize = 13
        block.BorderThickness = Thickness(0)
        block.IsReadOnly = True
        block.IsTabStop = False

        if sender == "You":
            block.Background = SolidColorBrush(Color.FromRgb(0, 120, 212))
            block.Foreground = SolidColorBrush(Color.FromRgb(255, 255, 255))
        else:
            block.Background = SolidColorBrush(Color.FromRgb(240, 240, 240))
            block.Foreground = SolidColorBrush(Color.FromRgb(30, 30, 30))

        self.chat_panel.Children.Add(block)
        self.scroll.ScrollToEnd()

    def _on_key_down(self, sender, e):
        """Send message when user presses Enter key."""
        if e.Key == Key.Return:
            self._on_send(sender, e)

    def _on_send(self, sender, e):
        """Handle send - get input, call API, show response, save history."""
        user_text = self.input_box.Text.strip()
        if not user_text:
            return

        self.input_box.Text = ""
        self._add_message("You", user_text)

        # Append user message to conversation
        self.conversation.append({"role": "user", "content": user_text})

        # Show thinking indicator
        self._add_message("AI", "Thinking...")

        try:
            # Call OpenAI API with full conversation history
            http_client = HttpClient()
            http_client.DefaultRequestHeaders.Add(
                "Authorization", "Bearer " + OPENAI_API_KEY
            )
            # Encode to ASCII to strip any special characters before sending
            # Sanitize all message content to ASCII before sending
            clean_messages = []
            for msg in self.conversation:
                clean_messages.append({
                    "role": msg["role"],
                    "content": msg["content"].encode("ascii", "ignore").decode("ascii")
                })

            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": clean_messages,
                "max_tokens": 800
            }, ensure_ascii=True)

            content = StringContent(
                payload,
                Encoding.UTF8,
                "application/json"
            )
            response = http_client.PostAsync(
                "https://api.openai.com/v1/chat/completions",
                content
            ).Result
            # Read response as bytes and decode as UTF-8 explicitly
            response_bytes = response.Content.ReadAsByteArrayAsync().Result
            response_text = Encoding.UTF8.GetString(response_bytes)
            result = json.loads(response_text)
            ai_response = result['choices'][0]['message']['content']

            # Clean markdown from response
            clean_response = clean_markdown(ai_response)

            # Remove thinking bubble
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )

            # Add response to conversation and UI
            self.conversation.append({"role": "assistant", "content": clean_response})
            self._add_message("AI", clean_response)

            # Save history to file
            save_history(self.conversation)

        except Exception as ex:
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )
            self._add_message("AI", "Error: " + str(ex))

# Run the Copilot window
window = CopilotWindow()
window.ShowDialog()