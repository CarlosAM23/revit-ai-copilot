# ════════════════════════════════════════════════════════════════════════════════
# IMPORTS SECTION - Required libraries and modules
# ════════════════════════════════════════════════════════════════════════════════

# For handling JSON data (converting Python objects to/from JSON format)
import json

# For making HTTP requests to external APIs (OpenAI in this case)
import urllib.request as urllib_req

# pyRevit framework for accessing Revit and UI utilities
from pyrevit import forms, script # type: ignore

# CLR allows Python to access .NET libraries (needed for WPF UI)
import clr # type: ignore

# Add references to WPF assemblies (.NET framework components for creating Windows UI)
clr.AddReference('PresentationFramework')  # Core WPF framework
clr.AddReference('PresentationCore')        # WPF core functionality
clr.AddReference('WindowsBase')             # Base classes for WPF

# Import WPF Window class for creating the chat window dialog
# Thickness is used to set margins and padding for UI elements
from System.Windows import Window, Thickness # type: ignore

# Import WPF control components for building the user interface:
# Grid = layout container with rows/columns
# RowDefinition = defines properties of grid rows
# GridLength = specifies row/column size
# TextBox = text input field
# Button = clickable button
# ScrollViewer = makes content scrollable
# StackPanel = arranges items vertically or horizontally
# TextBlock = displays text (read-only)
# Border = visual container with border and background
from System.Windows.Controls import ( # type: ignore
    Grid, RowDefinition, GridLength, GridUnitType,
    TextBox, Button, ScrollViewer, StackPanel,
    TextBlock, Border
)

# Import color and brush classes for styling UI elements (colors, backgrounds)
from System.Windows.Media import SolidColorBrush, Color # type: ignore

# Import Dispatcher for managing UI thread operations
from System.Windows.Threading import Dispatcher # type: ignore

# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Set up API credentials and AI behavior
# ════════════════════════════════════════════════════════════════════════════════

# API Key for authentication with OpenAI (required to make requests to their API)
from config import OPENAI_API_KEY
API_KEY = OPENAI_API_KEY

# Specify which AI model to use (gpt-4o-mini is faster and cheaper than full gpt-4)
MODEL   = "gpt-4o-mini"

# System prompt: This tells the AI how to behave
# The AI will act as a Revit/BIM expert and respond in Spanish
SYSTEM_PROMPT = """Eres un experto en Autodesk Revit y BIM.
Ayudas a resolver problemas de modelado, visibilidad, familias,
parámetros y flujos de trabajo en Revit.
Responde siempre en español, de forma clara y concisa."""

# ════════════════════════════════════════════════════════════════════════════════
# FUNCTION: ask_openai - Send messages to ChatGPT and get response
# ════════════════════════════════════════════════════════════════════════════════
def ask_openai(messages):
    """Sends conversation messages to OpenAI API and returns the AI's response.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
    Returns:
        String containing the AI's text response
    """
    
    # Create the request body as JSON:
    # - model: which AI model to use
    # - messages: conversation history (includes system prompt + all previous messages)
    # - max_tokens: limit response length to 800 tokens (roughly 600-800 words)
    data = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": 800
    }).encode('utf-8')  # Convert to UTF-8 bytes for HTTP transmission

    # Create an HTTP POST request to OpenAI's chat endpoint
    req = urllib_req.Request(
        "https://api.openai.com/v1/chat/completions",  # OpenAI API endpoint URL
        data=data,                                       # JSON payload with our messages
        headers={
            "Content-Type": "application/json",         # Tell server we're sending JSON
            "Authorization": "Bearer " + API_KEY        # Include API key for authentication
        }
    )
    
    # Send the request and get the response (timeout after 30 seconds if no response)
    response = urllib_req.urlopen(req, timeout=30)
    
    # Parse the response from JSON format to Python dictionary
    result = json.loads(response.read().decode('utf-8'))
    
    # Extract and return just the text content from the first choice
    # API response structure: {'choices': [{'message': {'content': 'text here'}}]}
    return result['choices'][0]['message']['content']


