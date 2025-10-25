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


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

