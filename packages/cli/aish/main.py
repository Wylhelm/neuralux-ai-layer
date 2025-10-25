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
                elif user_input.startswith("/"):
                    console.print(f"[red]Unknown command: {user_input}[/red]")
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

## Tips

1. Be specific about what you want
2. Commands are shown before execution for safety
3. Use `/explain` to understand complex commands
4. Context-aware: knows your current directory and git status
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
    
    asyncio.run(run())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

