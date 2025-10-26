"""Main CLI application for aish."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax

# Add common package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient

console = Console()


class AIShell:
    """AI-powered shell assistant."""
    
    def __init__(self):
        """Initialize the AI shell."""
        self.config = NeuraluxConfig()
        self.message_bus: Optional[MessageBusClient] = None
        self.context = {
            "cwd": os.getcwd(),
            "user": os.getenv("USER", "user"),
            "shell": os.getenv("SHELL", "/bin/bash"),
        }
    
    async def connect(self):
        """Connect to the message bus."""
        try:
            self.message_bus = MessageBusClient(self.config)
            await self.message_bus.connect()
            return True
        except Exception as e:
            console.print(f"[red]Failed to connect to message bus: {e}[/red]")
            console.print("[yellow]Make sure the Neuralux services are running:[/yellow]")
            console.print("  docker-compose up -d")
            return False
    
    async def disconnect(self):
        """Disconnect from the message bus."""
        if self.message_bus:
            await self.message_bus.disconnect()
    
    async def speak(self, text: str, wait: bool = True):
        """Speak text using TTS."""
        if not self.message_bus:
            return
        
        try:
            import subprocess
            import base64
            import tempfile
            
            response = await self.message_bus.request(
                "ai.audio.tts",
                {"text": text, "output_format": "wav"},
                timeout=30.0
            )
            
            if "error" not in response:
                audio_data = base64.b64decode(response["audio_data"])
                
                # Save and play
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    temp_path = f.name
                
                try:
                    # Try paplay first (PulseAudio)
                    subprocess.run(["paplay", temp_path], check=True, capture_output=True)
                except:
                    try:
                        # Fallback to aplay
                        subprocess.run(["aplay", temp_path], check=True, capture_output=True)
                    except:
                        pass
                finally:
                    os.unlink(temp_path)
        except Exception:
            pass
    
    def _get_context_info(self) -> str:
        """Get context information for the LLM."""
        context_parts = [
            f"Current directory: {self.context['cwd']}",
            f"User: {self.context['user']}",
            f"Shell: {self.context['shell']}",
        ]
        
        # Add git info if in a git repo
        try:
            git_branch = subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
                cwd=self.context['cwd'],
                text=True
            ).strip()
            if git_branch:
                context_parts.append(f"Git branch: {git_branch}")
        except:
            pass
        
        return "\n".join(context_parts)
    
    async def search_files(self, query: str) -> dict:
        """Search for files by content."""
        if not self.message_bus:
            return {"error": "Not connected to message bus"}
        
        try:
            response = await self.message_bus.request(
                "system.file.search",
                {"query": query, "limit": 10},
                timeout=10.0
            )
            return response
        except Exception as e:
            return {"error": str(e)}
    
    async def ask_llm(self, user_input: str, mode: str = "command") -> str:
        """Ask the LLM for help."""
        if not self.message_bus:
            return "Error: Not connected to message bus"
        
        context_info = self._get_context_info()
        
        if mode == "command":
            system_prompt = """You are an expert Linux system administrator and shell scripting expert.
Your job is to convert natural language requests into safe, correct shell commands.

Rules:
1. Provide ONLY the command, no explanations unless asked
2. Use safe commands - avoid destructive operations without confirmation
3. Prefer standard Linux tools (bash, coreutils, etc.)
4. Consider the user's current context
5. If unsure or the request is dangerous, explain the risks

Current context:
{context}
"""
        elif mode == "explain":
            system_prompt = """You are an expert Linux system administrator.
Your job is to explain shell commands, errors, and system behavior in clear, helpful terms.

Rules:
1. Be concise but thorough
2. Explain what the command does step by step
3. Mention any risks or important considerations
4. Suggest alternatives if relevant

Current context:
{context}
"""
        else:
            system_prompt = """You are a helpful Linux assistant.
Provide clear, accurate information about the user's question.

