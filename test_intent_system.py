#!/usr/bin/env python3
"""Test script for the intent classification system."""

import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "common"))

from neuralux.intent import IntentClassifier, IntentType
from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient

from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


async def test_intent_classifier():
    """Test the intent classifier with various inputs."""
    
    # Connect to message bus
    config = NeuraluxConfig()
    message_bus = MessageBusClient(config)
    
    try:
        await message_bus.connect()
    except Exception as e:
        console.print(f"[yellow]Warning: Could not connect to message bus: {e}[/yellow]")
        console.print("[yellow]Testing with heuristics only...[/yellow]\n")
        message_bus = None
    
    # Create classifier
    classifier = IntentClassifier(message_bus)
    
    # Test cases: (input, expected_intent, description)
    test_cases = [
        # Greetings
        ("hello", IntentType.GREETING, "Simple greeting"),
        ("hi there!", IntentType.GREETING, "Casual greeting"),
        ("how are you?", IntentType.GREETING, "Question greeting"),
        ("good morning", IntentType.GREETING, "Time-based greeting"),
        
        # Informational
        ("what is docker?", IntentType.INFORMATIONAL, "Knowledge question"),
        ("explain ssh", IntentType.INFORMATIONAL, "Explanation request"),
        ("why is the sky blue?", IntentType.INFORMATIONAL, "General knowledge"),
        ("tell me about kubernetes", IntentType.INFORMATIONAL, "Information request"),
        
        # Command requests
        ("show me large files", IntentType.COMMAND_REQUEST, "Action request"),
        ("list running processes", IntentType.COMMAND_REQUEST, "List command"),
        ("find all python files", IntentType.COMMAND_REQUEST, "Search command"),
        ("get disk usage", IntentType.COMMAND_REQUEST, "Status command"),
        
        # How-to questions (not commands!)
        ("how do I find large files?", IntentType.COMMAND_HOW_TO, "How-to question"),
        ("show me how to use grep", IntentType.COMMAND_HOW_TO, "Tutorial request"),
        ("how can I check disk space?", IntentType.COMMAND_HOW_TO, "Instruction request"),
        
        # Web search
        ("search the web for python tutorials", IntentType.WEB_SEARCH, "Explicit web search"),
        ("google latest linux news", IntentType.WEB_SEARCH, "Google search"),
        ("look up online rust documentation", IntentType.WEB_SEARCH, "Online lookup"),
        
        # File search
        ("find documents about machine learning", IntentType.FILE_SEARCH, "Document search"),
        ("search files containing TODO", IntentType.FILE_SEARCH, "Content search"),
        ("locate files about docker", IntentType.FILE_SEARCH, "File location"),
        
        # System queries
        ("check system health", IntentType.SYSTEM_QUERY, "Health check"),
        ("cpu usage", IntentType.SYSTEM_QUERY, "CPU status"),
        ("system status", IntentType.SYSTEM_QUERY, "System status"),
        
        # OCR
        ("ocr window", IntentType.OCR_REQUEST, "OCR command"),
        ("read text from screen", IntentType.OCR_REQUEST, "Text extraction"),
        
        # Image generation
        ("generate image of a sunset", IntentType.IMAGE_GEN, "Image generation"),
        ("create picture of mountains", IntentType.IMAGE_GEN, "Picture creation"),
    ]
    
    # Create results table
    table = Table(title="Intent Classification Test Results", show_lines=True)
    table.add_column("Input", style="cyan", width=40)
    table.add_column("Expected", style="blue", width=20)
    table.add_column("Classified", style="green", width=20)
    table.add_column("Confidence", justify="right", style="yellow")
    table.add_column("Approval", justify="center")
    table.add_column("Status", justify="center")
    
    passed = 0
    failed = 0
    
    for input_text, expected_intent, description in test_cases:
        try:
            # Classify intent
            result = await classifier.classify(input_text, context={})
            
            intent = result.get("intent")
            confidence = result.get("confidence", 0.0)
            needs_approval = result.get("needs_approval", False)
            reasoning = result.get("reasoning", "")
            
            # Check if correct
            is_correct = intent == expected_intent
            status = "✓" if is_correct else "✗"
            status_style = "green" if is_correct else "red"
            
            if is_correct:
                passed += 1
            else:
                failed += 1
            
            # Add to table
            table.add_row(
                input_text,
                expected_intent.value,
                intent.value if isinstance(intent, IntentType) else str(intent),
                f"{confidence:.2f}",
                "Yes" if needs_approval else "No",
                f"[{status_style}]{status}[/{status_style}]"
            )
            
            # Print reasoning for failures
            if not is_correct:
                console.print(f"  [red]Reasoning: {reasoning}[/red]")
        
        except Exception as e:
            failed += 1
            table.add_row(
                input_text,
                expected_intent.value,
                f"[red]ERROR[/red]",
                "0.00",
                "?",
                "[red]✗[/red]"
            )
            console.print(f"  [red]Error: {e}[/red]")
    
    # Display results
    console.print("\n")
    console.print(table)
    console.print("\n")
    
    # Summary
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    summary_table = Table(title="Summary", show_header=False)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")
    
    summary_table.add_row("Total Tests", str(total))
    summary_table.add_row("Passed", f"[green]{passed}[/green]")
    summary_table.add_row("Failed", f"[red]{failed}[/red]")
    summary_table.add_row("Success Rate", f"[{'green' if success_rate >= 80 else 'yellow'}]{success_rate:.1f}%[/]")
    
    console.print(summary_table)
    console.print("\n")
    
    # Cleanup
    if message_bus:
        await message_bus.disconnect()
    
    return success_rate >= 80


async def interactive_test():
    """Interactive mode to test custom inputs."""
    console.print("\n[bold cyan]Intent Classifier Interactive Test[/bold cyan]")
    console.print("Type queries to see how they're classified (Ctrl+C to exit)\n")
    
    # Connect to message bus
    config = NeuraluxConfig()
    message_bus = MessageBusClient(config)
    
    try:
        await message_bus.connect()
        console.print("[green]✓ Connected to message bus[/green]\n")
    except Exception as e:
        console.print(f"[yellow]⚠ Using heuristics only (no LLM): {e}[/yellow]\n")
        message_bus = None
    
    classifier = IntentClassifier(message_bus)
    
    try:
        while True:
            user_input = console.input("[bold green]Query:[/bold green] ").strip()
            
            if not user_input:
                continue
            
            # Classify
            result = await classifier.classify(user_input, context={})
            
            # Display result
            rprint("\n[bold]Result:[/bold]")
            rprint(f"  Intent: [cyan]{result.get('intent').value}[/cyan]")
            rprint(f"  Confidence: [yellow]{result.get('confidence', 0):.2f}[/yellow]")
            rprint(f"  Needs Approval: [{'red' if result.get('needs_approval') else 'green'}]{result.get('needs_approval')}[/]")
            rprint(f"  Reasoning: [dim]{result.get('reasoning', 'N/A')}[/dim]")
            
            if result.get("parameters"):
                rprint(f"  Parameters: {result['parameters']}")
            
            rprint()
    
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")
    finally:
        if message_bus:
            await message_bus.disconnect()


async def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_test()
    else:
        success = await test_intent_classifier()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

