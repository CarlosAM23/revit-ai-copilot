import json
import clr

# Use .NET native HTTP libraries instead of urllib (IronPython compatibility)
clr.AddReference('System.Net.Http')
from System.Net.Http import HttpClient, StringContent
from System.Text import Encoding

# Load WPF assemblies required for building UI windows
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

# Core WPF imports for window and layout
from System.Windows import Window, Thickness, GridLength, TextWrapping
from System.Windows.Controls import Grid, RowDefinition
from System.Windows.Controls import TextBox, Button, ScrollViewer
from System.Windows.Controls import StackPanel, TextBlock, DockPanel, Dock
from System.Windows.Media import SolidColorBrush, Color
from System.Windows.Input import Key

# Import API key from separate config file (not tracked by git)
from config import OPENAI_API_KEY

class CopilotWindow(Window):
    def __init__(self):
        # Set window title and dimensions
        self.Title = "AI Copilot - Revit"
        self.Width = 420
        self.Height = 580

        # Conversation history sent to OpenAI on every request
        self.conversation = [
            {"role": "system", "content": "You are an expert in Autodesk Revit and BIM modeling. Help users solve modeling problems, visibility issues, family parameters, view settings and general Revit workflows. Be clear, concise and practical."}
        ]

        self._build_ui()
        self._add_message("AI", "Hello! I am your Revit AI Copilot. How can I help you today?")

    def _build_ui(self):
        # Main container - 2 rows: chat area (flexible) + input bar (fixed 60px)
        grid = Grid()
        r1 = RowDefinition()
        r2 = RowDefinition()
        r2.Height = GridLength(60)  # Fixed height for input row
        grid.RowDefinitions.Add(r1)
        grid.RowDefinitions.Add(r2)

        # StackPanel holds all chat bubbles stacked vertically
        self.chat_panel = StackPanel()
        self.chat_panel.Margin = Thickness(8)

        # ScrollViewer wraps chat panel so it scrolls when messages overflow
        self.scroll = ScrollViewer()
        self.scroll.Content = self.chat_panel
        Grid.SetRow(self.scroll, 0)
        grid.Children.Add(self.scroll)

        # DockPanel for input area - button docked right, textbox fills the rest
        dock = DockPanel()
        dock.Margin = Thickness(8, 4, 8, 8)
        dock.LastChildFill = True

        # Send button docked to the right side
        self.send_btn = Button()
        self.send_btn.Content = "Send"
        self.send_btn.Width = 75
        self.send_btn.Margin = Thickness(4, 0, 0, 0)
        self.send_btn.Click += self._on_send  # Bind click event
        DockPanel.SetDock(self.send_btn, Dock.Right)

        # Text input where user types their question
        self.input_box = TextBox()
        self.input_box.FontSize = 13
        self.input_box.Padding = Thickness(8)
        self.input_box.KeyDown += self._on_key_down  # Bind Enter key event

        dock.Children.Add(self.send_btn)
        dock.Children.Add(self.input_box)

        Grid.SetRow(dock, 1)
        grid.Children.Add(dock)

        self.Content = grid

    def _add_message(self, sender, text):
        """Add a new message bubble to the chat panel."""
        block = TextBlock()
        block.Text = sender + ": " + text
        block.TextWrapping = TextWrapping.Wrap  # Wrap long messages
        block.Padding = Thickness(10, 8, 10, 8)
        block.Margin = Thickness(4, 3, 4, 3)
        block.FontSize = 13

        # Blue background for user messages, grey for AI messages
        if sender == "You":
            block.Background = SolidColorBrush(Color.FromRgb(0, 120, 212))
            block.Foreground = SolidColorBrush(Color.FromRgb(255, 255, 255))
        else:
            block.Background = SolidColorBrush(Color.FromRgb(240, 240, 240))

        # Add bubble to chat and scroll to latest message
        self.chat_panel.Children.Add(block)
        self.scroll.ScrollToEnd()

    def _on_key_down(self, sender, e):
        """Send message when user presses Enter key."""
        if e.Key == Key.Return:
            self._on_send(sender, e)

    def _on_send(self, sender, e):
        """Handle send button - get input, call API, show response."""
        user_text = self.input_box.Text.strip()

        # Do nothing if input is empty
        if not user_text:
            return

        # Clear input and show user message in chat
        self.input_box.Text = ""
        self._add_message("You", user_text)

        # Append user message to conversation history
        self.conversation.append({"role": "user", "content": user_text})

        # Show thinking indicator while waiting for API response
        self._add_message("AI", "Thinking...")

        try:
            # Send request to OpenAI using .NET HttpClient (IronPython compatible)
            http_client = HttpClient()
            http_client.DefaultRequestHeaders.Add(
                "Authorization", "Bearer " + OPENAI_API_KEY
            )
            content = StringContent(
                json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": self.conversation,
                    "max_tokens": 800
                }),
                Encoding.UTF8,
                "application/json"
            )
            response = http_client.PostAsync(
                "https://api.openai.com/v1/chat/completions",
                content
            ).Result
            response_text = response.Content.ReadAsStringAsync().Result
            result = json.loads(response_text)
            ai_response = result['choices'][0]['message']['content']

            # Remove "Thinking..." bubble and show real response
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )

            # Append AI response to conversation history for context
            self.conversation.append({"role": "assistant", "content": ai_response})
            self._add_message("AI", ai_response)

        except Exception as ex:
            # Remove "Thinking..." and show error message
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )
            self._add_message("AI", "Error: " + str(ex))


# Create and display the window
# ShowDialog blocks execution until the window is closed
window = CopilotWindow()
window.ShowDialog()