Current context:
{context}
"""
        
        request_data = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt.format(context=context_info)
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }
        
        try:
            response = await self.message_bus.request("ai.llm.request", request_data, timeout=30.0)
            
            if "error" in response:
                return f"Error: {response['error']}"
            
            return response.get("content", "No response generated")
        except asyncio.TimeoutError:
            return "Error: Request timed out. The LLM service might be loading the model."
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def interactive_mode(self):
        """Run in interactive mode."""
        console.print(Panel.fit(
            "[bold cyan]Neuralux AI Shell[/bold cyan]\n"
            "Natural language command interface\n\n"
            "Commands:\n"
            "  /explain <command> - Explain a command\n"
            "  /search <query> - Search files\n"
            "  /help - Show help\n"
            "  /exit - Exit the shell\n"
            "  Ctrl+C - Cancel current operation",
            border_style="cyan"
        ))
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]aish[/bold green]").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input == "/exit":
                    break
                elif user_input == "/help":
                    self._show_help()
                    continue
                elif user_input.startswith("/explain "):
                    command = user_input[9:]
                    await self._explain_command(command)
                    continue
                elif user_input.startswith("/search "):
                    search_query = user_input[8:]
                    await self._search_files_interactive(search_query)
                    continue
                elif user_input.startswith("/"):
                    console.print(f"[red]Unknown command: {user_input}[/red]")
                    continue
                
                # Detect file search queries (semantic)
                search_keywords = [
                    "find files", "search files", "locate files", 
                    "files about", "files containing", "files with",
                    "find document", "search document", "locate document",
                    "document about", "document containing", "document with",
                    "find the document", "find the file",
                    "documents about", "documents containing",
                ]
                is_search_query = any(keyword in user_input.lower() for keyword in search_keywords)
                
                if is_search_query:
                    await self._search_files_interactive(user_input)
                    continue
                
                # Get command from LLM
                with console.status("[bold yellow]Thinking...[/bold yellow]"):
                    response = await self.ask_llm(user_input, mode="command")
                
                # Clean the response - remove markdown code blocks
                clean_response = response.strip()
                if clean_response.startswith('```'):
                    # Remove code block markers
                    lines = clean_response.split('\n')
                    lines = [l for l in lines if not l.strip().startswith('```')]
                    clean_response = '\n'.join(lines).strip()
                
                # Display the suggested command
                console.print("\n[bold]Suggested command:[/bold]")
                syntax = Syntax(clean_response, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                
                # Ask for confirmation
                if Confirm.ask("\nExecute this command?", default=False):
                    await self._execute_command(clean_response)
                else:
                    console.print("[yellow]Command not executed[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled[/yellow]")
                continue
            except EOFError:
                break
        
        console.print("\n[cyan]Goodbye![/cyan]")
    
    async def _explain_command(self, command: str):
        """Explain a command."""
        with console.status("[bold yellow]Analyzing...[/bold yellow]"):
            explanation = await self.ask_llm(
                f"Explain this command: {command}",
                mode="explain"
            )
        
        md = Markdown(explanation)
        console.print("\n[bold]Explanation:[/bold]")
        console.print(Panel(md, border_style="blue"))
    
    def _extract_search_query(self, query: str) -> str:
        """Extract the actual search terms from a natural language query."""
        import re
        
        # Remove common search command phrases
        patterns = [
            r'^find\s+(the\s+)?(file|files|document|documents)\s+(about|containing|with|on)\s+',
            r'^search\s+(for\s+)?(file|files|document|documents)\s+(about|containing|with|on)\s+',
            r'^locate\s+(the\s+)?(file|files|document|documents)\s+(about|containing|with|on)\s+',
            r'^(find|search|locate)\s+(the\s+)?(file|files|document|documents)\s+',
            r'^(document|documents|file|files)\s+(about|containing|with|on)\s+',
        ]
        
        cleaned = query.lower().strip()
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # If we removed everything, use the original query
        if not cleaned or len(cleaned) < 2:
            return query
        
        return cleaned.strip()
    
    async def _search_files_interactive(self, query: str):
        """Search files and display results interactively."""
        # Extract the actual search terms from natural language
        extracted_query = self._extract_search_query(query)
        
        with console.status(f"[bold yellow]Searching for: {extracted_query}...[/bold yellow]"):
            result = await self.search_files(extracted_query)
        
        if "error" in result:
            error = result["error"]
            if "Connection refused" in error or "not found" in error.lower():
                console.print("\n[yellow]⚠ Filesystem service not running[/yellow]")
                console.print("\n[bold]To enable file search:[/bold]")
                console.print("1. Start the filesystem service:")
                console.print("   cd services/filesystem && python service.py &")
                console.print("\n2. Index your files:")
                console.print("   aish index ~/Documents")
            else:
                console.print(f"\n[red]Error: {error}[/red]")
            return
        
        results = result.get("results", [])
        
        if not results:
            console.print(f"\n[yellow]No files found matching: {extracted_query}[/yellow]")
            console.print("\n[bold]Tips:[/bold]")
            console.print("- Make sure files are indexed: aish index ~/path/to/directory")
            console.print("- Try different search terms")
            console.print("- Check that files contain text content")
            return
        
        console.print(f"\n[bold]Found {len(results)} files:[/bold]\n")
        
        for i, res in enumerate(results, 1):
            score_pct = int(res["score"] * 100)
            console.print(f"[bold cyan]{i}.[/bold cyan] [bold]{res['filename']}[/bold] (Score: {score_pct}%)")
            console.print(f"   Path: {res['file_path']}")
            console.print(f"   {res['snippet'][:150]}...")
            console.print("")
        
        # Ask if user wants to open a file
        if Confirm.ask("\nOpen a file?", default=False):
            try:
                file_num = int(Prompt.ask("Which file? (number)"))
                if 1 <= file_num <= len(results):
                    file_path = results[file_num - 1]["file_path"]
                    # Try to open with xdg-open
                    import subprocess
                    subprocess.run(["xdg-open", file_path])
                    console.print(f"[green]✓ Opened {file_path}[/green]")
            except (ValueError, KeyboardInterrupt):
                pass
    
    async def _execute_command(self, command: str):
        """Execute a shell command."""
        console.print("\n[bold]Executing...[/bold]")
        
        # Clean up command - join multiple lines with && if needed
        command = command.strip()
        if '\n' in command:
            # Multiple commands - join with &&
            commands = [c.strip() for c in command.split('\n') if c.strip()]
            command = ' && '.join(commands)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.context['cwd'],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            
            if result.returncode != 0:
                console.print(f"[red]Command failed with exit code {result.returncode}[/red]")
            else:
                console.print("[green]✓ Command completed successfully[/green]")
        
        except subprocess.TimeoutExpired:
            console.print(f"[red]Command timed out after 30 seconds[/red]")
        except Exception as e:
            console.print(f"[red]Error executing command: {e}[/red]")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
# Neuralux AI Shell Help

## Usage Examples

**Find files:**
- "show me large files in my downloads folder"
- "find python files modified today"

**System monitoring:**
- "what's using the most CPU?"
- "show disk usage"
- "check memory usage"

**File operations:**
- "copy all images to backup folder"
- "rename all txt files to md"

**Development:**
- "start a python http server"
- "find all TODOs in my code"

**Explain commands:**
- `/explain tar -xzf archive.tar.gz`
- `/explain ps aux | grep python`

**Search files by content (semantic search):**
- "find the document about Claude"
- "document containing gemini"
- "search files with budget information"
- `/search python code examples`
- `/search machine learning notes`

**Note:** For content search, use phrases like "document about", "document containing", 
or use `/search` directly. Regular "find" commands search by filename.

## Tips

1. **Index first:** Run `aish index ~/Documents` before searching content
2. Be specific about what you want
3. Commands are shown before execution for safety
4. Use `/explain` to understand complex commands
5. Context-aware: knows your current directory and git status
"""
        console.print(Markdown(help_text))


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """Neuralux AI Shell - Natural language command interface."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided, start interactive mode
        ctx.invoke(ask)


@cli.command()
@click.argument("query", nargs=-1, required=False)
@click.option("--execute", "-e", is_flag=True, help="Execute without confirmation")
@click.option("--explain", is_flag=True, help="Explain the command instead")
def ask(query, execute, explain):
    """Ask for a command or explanation."""
    if not query:
        # Interactive mode
        shell = AIShell()
        
        async def run():
            if await shell.connect():
                try:
                    await shell.interactive_mode()
                finally:
                    await shell.disconnect()
        
        asyncio.run(run())
    else:
        # Single query mode
        query_text = " ".join(query)
        shell = AIShell()
        
        async def run():
            if await shell.connect():
                try:
                    mode = "explain" if explain else "command"
                    response = await shell.ask_llm(query_text, mode=mode)
                    
                    if explain:
                        md = Markdown(response)
                        console.print(md)
                    else:
                        console.print(response)
                        if execute:
                            await shell._execute_command(response)
                finally:
                    await shell.disconnect()
        
        asyncio.run(run())


@cli.command()
@click.argument("command")
def explain(command):
    """Explain a shell command."""
    shell = AIShell()
    
    async def run():
        if await shell.connect():
            try:
                await shell._explain_command(command)
            finally:
                await shell.disconnect()
    
    asyncio.run(run())


@cli.command()
def status():
    """Check Neuralux service status."""
    shell = AIShell()
    
    async def run():
        console.print("[bold]Checking Neuralux services...[/bold]\n")
        
        # Check message bus
        if await shell.connect():
            console.print("[green]✓[/green] Message bus: Connected")
            await shell.disconnect()
        else:
            console.print("[red]✗[/red] Message bus: Not connected")
            return
        
        # Check LLM service
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/", timeout=5.0)
                if response.status_code == 200:
                    console.print("[green]✓[/green] LLM service: Running")
                else:
                    console.print("[yellow]⚠[/yellow] LLM service: Unexpected status")
        except:
            console.print("[red]✗[/red] LLM service: Not running")
        
        # Check filesystem service
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8003/", timeout=5.0)
                if response.status_code == 200:
                    console.print("[green]✓[/green] Filesystem service: Running")
                else:
                    console.print("[yellow]⚠[/yellow] Filesystem service: Unexpected status")
        except:
            console.print("[red]✗[/red] Filesystem service: Not running")
        
        # Check health service
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8004/", timeout=5.0)
                if response.status_code == 200:
                    console.print("[green]✓[/green] Health service: Running")
                else:
                    console.print("[yellow]⚠[/yellow] Health service: Unexpected status")
        except:
            console.print("[red]✗[/red] Health service: Not running")
        
        # Check audio service
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8006/", timeout=5.0)
                if response.status_code == 200:
                    console.print("[green]✓[/green] Audio service: Running")
                else:
                    console.print("[yellow]⚠[/yellow] Audio service: Unexpected status")
        except:
            console.print("[red]✗[/red] Audio service: Not running")
    
    asyncio.run(run())


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--recursive/--no-recursive", default=True, help="Index subdirectories")
def index(directory, recursive):
    """Index a directory for semantic file search."""
    shell = AIShell()
    
    async def run():
        if await shell.connect():
            try:
                console.print(f"[bold]Indexing {directory}...[/bold]\n")
                
                response = await shell.message_bus.request(
                    "system.file.index",
                    {"directory": directory, "recursive": recursive},
                    timeout=300.0  # 5 min timeout for large directories
                )
                
                if "error" in response:
                    console.print(f"[red]Error: {response['error']}[/red]")
                else:
                    console.print(f"[green]✓ Indexed {response['files_indexed']} files[/green]")
                    console.print(f"  Created {response['chunks_created']} searchable chunks")
                    console.print(f"  Duration: {response['duration_seconds']:.1f}s")
                    
                    if response.get('errors'):
                        console.print(f"\n[yellow]⚠ {len(response['errors'])} errors:[/yellow]")
                        for error in response['errors'][:5]:  # Show first 5
                            console.print(f"  {error}")
            finally:
                await shell.disconnect()
    
    asyncio.run(run())


@cli.command()
@click.option("--watch", is_flag=True, help="Continuously monitor health")
@click.option("--interval", default=2, help="Update interval in seconds (with --watch)")
def health(watch: bool, interval: int):
    """Display system health metrics."""
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    import time
    
    async def run():
        shell = AIShell()
        if not await shell.connect():
            return
        
        try:
            def create_dashboard(data: dict):
                """Create a dashboard layout from health data."""
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="body"),
                    Layout(name="footer", size=3)
                )
                
                # Header with status
                status_color = {"healthy": "green", "warning": "yellow", "critical": "red"}.get(
                    data.get("status", "unknown"), "white"
                )
                layout["header"].update(
                    Panel(
                        f"[bold]{data.get('status', 'Unknown').upper()}[/bold]",
                        style=status_color,
                        title="System Health"
                    )
                )
                
                # Body with metrics
                layout["body"].split_row(
                    Layout(name="left"),
                    Layout(name="right")
                )
                
                # Left: CPU and Memory
                metrics = data.get("current_metrics", {})
                cpu = metrics.get("cpu", {})
                memory = metrics.get("memory", {})
                
                cpu_table = Table(title="CPU", show_header=False, box=None)
                cpu_table.add_row("Usage", f"{cpu.get('usage_percent', 0):.1f}%")
                cpu_table.add_row("Load Avg", ", ".join([f"{x:.2f}" for x in cpu.get("load_average", [0, 0, 0])]))
                
                mem_table = Table(title="Memory", show_header=False, box=None)
                mem_used_gb = memory.get("used", 0) / (1024**3)
                mem_total_gb = memory.get("total", 1) / (1024**3)
                mem_table.add_row("Usage", f"{memory.get('percent', 0):.1f}%")
                mem_table.add_row("Used/Total", f"{mem_used_gb:.1f} / {mem_total_gb:.1f} GB")
                
                layout["left"].split_column(
                    Layout(Panel(cpu_table)),
                    Layout(Panel(mem_table))
                )
                
                # Right: Disks and Top Processes
                disks = metrics.get("disks", [])
                disk_table = Table(title="Disks", show_header=True)
                disk_table.add_column("Mount")
                disk_table.add_column("Used")
                disk_table.add_column("Free")
                disk_table.add_column("Usage")
                
                for disk in disks[:3]:  # Show top 3
                    used_gb = disk.get("used", 0) / (1024**3)
                    free_gb = disk.get("free", 0) / (1024**3)
                    percent = disk.get("percent", 0)
                    color = "red" if percent > 90 else "yellow" if percent > 80 else "green"
                    disk_table.add_row(
                        disk.get("mountpoint", ""),
                        f"{used_gb:.1f}GB",
                        f"{free_gb:.1f}GB",
                        f"[{color}]{percent:.1f}%[/{color}]"
                    )
                
                procs = metrics.get("top_processes", [])
                proc_table = Table(title="Top Processes", show_header=True)
                proc_table.add_column("PID")
                proc_table.add_column("Name")
                proc_table.add_column("CPU%")
                proc_table.add_column("Mem%")
                
                for proc in procs[:5]:  # Show top 5
                    proc_table.add_row(
                        str(proc.get("pid", "")),
                        proc.get("name", "")[:20],
                        f"{proc.get('cpu_percent', 0):.1f}",
                        f"{proc.get('memory_percent', 0):.1f}"
                    )
                
                layout["right"].split_column(
                    Layout(Panel(disk_table)),
                    Layout(Panel(proc_table))
                )
                
                # Footer with alerts
                alerts = data.get("alerts", [])
                if alerts:
                    alert_text = "\n".join([f"[{a.get('level', 'info')}]{a.get('message', '')}[/{a.get('level', 'info')}]" for a in alerts[:3]])
                    layout["footer"].update(Panel(alert_text, title="Alerts", style="yellow"))
                else:
                    layout["footer"].update(Panel("[green]No alerts[/green]", title="Alerts"))
                
                return layout
            
            if watch:
                # Continuous monitoring
                with Live(console=console, refresh_per_second=1) as live:
                    while True:
                        response = await shell.message_bus.request(
                            "system.health.summary",
                            {},
                            timeout=5.0
                        )
                        
                        if "error" not in response:
                            live.update(create_dashboard(response))
                        
                        time.sleep(interval)
            else:
                # Single snapshot
                response = await shell.message_bus.request(
                    "system.health.summary",
                    {},
                    timeout=5.0
                )
                
                if "error" in response:
                    console.print(f"[red]Error: {response['error']}[/red]")
                    console.print("\n[yellow]Make sure the health service is running:[/yellow]")
                    console.print("  cd services/health && python service.py &")
                else:
                    console.print(create_dashboard(response))
        
        finally:
            await shell.disconnect()
    
    asyncio.run(run())


@cli.command()
@click.argument("text", nargs=-1, required=False)
@click.option("--voice", "-v", default=None, help="Voice model to use")
@click.option("--speed", "-s", type=float, default=None, help="Speech speed (0.5-2.0)")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save audio to file")
@click.option("--play", "-p", is_flag=True, help="Play audio immediately")
def speak(text, voice, speed, output, play):
    """Convert text to speech.
    
    Examples:
      aish speak "Hello, world!"
      aish speak "This is faster" --speed 1.5
      aish speak "Save to file" --output speech.wav
    """
    if not text:
        console.print("[red]Error: No text provided[/red]")
        console.print("Usage: aish speak <text>")
        return
    
    text_to_speak = " ".join(text)
    shell = AIShell()
    
    async def run():
        if await shell.connect():
            try:
                console.print("[bold]Synthesizing speech...[/bold]")
                
                # Request TTS from audio service
                request_data = {
                    "text": text_to_speak,
                    "output_format": "wav"
                }
                if voice:
                    request_data["voice"] = voice
                if speed:
                    request_data["speed"] = speed
                
                response = await shell.message_bus.request(
                    "ai.audio.tts",
                    request_data,
                    timeout=30.0
                )
                
                if "error" in response:
                    console.print(f"[red]Error: {response['error']}[/red]")
                    console.print("\n[yellow]Make sure the audio service is running:[/yellow]")
                    console.print("  cd services/audio && python service.py &")
                    return
                
                # Decode audio data
                import base64
                audio_data = base64.b64decode(response["audio_data"])
                
                # Save to file if requested
                if output:
                    with open(output, "wb") as f:
                        f.write(audio_data)
                    console.print(f"[green]✓ Audio saved to {output}[/green]")
                
                # Play if requested
                if play or not output:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        temp_path = f.name
                    
                    try:
                        # Try to play with different audio players (paplay first for PulseAudio/PipeWire)
                        players = ["paplay", "aplay", "ffplay", "play"]
                        for player in players:
                            try:
                                import subprocess
                                subprocess.run([player, temp_path], check=True, capture_output=True)
                                console.print(f"[green]✓ Played audio ({response['duration']:.1f}s)[/green]")
                                break
                            except (FileNotFoundError, subprocess.CalledProcessError):
                                continue
                        else:
                            console.print("[yellow]No audio player found. Install aplay, paplay, or ffplay.[/yellow]")
                    finally:
                        Path(temp_path).unlink()
                
                console.print(f"[dim]Processing time: {response.get('processing_time', 0):.2f}s[/dim]")
                
            finally:
                await shell.disconnect()
    
    asyncio.run(run())


@cli.command()
@click.option("--language", "-l", default=None, help="Language code (e.g., 'en', 'fr') or 'auto'")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save transcription to file")
@click.option("--file", "-f", type=click.Path(exists=True), help="Transcribe from audio file")
@click.option("--duration", "-d", type=int, default=5, help="Recording duration in seconds (if not using --file)")
def listen(language, output, file, duration):
    """Convert speech to text.
    
    Examples:
      aish listen                           # Record 5 seconds and transcribe
      aish listen --duration 10             # Record 10 seconds
      aish listen --file recording.wav      # Transcribe existing file
      aish listen --language fr             # Transcribe in French
    """
    shell = AIShell()
    
    async def run():
        if await shell.connect():
            try:
                audio_path = file
                
                # If no file provided, record from microphone
                if not audio_path:
                    console.print(f"[bold]Recording for {duration} seconds...[/bold]")
                    console.print("[dim]Speak now...[/dim]")
                    
                    try:
                        import pyaudio
                        import wave
                        import tempfile
                        
                        # Recording parameters
                        CHUNK = 1024
                        FORMAT = pyaudio.paInt16
                        CHANNELS = 1
                        RATE = 16000
                        
                        p = pyaudio.PyAudio()
                        stream = p.open(
                            format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK
                        )
                        
                        frames = []
                        
                        for i in range(0, int(RATE / CHUNK * duration)):
                            data = stream.read(CHUNK)
                            frames.append(data)
                        
                        stream.stop_stream()
                        stream.close()
                        p.terminate()
                        
                        # Save to temporary file
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                            temp_path = f.name
                        
                        wf = wave.open(temp_path, 'wb')
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(p.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(b''.join(frames))
                        wf.close()
                        
                        audio_path = temp_path
                        
                    except ImportError:
                        console.print("[red]Error: PyAudio not installed[/red]")
                        console.print("Install with: pip install pyaudio")
                        return
                    except Exception as e:
                        console.print(f"[red]Recording failed: {e}[/red]")
                        return
                
                console.print("[bold]Transcribing...[/bold]")
                
                # Request STT from audio service
                request_data = {
                    "audio_path": audio_path,
                    "vad_filter": True
                }
                if language:
                    request_data["language"] = language
                
                response = await shell.message_bus.request(
                    "ai.audio.stt",
                    request_data,
                    timeout=60.0
                )
                
                if "error" in response:
                    console.print(f"[red]Error: {response['error']}[/red]")
                    console.print("\n[yellow]Make sure the audio service is running:[/yellow]")
                    console.print("  cd services/audio && python service.py &")
                    return
                
                # Display results
                text = response["text"]
                if not text:
                    console.print("[yellow]No speech detected in audio[/yellow]")
                else:
                    console.print("\n[bold green]Transcription:[/bold green]")
                    console.print(Panel(text, border_style="green"))
                    
                    if response.get("language"):
                        console.print(f"[dim]Language: {response['language']}[/dim]")
                    if response.get("duration"):
                        console.print(f"[dim]Audio duration: {response['duration']:.1f}s[/dim]")
                    if response.get("processing_time"):
                        console.print(f"[dim]Processing time: {response['processing_time']:.2f}s[/dim]")
                    
                    # Save to file if requested
                    if output:
                        with open(output, "w") as f:
                            f.write(text)
                        console.print(f"\n[green]✓ Transcription saved to {output}[/green]")
                
                # Cleanup temporary file if we created one
                if not file and audio_path:
                    try:
                        Path(audio_path).unlink()
                    except:
                        pass
                
            finally:
                await shell.disconnect()
    
    asyncio.run(run())


@cli.command()
@click.option("--hotkey", is_flag=True, help="Run hotkey daemon (X11 only) [documented fallback on Wayland]")
@click.option("--tray", is_flag=True, help="Show system tray icon for quick toggle (requires Ayatana/AppIndicator)")
@click.option("--toggle", is_flag=True, help="Send a toggle signal to an existing overlay instance and exit")
@click.option("--show", is_flag=True, help="Send a show signal to an existing overlay instance and exit")
@click.option("--hide", is_flag=True, help="Send a hide signal to an existing overlay instance and exit")
def overlay(hotkey: bool, tray: bool, toggle: bool, show: bool, hide: bool):
    """Launch the Neuralux GUI overlay."""
    # Try to import GTK overlay components with a clear error if unavailable
    try:
        # Add packages/ to sys.path so we can import the overlay package
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from overlay.overlay_window import OverlayApplication
        from overlay.config import OverlayConfig
        # Tray is optional; imported lazily later
        from gi.repository import GLib  # type: ignore
    except Exception as e:  # pragma: no cover - environment dependent
        console.print("[red]Failed to load GTK4 overlay.[/red]")
        console.print("[yellow]Ensure GTK4 bindings are installed:[/yellow]")
        console.print("  sudo apt install python3-gi gir1.2-gtk-4.0")
        console.print(f"Details: {e}")
        sys.exit(1)

    # Create config before using it in hotkey setup
    config = OverlayConfig()

    # If control flags are provided, send the appropriate message and exit.
    if toggle or show or hide:
        async def _send_signal():
            bus = MessageBusClient(NeuraluxConfig())
            await bus.connect()
            try:
                subject = (
                    "ui.overlay.toggle" if toggle else "ui.overlay.show" if show else "ui.overlay.hide"
                )
                await bus.publish(subject, {})
                console.print(f"[green]Sent overlay signal:[/green] {subject}")
            finally:
                await bus.disconnect()

        asyncio.run(_send_signal())
        return

    if hotkey:
        # Try to start X11 hotkey listener (Wayland will be a no-op)
        try:
            from overlay.hotkey import X11HotkeyListener
            listener = X11HotkeyListener(
                on_trigger=lambda: GLib.idle_add(lambda: app.window and app.window.toggle_visibility()),
                hotkey=config.hotkey,
            )
            listener.start()
            combo = "Ctrl+Space" if "Control" in config.hotkey or "control" in config.hotkey else "Alt+Space"
            import os as _os
            if _os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11":
                console.print(f"[green]Hotkey:[/green] {combo} (X11)")
            else:
                console.print("[yellow]Wayland detected:[/yellow] Global hotkeys are restricted. Create a DE shortcut to run 'aish overlay'.")
        except Exception:
            console.print("[yellow]Hotkey unavailable. Install python-xlib or use a DE shortcut to run 'aish overlay'.[/yellow]")

    # Async command handler that queries LLM and shows minimal status
    async def handle_query(text: str):
        shell = AIShell()
        try:
            if not await shell.connect():
                return "Message bus not available"
            if text.startswith("/search "):
                query = text[len("/search "):].strip()
                result = await shell.search_files(query)
                if "error" in result:
                    return result.get("error")
                return {"_overlay_render": "file_search", "results": result.get("results", [])}
            if text in ("/health", "/health summary"):
                try:
                    summary = await shell.message_bus.request("system.health.summary", {}, timeout=5.0)
                    return {"_overlay_render": "health", "data": summary}
                except Exception as e:
                    return f"Health error: {e}"
            response = await shell.ask_llm(text, mode="command")
            return response
        finally:
            try:
                await shell.disconnect()
            except Exception:
                pass

    # Placeholder UI callback that offloads to asyncio in a thread
    def on_command(text: str):
        # Update status immediately
        try:
            if app.window is not None:
                app.window.set_status(f"Processing: {text}")
        except Exception:
            pass

        import threading
        import asyncio as _asyncio

        def _worker():
            try:
                result = _asyncio.run(handle_query(text))
            except Exception as _e:  # pragma: no cover
                result = f"Error: {_e}"
            # Push a UI update back to the GTK thread
            try:
                def _update():
                    if not app.window:
                        return False
                    app.window.clear_results()
                    # If this is a special overlay command result, render accordingly
                    if isinstance(result, dict) and result.get("_overlay_render") == "health":
                        data = result.get("data", {})
                        app.window.add_result("Health", f"Status: {data.get('status','unknown')} | CPU: {data.get('current_metrics',{}).get('cpu',{}).get('usage_percent',0):.1f}%")
                    elif isinstance(result, dict) and result.get("_overlay_render") == "file_search":
                        items = result.get("results", [])
                        if not items:
                            app.window.add_result("Files", "No results")
                        else:
                            for it in items[: app.window.config.max_results]:
                                title = it.get("filename", "file")
                                sub = it.get("file_path", "")
                                app.window.add_result(title, sub)
                    else:
                        app.window.add_result("Result", result if isinstance(result, str) else str(result))
                    app.window.set_status("Done")
                    return False
                GLib.idle_add(_update)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    app = OverlayApplication(config=config, on_command=on_command)

    # Optional tray integration
    tray_instance = None
    if tray or getattr(config, "enable_tray", False):
        try:
            from overlay.tray import OverlayTray  # type: ignore

            def _quit():
                try:
                    # Gracefully close the GTK app
                    if app.window:
                        app.window.hide()
                    # Stop the main loop
                    from gi.repository import Gtk as _Gtk  # type: ignore
                    _Gtk.main_quit()
                except Exception:
                    pass

            # Resolve tray icon
            icon = config.tray_icon
            if icon == "auto":
                default_icon = str(Path(__file__).parent.parent.parent / "overlay" / "assets" / "neuralux-tray.svg")
                icon = default_icon if Path(default_icon).exists() else "utilities-terminal"

            tray_instance = OverlayTray(
                on_toggle=lambda: GLib.idle_add(lambda: app.window and app.window.toggle_visibility()),
                on_quit=_quit,
                icon_name=icon,
                app_name=config.app_name,
            )
            if not tray_instance.enabled:
                console.print("[yellow]Tray not available via in-process integration. Falling back to external helper...[/yellow]")
        except Exception:
            console.print("[yellow]Tray integration failed to initialize. Attempting external helper...[/yellow]")

        # Fallback: launch external tray helper (GTK3 + AppIndicator)
        if not tray_instance or not getattr(tray_instance, "enabled", False):
            try:
                import subprocess as _sp
                import os as _os
                packages_dir = str(Path(__file__).parent.parent.parent)
                env = _os.environ.copy()
                env["PYTHONPATH"] = packages_dir + _os.pathsep + env.get("PYTHONPATH", "")
                env["NEURALUX_APP_NAME"] = config.app_name
                env["NEURALUX_TRAY_ICON"] = icon if isinstance(icon, str) else "utilities-terminal"
                _sp.Popen([sys.executable, "-m", "overlay.tray_helper"], env=env)
                console.print("[green]External tray helper started.[/green]")
            except Exception:
                console.print("[yellow]Could not start external tray helper. Ensure ayatana-appindicator is installed.[/yellow]")

    # Subscribe to bus events for external tray helper control
    try:
        import threading as _threading
        import asyncio as _asyncio

        def _start_bus_listener():
            async def _runner():
                try:
                    bus = MessageBusClient(NeuraluxConfig())
                    await bus.connect()

                    async def _on_toggle(_msg):
                        try:
                            GLib.idle_add(lambda: app.window and app.window.toggle_visibility())
                        except Exception:
                            pass

                    async def _on_show(_msg):
                        try:
                            GLib.idle_add(lambda: (app.window and getattr(app.window, "show_overlay", app.window.present)()))
                        except Exception:
                            pass

                    async def _on_hide(_msg):
                        try:
                            GLib.idle_add(lambda: (app.window and getattr(app.window, "hide_overlay", app.window.hide)()))
                        except Exception:
                            pass

                    async def _on_quit(_msg):
                        try:
                            from gi.repository import Gtk as _Gtk  # type: ignore
                            GLib.idle_add(lambda: (app.window and app.window.hide(), False))
                            _Gtk.main_quit()
                        except Exception:
                            pass

                    await bus.subscribe("ui.overlay.toggle", _on_toggle)
                    await bus.subscribe("ui.overlay.show", _on_show)
                    await bus.subscribe("ui.overlay.hide", _on_hide)
                    await bus.subscribe("ui.overlay.quit", _on_quit)

                    # Keep the task alive
                    stopper = _asyncio.Event()
                    await stopper.wait()
                except Exception:
                    pass

            _asyncio.run(_runner())

        _threading.Thread(target=_start_bus_listener, daemon=True).start()
    except Exception:
        pass

    # Run the GTK application (blocks until closed)
    try:
        # Gtk.Application.run() expects argv or None
        app.run(None)
    except Exception as e:
        console.print(f"[red]Overlay terminated with error:[/red] {e}")

@cli.command()
@click.option("--continuous", "-c", is_flag=True, help="Continuous conversation mode (Ctrl+C to exit)")
@click.option("--duration", "-d", type=int, default=5, help="Recording duration per turn (seconds)")
@click.option("--language", "-l", default=None, help="Force specific language (e.g., 'en', 'fr')")
@click.option("--wake-word", "-w", is_flag=True, help="Require 'neuralux' wake word to activate")
def assistant(continuous, duration, language, wake_word):
    """Voice-activated AI assistant.
    
    Interactive conversation with voice input and output.
    
    Examples:
      aish assistant                  # Single turn conversation
      aish assistant -c               # Continuous conversation
      aish assistant -d 10            # 10 second recording per turn
      aish assistant -w               # Require wake word
    """
    shell = AIShell()
    
    async def run():
        if not await shell.connect():
            return
        
        try:
            console.print(Panel.fit(
                "[bold cyan]🎤 Voice Assistant Activated[/bold cyan]\n\n"
                f"Recording duration: {duration}s per turn\n"
                f"Mode: {'Continuous' if continuous else 'Single turn'}\n"
                f"Language: {language or 'Auto-detect'}\n"
                f"Wake word: {'Enabled' if wake_word else 'Disabled'}\n\n"
                "[dim]Speak your command after the beep...[/dim]",
                title="Neuralux Assistant"
            ))
            
            conversation_history = []
            turn = 0
            
            while True:
                turn += 1
                console.print(f"\n[bold]{'─' * 70}[/bold]")
                console.print(f"[bold cyan]Turn {turn}[/bold cyan]")
                
                # Step 1: Listen for voice input
                console.print("\n[yellow]🎤 Listening...[/yellow]")
                await shell.speak("I'm listening")
                
                import pyaudio
                import wave
                import tempfile
                
                # Record audio
                audio_format = pyaudio.paInt16
                channels = 1
                rate = 16000
                chunk = 1024
                
                p = pyaudio.PyAudio()
                stream = p.open(
                    format=audio_format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk
                )
                
                frames = []
                console.print(f"[green]Recording for {duration} seconds... Speak now![/green]")
                
                for _ in range(0, int(rate / chunk * duration)):
                    data = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data)
                
                stream.stop_stream()
                stream.close()
                p.terminate()
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                
                wf = wave.open(temp_path, "wb")
                wf.setnchannels(channels)
                wf.setsampwidth(p.get_sample_size(audio_format))
                wf.setframerate(rate)
                wf.writeframes(b"".join(frames))
                wf.close()
                
                # Step 2: Transcribe
                console.print("[yellow]🔄 Transcribing...[/yellow]")
                
                import base64
                with open(temp_path, "rb") as f:
                    audio_data = base64.b64encode(f.read()).decode()
                
                os.unlink(temp_path)
                
                stt_request = {
                    "audio_data": audio_data,
                    "language": language if language else "en",  # Default to English if not specified
                    "vad_filter": False  # Disable VAD for better capture in voice assistant
                }
                
                stt_response = await shell.message_bus.request(
                    "ai.audio.stt",
                    stt_request,
                    timeout=30.0
                )
                
                if "error" in stt_response:
                    console.print(f"[red]STT Error: {stt_response['error']}[/red]")
                    await shell.speak("Sorry, I couldn't understand you")
                    if not continuous:
                        break
                    continue
                
                user_text = stt_response.get("text", "").strip()
                detected_lang = stt_response.get("language", "unknown")
                
                if not user_text:
                    console.print("[yellow]No speech detected[/yellow]")
                    await shell.speak("I didn't hear anything")
                    if not continuous:
                        break
                    continue
                
                console.print(f"\n[bold green]You said:[/bold green] {user_text}")
                console.print(f"[dim](Language: {detected_lang})[/dim]")
                
                # Check for exit commands (expanded list)
                exit_keywords = [
                    "exit", "quit", "goodbye", "good bye", "bye", "stop", 
                    "au revoir", "adieu", "bye bye", "end", "finish", "close"
                ]
                if any(keyword in user_text.lower() for keyword in exit_keywords):
                    console.print("\n[cyan]Goodbye![/cyan]")
                    await shell.speak("Goodbye! Have a great day!")
                    break
                
                # Step 3: Process with LLM
                console.print("[yellow]🤔 Thinking...[/yellow]")
                
                # Try to get a command suggestion first
                suggested_command = await shell.ask_llm(user_text, mode="command")
                
                # Check if this looks like an actionable command request
                is_command_request = any(word in user_text.lower() for word in [
                    "show", "list", "find", "search", "create", "delete", "run",
                    "execute", "check", "get", "display", "open", "edit", "install"
                ])
                
                if is_command_request and suggested_command and not suggested_command.startswith("Error"):
                    # We have a command to execute
                    # Clean up markdown backticks from LLM response
                    clean_suggested_command = suggested_command.strip().strip('`').strip()
                    assistant_text = f"I'll run the command: {clean_suggested_command}. Should I proceed?"
                    needs_approval = True
                    pending_command = clean_suggested_command
                else:
                    # Regular conversation - no command needed
                    needs_approval = False
                    pending_command = None
                    
                    # Build conversation messages
                    messages = [
                        {
                            "role": "system",
                            "content": "You are Neuralux, a helpful voice-activated AI assistant for Linux. Provide concise, natural responses suitable for text-to-speech. Keep responses under 50 words for voice interaction."
                        }
                    ]
                    
                    # Add conversation history (last 3 turns)
                    for i, msg in enumerate(conversation_history[-6:]):
                        role = "user" if i % 2 == 0 else "assistant"
                        messages.append({"role": role, "content": msg})
                    
                    # Add current user input
                    messages.append({"role": "user", "content": user_text})
                    
                    llm_request = {
                        "messages": messages,
                        "max_tokens": 150,
                        "temperature": 0.7,
                        "stream": False
                    }
                    
                    llm_response = await shell.message_bus.request(
                        "ai.llm.request",
                        llm_request,
                        timeout=30.0
                    )
                    
                    if "error" in llm_response:
                        console.print(f"[red]LLM Error: {llm_response['error']}[/red]")
                        await shell.speak("Sorry, I'm having trouble thinking right now")
                        if not continuous:
                            break
                        continue
                    
                    assistant_text = llm_response.get("content", "").strip()
                
                console.print(f"\n[bold blue]Assistant:[/bold blue] {assistant_text}")
                
                # Add to conversation history
                conversation_history.append(user_text)
                conversation_history.append(assistant_text)
                
                # Step 4: Speak response
                console.print("[yellow]🔊 Speaking...[/yellow]")
                await shell.speak(assistant_text)
                
                # Check if command approval is needed
                if needs_approval and pending_command:
                    console.print("\n[yellow]Waiting for approval...[/yellow]")
                    await shell.speak("Should I proceed? Say yes or no")
                    
                    # Record approval response
                    console.print("[green]Recording approval (3 seconds)...[/green]")
                    
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=audio_format,
                        channels=channels,
                        rate=rate,
                        input=True,
                        frames_per_buffer=chunk
                    )
                    
                    frames = []
                    for _ in range(0, int(rate / chunk * 3)):
                        data = stream.read(chunk, exception_on_overflow=False)
                        frames.append(data)
                    
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                    
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name
                    
                    wf = wave.open(temp_path, "wb")
                    wf.setnchannels(channels)
                    wf.setsampwidth(p.get_sample_size(audio_format))
                    wf.setframerate(rate)
                    wf.writeframes(b"".join(frames))
                    wf.close()
                    
                    with open(temp_path, "rb") as f:
                        audio_data = base64.b64encode(f.read()).decode()
                    
                    os.unlink(temp_path)
                    
                    approval_response = await shell.message_bus.request(
                        "ai.audio.stt",
                        {
                            "audio_data": audio_data,
                            "language": language if language else "en",
                            "vad_filter": False
                        },
                        timeout=30.0
                    )
                    
                    approval_text = approval_response.get("text", "").strip().lower()
                    console.print(f"\n[bold]Approval response:[/bold] {approval_text}")
                    
                    if "yes" in approval_text or "oui" in approval_text or "yeah" in approval_text:
                        console.print("[green]✓ Approved![/green]")
                        await shell.speak("Okay, executing now")
                        
                        # Execute the command
                        try:
                            console.print(f"\n[bold cyan]$ {pending_command}[/bold cyan]")
                            
                            result = subprocess.run(
                                pending_command,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=30,
                                cwd=shell.context['cwd']
                            )
                            
                            output = result.stdout.strip()
                            error = result.stderr.strip()
                            
                            if result.returncode == 0:
                                # Success
                                console.print(output if output else "[dim]Command completed successfully[/dim]")
                                
                                # Speak a summary of the output
                                if output:
                                    # Get first few lines for voice output
                                    lines = output.split('\n')[:3]
                                    if len(lines) > 3:
                                        summary = f"Here are the first results: {' '.join(lines)}. There are more results shown on screen."
                                    else:
                                        summary = f"The results are: {' '.join(lines)}"
                                    await shell.speak(summary)
                                else:
                                    await shell.speak("Command completed successfully")
                            else:
                                # Error
                                console.print(f"[red]Error (exit code {result.returncode}):[/red]")
                                if error:
                                    console.print(error)
                                await shell.speak(f"Command failed with error: {error[:100]}")
                                
                        except subprocess.TimeoutExpired:
                            console.print("[red]Command timed out after 30 seconds[/red]")
                            await shell.speak("Command timed out")
                        except Exception as e:
                            console.print(f"[red]Error executing command: {e}[/red]")
                            await shell.speak(f"Error executing command: {str(e)[:100]}")
                    else:
                        console.print("[red]✗ Denied[/red]")
                        await shell.speak("Okay, I won't do that")
                
                if not continuous:
                    console.print("\n[cyan]Single turn complete. Use -c for continuous mode.[/cyan]")
                    break
                
                console.print("\n[dim]Press Ctrl+C to exit continuous mode[/dim]")
        
        except KeyboardInterrupt:
            console.print("\n\n[cyan]Voice assistant stopped[/cyan]")
            await shell.speak("Goodbye")
        
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
        
        finally:
            await shell.disconnect()
    
    asyncio.run(run())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

