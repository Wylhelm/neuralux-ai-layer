"""Conversational mode with multi-step workflow support."""

import asyncio
from typing import Optional, Dict, Any
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Confirm

from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient
from neuralux.conversation_handler import ConversationHandler
from neuralux.memory import default_session_id

logger = structlog.get_logger(__name__)
console = Console()


class ConversationalMode:
    """
    Enhanced conversational mode with multi-step workflow support.
    
    Features:
    - Contextual memory across turns
    - Multi-step action planning
    - Reference resolution ("it", "that file", etc.)
    - Approval management for destructive actions
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize conversational mode."""
        self.config = NeuraluxConfig()
        self.message_bus: Optional[MessageBusClient] = None
        self.handler: Optional[ConversationHandler] = None
        self.session_id = session_id or default_session_id()
        self.running = False
    
    async def connect(self):
        """Connect to message bus and initialize handler."""
        try:
            self.message_bus = MessageBusClient(self.config)
            await self.message_bus.connect()
            
            self.handler = ConversationHandler(
                message_bus=self.message_bus,
                session_id=self.session_id,
                user_id="cli_user",
                approval_callback=self._approval_callback,
            )
            
            # Subscribe to agent suggestions
            await self.message_bus.subscribe("agent.suggestion", self._handle_suggestion)
            
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect: {e}[/red]")
            return False
    
    async def disconnect(self):
        """Disconnect from message bus."""
        if self.message_bus:
            await self.message_bus.disconnect()

    async def _handle_suggestion(self, suggestion: Dict[str, Any]):
        """Handle incoming suggestions from the agent."""
        if not isinstance(suggestion, dict):
            return

        title = suggestion.get("title") or "Suggestion"
        message = suggestion.get("message") or ""
        actions = suggestion.get("actions") or []

        body_lines = []
        if message:
            body_lines.append(message)

        if isinstance(actions, list) and actions:
            body_lines.append("")
            for idx, action in enumerate(actions, 1):
                label = action.get("label") or f"Option {idx}"
                command = action.get("command")
                if command:
                    body_lines.append(f"{idx}. [cyan]{label}[/cyan] → `{command}`")
                else:
                    body_lines.append(f"{idx}. [cyan]{label}[/cyan]")

        panel_body = "\n".join(body_lines) if body_lines else "No additional details."

        console.print(
            Panel(
                panel_body,
                title=f"🧠 {title}",
                border_style="yellow",
            )
        )
    
    def _approval_callback(self, action) -> bool:
        """Ask user for approval of an action."""
        console.print(Panel(
            f"[yellow]Action requires approval:[/yellow]\n\n"
            f"Type: {action.action_type.value}\n"
            f"Description: {action.description}\n"
            f"Params: {action.params}",
            title="⚠️  Approval Required",
            border_style="yellow"
        ))
        
        return Confirm.ask("Approve this action?", default=True)
    
    async def run(self):
        """Run the conversational mode."""
        self.running = True
        
        # Display welcome message
        welcome = """# 🧠 Neuralux Conversational Mode

Welcome to the enhanced conversational interface!

**What's new:**
- 🔗 **Contextual memory** - I remember what we discuss
- 🎯 **Multi-step workflows** - Complex tasks, one request
- 📝 **File operations** - Create, write, move files naturally
- 🎨 **Image generation** - Generate and save images
- 📸 **OCR integration** - Extract and use text from images

**Example workflows:**
```
> create a file named todo.txt
> write a list of 5 project ideas in it
> generate an image of a futuristic city
> save it to my Pictures folder
```

Type `help` for commands, `/reset` to clear context, or `exit` to quit.
"""
        console.print(Markdown(welcome))
        
        # Show context summary
        if self.handler:
            summary = self.handler.get_context_summary()
            if summary["turn_count"] > 0:
                console.print(f"\n[dim]Restored session with {summary['turn_count']} previous turns[/dim]\n")
        
        while self.running:
            try:
                # Get user input
                try:
                    loop = asyncio.get_running_loop()
                    user_input = await loop.run_in_executor(
                        None,
                        console.input,
                        "\n[bold cyan]You:[/bold cyan] ",
                    )
                    user_input = (user_input or "").strip()
                except (KeyboardInterrupt, EOFError):
                    self.running = False
                    console.print("[green]Goodbye! 👋[/green]")
                    break

                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ["exit", "quit", "bye"]:
                    self.running = False
                    console.print("[green]Goodbye! 👋[/green]")
                    break
                
                if user_input.lower() == "/reset":
                    if self.handler:
                        self.handler.reset_conversation()
                        console.print("[green]✓ Conversation reset[/green]")
                    continue
                
                if user_input.lower() == "/history":
                    await self._show_history()
                    continue
                
                if user_input.lower() == "/context":
                    self._show_context()
                    continue
                
                if user_input.lower() == "help":
                    self._show_help()
                    continue
                
                # Process message
                await self._process_message(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                self.running = False
            except Exception as e:
                logger.error("conversation_error", error=str(e))
                console.print(f"[red]Error: {e}[/red]")
    
    async def _process_message(self, user_input: str):
        """Process a user message."""
        if not self.handler:
            console.print("[red]Not connected to services[/red]")
            return
        
        console.print()  # Blank line
        
        # Show thinking indicator
        with console.status("[bold blue]🤔 Thinking...[/bold blue]"):
            result = await self.handler.process_message(user_input, auto_approve=False)
        
        result_type = result.get("type")
        message = result.get("message", "")
        actions = result.get("actions", [])
        
        if result_type == "needs_approval":
            # Show planned actions
            self._show_planned_actions(actions)
            
            # Ask for approval
            if Confirm.ask("\n[yellow]Approve these actions?[/yellow]", default=True):
                pending_actions = result.get("pending_actions", [])
                
                with console.status("[bold green]⚙️  Executing...[/bold green]"):
                    exec_result = await self.handler.approve_and_execute(pending_actions)
                
                self._show_result(exec_result)
            else:
                console.print("[yellow]Actions cancelled[/yellow]")
        
        elif result_type in ["success", "partial_success"]:
            self._show_result(result)
        
        elif result_type == "error":
            console.print(f"[red]❌ {message}[/red]")
        
        else:
            console.print(f"[cyan]🤖 {message}[/cyan]")
    
    def _show_planned_actions(self, actions: list):
        """Display planned actions."""
        console.print("[bold]Planned actions:[/bold]\n")
        
        for i, action in enumerate(actions, 1):
            action_type = action.get("action_type", "unknown")
            description = action.get("description", "No description")
            needs_approval = action.get("needs_approval", False)
            params = action.get("params", {})
            
            approval_icon = "🔒" if needs_approval else "✅"
            console.print(f"  {i}. {approval_icon} {action_type}: {description}")
            
            # Show key parameters for transparency
            if params:
                important_params = {}
                # Show most relevant params based on action type
                if action_type == "file_create" and "file_path" in params:
                    important_params["path"] = params["file_path"]
                elif action_type == "file_write" and "file_path" in params:
                    important_params["path"] = params["file_path"]
                    if "content" in params:
                        content = params["content"]
                        if len(str(content)) > 50:
                            important_params["content"] = f"{str(content)[:50]}..."
                        else:
                            important_params["content"] = content
                elif action_type == "image_generate" and "prompt" in params:
                    important_params["prompt"] = params["prompt"]
                elif action_type == "image_save":
                    if "src_path" in params:
                        important_params["from"] = params["src_path"]
                    if "dst_path" in params:
                        important_params["to"] = params["dst_path"]
                elif action_type == "llm_generate" and "prompt" in params:
                    prompt = params["prompt"]
                    if len(prompt) > 60:
                        important_params["prompt"] = f"{prompt[:60]}..."
                    else:
                        important_params["prompt"] = prompt
                elif action_type == "command_execute" and "command" in params:
                    # Always show the full command to be executed
                    important_params["command"] = params["command"]
                
                # Display important params
                if important_params:
                    for key, value in important_params.items():
                        console.print(f"     [dim]{key}: {value}[/dim]")
    
    def _show_result(self, result: dict):
        """Display execution results."""
        message = result.get("message", "")
        actions = result.get("actions", [])
        result_type = result.get("type", "success")
        
        # Show message
        if result_type == "success":
            console.print(f"[green]✓ {message}[/green]")
        elif result_type == "partial_success":
            console.print(f"[yellow]⚠ {message}[/yellow]")
        else:
            console.print(f"[red]❌ {message}[/red]")
        
        # Show action details if verbose
        if actions and len(actions) > 0:
            console.print("\n[dim]Actions performed:[/dim]")
            for action in actions:
                success = action.get("success", False)
                action_type = action.get("action_type", "unknown")
                desc = action.get("description", "")
                details = action.get("details", {})
                
                icon = "✓" if success else "✗"
                console.print(f"  {icon} {desc or action_type}")
                
                # Show relevant details
                if success and details:
                    if "file_path" in details:
                        console.print(f"    [dim]→ {details['file_path']}[/dim]")
                    if "image_path" in details:
                        console.print(f"    [dim]→ {details['image_path']}[/dim]")
                    if "stdout" in details and details["stdout"]:
                        # Show command output
                        stdout = details["stdout"].strip()
                        if stdout:
                            console.print(f"\n[cyan]Output:[/cyan]")
                            # Show full output up to reasonable limit
                            max_output_chars = 10000  # 10KB of output
                            if len(stdout) > max_output_chars:
                                lines = stdout.split('\n')
                                truncated_output = '\n'.join(lines[:100])  # Show first 100 lines
                                if len(truncated_output) > max_output_chars:
                                    truncated_output = stdout[:max_output_chars]
                                
                                total_lines = len(lines)
                                shown_lines = len(truncated_output.split('\n'))
                                console.print(f"[dim]{truncated_output}[/dim]")
                                console.print(f"\n[yellow]⚠ Output truncated: showing {shown_lines}/{total_lines} lines ({len(truncated_output)}/{len(stdout)} chars)[/yellow]")
                            else:
                                console.print(f"[dim]{stdout}[/dim]")
                    if "stderr" in details and details["stderr"] and not success:
                        # Show error output
                        stderr = details["stderr"].strip()
                        if stderr:
                            console.print(f"\n[red]Error:[/red]")
                            console.print(f"[dim]{stderr}[/dim]")
                    
                    # Show document query results in a nice format
                    if "results" in details and action_type == "document_query":
                        results = details.get("results", [])
                        query = details.get("query", "")
                        count = details.get("count", 0)
                        
                        console.print(f"\n[cyan]Found {count} documents matching '{query}':[/cyan]\n")
                        
                        if results:
                            from rich.table import Table
                            table = Table(show_header=True, header_style="bold cyan")
                            table.add_column("#", style="dim", width=3)
                            table.add_column("Document", style="green")
                            table.add_column("Relevance", justify="right", width=10)
                            table.add_column("Preview", style="dim")
                            
                            for idx, result in enumerate(results[:10], 1):  # Show top 10
                                # Handle both 'path' and 'file_path' field names
                                file_path = result.get("file_path") or result.get("path", "")
                                filename = result.get("filename", "")
                                score = result.get("score", 0)
                                snippet = result.get("snippet", "")
                                
                                # Use filename for display, fallback to truncated path
                                if filename:
                                    display_name = filename
                                elif file_path:
                                    display_name = file_path if len(file_path) < 40 else "..." + file_path[-37:]
                                else:
                                    display_name = "unknown"
                                
                                # Truncate snippet
                                if len(snippet) > 60:
                                    snippet = snippet[:57] + "..."
                                
                                table.add_row(
                                    str(idx),
                                    display_name,
                                    f"{score:.2f}",
                                    snippet
                                )
                            
                            console.print(table)
                            console.print(f"\n[dim]Tip: To open a document, say 'open document 1' or 'show me document 2'[/dim]")
                        else:
                            console.print("[yellow]No documents found.[/yellow]")
                    
                    # Show web search results in a nice format
                    if "results" in details and action_type == "web_search":
                        results = details.get("results", [])
                        query = details.get("query", "")
                        count = details.get("count", 0)
                        
                        console.print(f"\n[cyan]Found {count} web results for '{query}':[/cyan]\n")
                        
                        if results:
                            from rich.table import Table
                            table = Table(show_header=True, header_style="bold cyan")
                            table.add_column("#", style="dim", width=3)
                            table.add_column("Title", style="green")
                            table.add_column("URL", style="blue", overflow="fold")
                            table.add_column("Snippet", style="dim")
                            
                            for idx, result in enumerate(results[:10], 1):  # Show top 10
                                title = result.get("title", "")
                                url = result.get("url", "")
                                snippet = result.get("snippet", "")
                                
                                # Truncate for display
                                if len(title) > 40:
                                    title = title[:37] + "..."
                                if len(url) > 50:
                                    url = url[:47] + "..."
                                if len(snippet) > 80:
                                    snippet = snippet[:77] + "..."
                                
                                table.add_row(
                                    str(idx),
                                    title,
                                    url,
                                    snippet
                                )
                            
                            console.print(table)
                            console.print(f"\n[dim]Tip: To open a link, say 'open link 1' or 'visit site 2'[/dim]")
                        else:
                            console.print("[yellow]No results found.[/yellow]")

                    # Show system command results in a nice format
                    if action_type == "system_command":
                        if "processes" in details:
                            from rich.table import Table
                            table = Table(show_header=True, header_style="bold cyan")
                            table.add_column("PID", style="dim", width=10)
                            table.add_column("User", style="green", width=15)
                            table.add_column("CPU %", justify="right", width=10)
                            table.add_column("Mem %", justify="right", width=10)
                            table.add_column("Name", style="cyan")

                            for p in details["processes"]:
                                table.add_row(
                                    str(p.get("pid")),
                                    p.get("username"),
                                    f"{p.get('cpu_percent', 0.0):.2f}",
                                    f"{p.get('memory_percent', 0.0):.2f}",
                                    p.get("name"),
                                )
                            console.print(table)
                        elif "status" in details:
                            console.print(f"  [dim]Status: {details['status']}[/dim]")
    
    async def _show_history(self):
        """Show conversation history."""
        if not self.handler:
            return
        
        history = self.handler.get_conversation_history(limit=20)
        
        if not history:
            console.print("[dim]No conversation history yet[/dim]")
            return
        
        console.print("\n[bold]Recent conversation:[/bold]\n")
        
        for item in history:
            role = item["role"]
            content = item["content"]
            
            if role == "user":
                console.print(f"[cyan]You:[/cyan] {content}")
            else:
                console.print(f"[green]Assistant:[/green] {content}")
            
            # Show action if present
            if "action" in item:
                action = item["action"]
                action_type = action.get("type", "unknown")
                success = action.get("success", False)
                icon = "✓" if success else "✗"
                console.print(f"  [dim]{icon} {action_type}[/dim]")
            
            console.print()  # Blank line
    
    def _show_context(self):
        """Show current context variables."""
        if not self.handler:
            return
        
        summary = self.handler.get_context_summary()
        
        table = Table(title="Current Context")
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="green")
        
        variables = summary.get("variables", {})
        if variables:
            for key, value in variables.items():
                if isinstance(value, str):
                    display_value = value[:100] + "..." if len(value) > 100 else value
                else:
                    display_value = str(value)
                table.add_row(key, display_value)
        else:
            table.add_row("No variables", "")
        
        console.print()
        console.print(table)
        console.print()
        console.print(f"[dim]Turn count: {summary.get('turn_count', 0)}[/dim]")
        console.print(f"[dim]Working directory: {summary.get('working_directory', 'unknown')}[/dim]")
    
    def _show_help(self):
        """Show help message."""
        help_text = """# Conversational Mode Commands

**Special commands:**
- `help` - Show this help
- `/reset` - Clear conversation context
- `/history` - Show conversation history
- `/context` - Show current context variables
- `exit` / `quit` - Exit conversational mode

**Example multi-step workflows:**

**1. Create and populate a file:**
```
> create a file named notes.txt
> write a summary of quantum computing in it
```

**2. Generate and save an image:**
```
> generate an image of a serene mountain landscape
> save it to my Pictures folder
```

**3. OCR and process:**
```
> ocr the active window
> put the text in a file named extracted.txt
```

**4. Chain multiple operations:**
```
> create a file ideas.txt
> write 5 startup ideas about AI in it
> generate an image representing the first idea
> save the image to Desktop
```

The assistant remembers context, so you can use references like:
- "it", "that", "the file", "the image"
- "write X **in it**" (refers to last created file)
- "save **it** to..." (refers to last generated image)
"""
        console.print(Markdown(help_text))


async def main():
    """Main entry point for conversational mode."""
    mode = ConversationalMode()
    
    if await mode.connect():
        try:
            await mode.run()
        finally:
            await mode.disconnect()
    else:
        console.print("[red]Failed to initialize conversational mode[/red]")


if __name__ == "__main__":
    asyncio.run(main())
