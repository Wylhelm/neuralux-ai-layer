#!/usr/bin/env python3
"""
Test script for the improved voice activity detection in the voice assistant.

This script demonstrates the VAD improvements by showing how the recording
parameters work and providing examples of different configurations.
"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_voice_assistant():
    """Test the voice assistant with different VAD configurations."""
    
    console.print(Panel.fit(
        "[bold cyan]🎤 Voice Assistant VAD Test[/bold cyan]\n\n"
        "This script will test the improved voice activity detection.\n"
        "The voice assistant now automatically detects when you finish speaking\n"
        "instead of using fixed duration recording.\n\n"
        "[yellow]Make sure the audio service is running:[/yellow]\n"
        "  make start-all\n"
        "  aish status\n\n"
        "[green]Press Enter to start testing...[/green]",
        title="Neuralux VAD Test"
    ))
    
    input()
    
    # Test configurations
    test_configs = [
        {
            "name": "Default Settings",
            "description": "Standard silence detection (1.5s silence to stop)",
            "command": ["aish", "assistant", "-d", "10"]
        },
        {
            "name": "Quick Response Mode", 
            "description": "Faster silence detection (0.8s silence to stop)",
            "command": ["aish", "assistant", "-s", "0.8", "-d", "8"]
        },
        {
            "name": "Patient Mode",
            "description": "Longer silence detection (3.0s silence to stop)",
            "command": ["aish", "assistant", "-s", "3.0", "-d", "15"]
        },
        {
            "name": "Sensitive Mode",
            "description": "More sensitive volume detection",
            "command": ["aish", "assistant", "-t", "0.005", "-s", "1.0"]
        }
    ]
    
    for i, config in enumerate(test_configs, 1):
        console.print(f"\n[bold]{'─' * 60}[/bold]")
        console.print(f"[bold cyan]Test {i}: {config['name']}[/bold cyan]")
        console.print(f"[dim]{config['description']}[/dim]")
        
        console.print(f"\n[yellow]Command:[/yellow] {' '.join(config['command'])}")
        console.print(f"[green]Try saying:[/green] 'Hello, this is a test of the voice assistant with natural pauses.'")
        console.print(f"[dim]Notice how it waits for you to finish speaking before stopping.[/dim]")
        
        response = input("\nPress Enter to run this test (or 'q' to quit): ")
        if response.lower() == 'q':
            break
            
        try:
            console.print(f"\n[bold green]Running: {' '.join(config['command'])}[/bold green]")
            subprocess.run(config['command'], check=True)
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error running test: {e}[/red]")
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Test interrupted by user[/yellow]")
            break
    
    console.print(f"\n[bold green]✅ VAD Testing Complete![/bold green]")
    console.print(f"\n[cyan]Key Improvements:[/cyan]")
    console.print(f"• Real-time voice activity detection")
    console.print(f"• Configurable silence detection")
    console.print(f"• Natural pause support")
    console.print(f"• No more cut-off speech")
    console.print(f"• Better user experience")

if __name__ == "__main__":
    test_voice_assistant()