# ════════════════════════════════════════════════════════════════════════════════
# CLASS: CopilotWindow - Main chat interface window
# ════════════════════════════════════════════════════════════════════════════════
class CopilotWindow(Window):
    """A WPF window that creates the AI Copilot chat interface."""
    
    # Constructor: runs when window is created
    def __init__(self):
        # Set window title (appears in title bar)
        self.Title = "AI Copilot - Revit"
        
        # Set initial window size (width x height in pixels)
        self.Width = 420
        self.Height = 600
        
        # Set minimum allowed window size (prevents it from getting too small)
        self.MinWidth = 350
        self.MinHeight = 400

        # Initialize conversation history with system prompt
        # The system prompt is included in every API call for context
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Build the user interface (buttons, text boxes, etc.)
        self._build_ui()
        
        # Add the AI's welcome message to the chat
        self._add_message("AI", "Hola! Soy tu AI Copilot para Revit. ¿En qué te puedo ayudar hoy?")

    def _build_ui(self):
        """Build the user interface layout with chat area and input area."""
        
        # Create a Grid layout container (like a table with rows and columns)
        grid = Grid()
        
        # Row 1: Chat area - Add a row with flexible height (grows to fill space)
        grid.RowDefinitions.Add(RowDefinition())
        
        # Row 2: Input area - Create a row with fixed height of 70 pixels
        r2 = RowDefinition()
        r2.Height = GridLength(70)  # Set fixed height for input area at bottom
        grid.RowDefinitions.Add(r2)

        # CHAT AREA - Create a scrollable container for messages
        
        # Create a StackPanel to hold messages (stacks items vertically)
        self.chat_panel = StackPanel()
        # Add 8 pixels of margin (space) around all sides
        self.chat_panel.Margin = Thickness(8)

        # Create a ScrollViewer (makes content scrollable when it exceeds window size)
        scroll = ScrollViewer()
        scroll.Content = self.chat_panel  # Put the message panel inside the scroll viewer
        scroll.VerticalScrollBarVisibility = 2  # Auto = show scroll bar only when needed
        
        # Place this scroll viewer in grid row 0 (the top/chat area)
        Grid.SetRow(scroll, 0)
        
        # Add the scroll viewer to the main grid
        grid.Children.Add(scroll)
        
        # Save reference to scroll viewer so we can scroll to latest message
        self.scroll = scroll

        # INPUT AREA - Create the message input section at bottom
        
        # Create a container for the input area
        input_grid = Grid()
        # Add margins: 8px left, 4px top, 8px right, 8px bottom
        input_grid.Margin = Thickness(8, 4, 8, 8)

        # Create the text input box where user types messages
        self.input_box = TextBox()
        self.input_box.FontSize = 13                              # Use 13pt font
        self.input_box.TextWrapping = 3                           # Enable word wrap
        self.input_box.AcceptsReturn = False                      # Don't accept Enter (we'll handle it)
        self.input_box.Height = 54                                # Fixed height of 54 pixels
        self.input_box.Padding = Thickness(8)                    # 8px padding inside text box
        self.input_box.Margin = Thickness(0, 0, 8, 0)            # 8px space to the right
        self.input_box.VerticalContentAlignment = 1              # Center text vertically (1 = Center)
        # Attach event handler: when user presses a key, call the _on_key_down method
        self.input_box.KeyDown += self._on_key_down

        # Create the Send button
        send_btn = Button()
        send_btn.Content = "Enviar"                              # Button label (Spanish for "Send")
        send_btn.Width = 75                                       # Button width: 75 pixels
        send_btn.Height = 54                                      # Button height: 54 pixels (matches input box)
        send_btn.FontSize = 13                                    # Font size: 13pt
        # Attach event handler: when user clicks button, call the _on_send method
        send_btn.Click += self._on_send

        # Create a DockPanel to arrange input box and button side by side
        input_row = __import__('System.Windows.Controls', fromlist=['DockPanel']).DockPanel()
        # Import DockPanel control for horizontal layout
        from System.Windows.Controls import DockPanel, Dock
        
        # Dock the send button to the right side of the panel
        DockPanel.SetDock(send_btn, Dock.Right)
        
        # Add button to the panel (positioned on right)
        input_row.Children.Add(send_btn)
        
        # Add input box to the panel (fills remaining space on left)
        input_row.Children.Add(self.input_box)
        
        # Add margins around the input area
        input_row.Margin = Thickness(8, 4, 8, 8)

        # Place this input row in grid row 1 (the bottom/input area)
        Grid.SetRow(input_row, 1)
        
        # Add the input row to the main grid
        grid.Children.Add(input_row)

        # Set the grid as the main content of the window
        self.Content = grid

    # METHOD: _add_message - Display a message in the chat area
    def _add_message(self, sender, text):
        """Add a message bubble to the chat display.
        
        Args:
            sender: "Tú" for user messages, "AI" for AI responses
            text: The message text to display
        """
        
        # Determine if this message is from the user or the AI
        is_user = sender == "Tú"

        # Create a text block (label) to display the message
        bubble = TextBlock()
        bubble.Text = "{}: {}".format(sender, text)               # Format: "Sender: Message"
        bubble.TextWrapping = 3                                   # Enable word wrapping (3 = Wrap)
        bubble.Padding = Thickness(10, 8, 10, 8)                # 10px horizontal, 8px vertical padding
        
        # Add margins to position message (left-aligned for AI, right-aligned for user)
        # Left margin 48px for user messages (pushes them right), right margin 48px for AI
        bubble.Margin = Thickness(
            48 if is_user else 4,    # Left margin: 48px if user, 4px if AI
            4,                       # Top margin: 4px
            4 if is_user else 48,    # Right margin: 4px if user, 48px if AI
            4                        # Bottom margin: 4px
        )
        bubble.FontSize = 13                                      # Use 13pt font

        # Create a border around the text (the "bubble" container)
        border = Border()
        # Set rounded corners (radius of 8 pixels for smooth bubble shape)
        border.CornerRadius = __import__('System.Windows', fromlist=['CornerRadius']).CornerRadius(8)
        border.Child = bubble                                     # Put the text inside the border
        border.Margin = Thickness(4, 2, 4, 2)                   # Small margin around each message

        # Style the message bubble based on whether it's from user or AI
        if is_user:
            # USER MESSAGES - Blue background with white text (right-aligned)
            from System.Windows.Media import Colors
            # RGB(0, 120, 212) = Microsoft blue color
            border.Background = SolidColorBrush(Color.FromRgb(0, 120, 212))
            # White text for contrast on blue background
            bubble.Foreground = SolidColorBrush(Colors.White)
        else:
            # AI MESSAGES - Light gray background (left-aligned)
            # RGB(240, 240, 240) = light gray
            border.Background = SolidColorBrush(Color.FromRgb(240, 240, 240))

        # Add the message bubble to the chat panel (displays it in the chat)
        self.chat_panel.Children.Add(border)
        
        # Auto-scroll to the bottom to show the latest message
        self.scroll.ScrollToEnd()

    # EVENT HANDLER: _on_key_down - Responds when user presses a key in the input box
    def _on_key_down(self, sender, e):
        """Handle key press events in the input box."""
        from System.Windows.Input import Key
        
        # Check if the key pressed was Enter/Return
        if e.Key == Key.Return:
            # Trigger the send function as if user clicked the Send button
            self._on_send(sender, e)

    # EVENT HANDLER: _on_send - Send user message and get AI response
    def _on_send(self, sender, e):
        """Handle send button click or Enter key press.
        Gets user input, sends it to AI, and displays response.
        """
        
        # Get the text from input box and remove extra whitespace (strip)
        user_text = self.input_box.Text.strip()
        
        # If input is empty, do nothing and return
        if not user_text:
            return

        # Clear the input box (makes it empty for next message)
        self.input_box.Text = ""
        
        # Display the user's message in the chat
        self._add_message("Tú", user_text)

        # Add user message to conversation history (needed for context in API call)
        # Format: {"role": "user", "content": "user's message"}
        self.conversation.append({"role": "user", "content": user_text})

        # Try to get response from AI (handle errors gracefully if something goes wrong)
        try:
            # Show loading indicator while waiting for AI response
            self._add_message("AI", "...")
            
            # Send conversation to OpenAI API and get response
            response = ask_openai(self.conversation)
            
            # Remove the loading indicator ("...") and replace with actual response
            # Children.Count - 1 = index of last item in the list
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )
            
            # Add AI response to conversation history for future context
            # Format: {"role": "assistant", "content": "AI's response"}
            self.conversation.append({"role": "assistant", "content": response})
            
            # Display the AI's response in the chat
            self._add_message("AI", response)
            
        # If anything goes wrong (API error, network error, etc.)
        except Exception as ex:
            # Remove the loading indicator ("...")
            self.chat_panel.Children.RemoveAt(
                self.chat_panel.Children.Count - 1
            )
            # Display error message to user
            self._add_message("AI", "Error: " + str(ex))


# ════════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION - Create and display the window
# ════════════════════════════════════════════════════════════════════════════════

# Create an instance of the CopilotWindow (runs __init__ method)
window = CopilotWindow()

# Display the window as a modal dialog (user must close it to continue)
window.ShowDialog()