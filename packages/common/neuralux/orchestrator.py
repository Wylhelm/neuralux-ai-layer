"""Action orchestrator for multi-step conversational workflows."""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

import structlog

from .conversation import (
    ConversationContext,
    ConversationManager,
    ActionResult,
    ActionType,
    ReferenceResolver,
)
from .file_ops import FileOperations, PathExpander
from .messaging import MessageBusClient

logger = structlog.get_logger(__name__)


class ActionStatus(str, Enum):
    """Status of an action execution."""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Action:
    """A single action to execute."""
    action_type: ActionType
    params: Dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[ActionResult] = None
    needs_approval: bool = True
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.value,
            "params": self.params,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "needs_approval": self.needs_approval,
            "description": self.description,
        }


class ActionOrchestrator:
    """Orchestrates multi-step workflows with approval management."""
    
    def __init__(
        self,
        message_bus: MessageBusClient,
        conversation_manager: ConversationManager,
        approval_callback: Optional[Callable[[Action], bool]] = None,
    ):
        """
        Initialize action orchestrator.
        
        Args:
            message_bus: NATS message bus client
            conversation_manager: Conversation context manager
            approval_callback: Optional callback for approval requests
        """
        self.message_bus = message_bus
        self.conversation_manager = conversation_manager
        self.approval_callback = approval_callback
    
    async def execute_action(
        self,
        action: Action,
        context: ConversationContext,
    ) -> ActionResult:
        """
        Execute a single action.
        
        Args:
            action: Action to execute
            context: Conversation context
            
        Returns:
            ActionResult with execution details
        """
        logger.info("executing_action", action_type=action.action_type.value, params=action.params)
        
        action.status = ActionStatus.EXECUTING
        start_time = time.time()
        
        try:
            # Route to appropriate handler
            if action.action_type == ActionType.LLM_GENERATE:
                result = await self._execute_llm_generate(action, context)
            elif action.action_type == ActionType.IMAGE_GENERATE:
                result = await self._execute_image_generate(action, context)
            elif action.action_type == ActionType.IMAGE_SAVE:
                result = await self._execute_image_save(action, context)
            elif action.action_type == ActionType.OCR_CAPTURE:
                result = await self._execute_ocr_capture(action, context)
            elif action.action_type == ActionType.DOCUMENT_QUERY:
                result = await self._execute_document_query(action, context)
            elif action.action_type == ActionType.WEB_SEARCH:
                result = await self._execute_web_search(action, context)
            elif action.action_type == ActionType.COMMAND_EXECUTE:
                result = await self._execute_command(action, context)
            else:
                result = ActionResult(
                    action_type=action.action_type,
                    timestamp=time.time(),
                    success=False,
                    error=f"Unknown action type: {action.action_type}",
                )
            
            action.status = ActionStatus.COMPLETED if result.success else ActionStatus.FAILED
            action.result = result
            
            # Update conversation context
            if result.success:
                self._update_context_variables(action, result, context)
            
            logger.info(
                "action_completed",
                action_type=action.action_type.value,
                success=result.success,
                duration=time.time() - start_time,
            )
            
            return result
            
        except Exception as e:
            logger.error("action_execution_failed", action_type=action.action_type.value, error=str(e))
            result = ActionResult(
                action_type=action.action_type,
                timestamp=time.time(),
                success=False,
                error=str(e),
            )
            action.status = ActionStatus.FAILED
            action.result = result
            return result
    
    def _update_context_variables(
        self,
        action: Action,
        result: ActionResult,
        context: ConversationContext,
    ):
        """Update context variables based on action result."""
        details = result.details
        
        # Update based on action type
        if action.action_type == ActionType.LLM_GENERATE:
            generated_text = details.get("content")
            if generated_text:
                context.set_variable("last_generated_text", generated_text)
        
        elif action.action_type == ActionType.IMAGE_GENERATE:
            image_path = details.get("image_path")
            if image_path:
                context.set_variable("last_generated_image", image_path)
        
        elif action.action_type == ActionType.IMAGE_SAVE:
            image_path = details.get("saved_path")
            if image_path:
                context.set_variable("last_saved_image", image_path)
        
        elif action.action_type == ActionType.OCR_CAPTURE:
            ocr_text = details.get("text")
            if ocr_text:
                context.set_variable("last_ocr_text", ocr_text)
        
        elif action.action_type == ActionType.DOCUMENT_QUERY:
            results = details.get("results", [])
            if results:
                context.set_variable("last_query_results", results)
                context.set_variable("last_query", details.get("query", ""))
        
        elif action.action_type == ActionType.WEB_SEARCH:
            results = details.get("results", [])
            if results:
                context.set_variable("last_search_results", results)
                context.set_variable("last_search_query", details.get("query", ""))
    
    async def _execute_document_query(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute document query using indexed filesystem."""
        query = action.params.get("query") or action.params.get("search")
        limit = action.params.get("limit", 10)
        
        if not query:
            return ActionResult(
                action_type=ActionType.DOCUMENT_QUERY,
                timestamp=time.time(),
                success=False,
                error="Missing query parameter",
            )
        
        try:
            # Call filesystem service's search endpoint via NATS
            response = await self.message_bus.request(
                "system.file.search",
                {
                    "query": query,
                    "limit": limit,
                },
                timeout=10.0,
            )
            
            if response.get("error"):
                return ActionResult(
                    action_type=ActionType.DOCUMENT_QUERY,
                    timestamp=time.time(),
                    success=False,
                    error=response["error"],
                )
            
            results = response.get("results", [])
            
            return ActionResult(
                action_type=ActionType.DOCUMENT_QUERY,
                timestamp=time.time(),
                success=True,
                details={
                    "query": query,
                    "count": len(results),
                    "results": results,
                },
            )
            
        except Exception as e:
            return ActionResult(
                action_type=ActionType.DOCUMENT_QUERY,
                timestamp=time.time(),
                success=False,
                error=f"Document query failed: {e}",
            )
    
    async def _execute_web_search(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute web search using DuckDuckGo."""
        query = action.params.get("query")
        num_results = action.params.get("limit", 5)
        
        if not query:
            return ActionResult(
                action_type=ActionType.WEB_SEARCH,
                timestamp=time.time(),
                success=False,
                error="Missing query parameter",
            )
        
        try:
            # Use DuckDuckGo search
            try:
                from ddgs import DDGS
            except Exception:
                from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="us-en", safesearch="moderate", max_results=num_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            
            return ActionResult(
                action_type=ActionType.WEB_SEARCH,
                timestamp=time.time(),
                success=True,
                details={
                    "query": query,
                    "count": len(results),
                    "results": results,
                },
            )
            
        except ImportError:
            return ActionResult(
                action_type=ActionType.WEB_SEARCH,
                timestamp=time.time(),
                success=False,
                error="DuckDuckGo search library not installed. Install with: pip install duckduckgo-search",
            )
        except Exception as e:
            return ActionResult(
                action_type=ActionType.WEB_SEARCH,
                timestamp=time.time(),
                success=False,
                error=f"Web search failed: {str(e)}",
            )
    
    async def _execute_image_generate(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute image generation."""
        prompt = action.params.get("prompt")
        
        if not prompt:
            return ActionResult(
                action_type=ActionType.IMAGE_GENERATE,
                timestamp=time.time(),
                success=False,
                error="Missing prompt parameter",
            )
        
        try:
            # Call vision service for image generation
            request = {
                "prompt": prompt,
                "width": action.params.get("width", 1024),
                "height": action.params.get("height", 1024),
                "num_inference_steps": action.params.get("steps", 4),
                "guidance_scale": action.params.get("guidance", 0.0),
            }
            
            response = await self.message_bus.request("ai.vision.imagegen.request", request, timeout=60.0)
            
            if response.get("error"):
                return ActionResult(
                    action_type=ActionType.IMAGE_GENERATE,
                    timestamp=time.time(),
                    success=False,
                    error=response["error"],
                )
            
            image_path = response.get("image_path", "")
            
            return ActionResult(
                action_type=ActionType.IMAGE_GENERATE,
                timestamp=time.time(),
                success=True,
                details={
                    "image_path": image_path,
                    "prompt": prompt,
                    "width": request["width"],
                    "height": request["height"],
                },
            )
            
        except Exception as e:
            return ActionResult(
                action_type=ActionType.IMAGE_GENERATE,
                timestamp=time.time(),
                success=False,
                error=f"Image generation failed: {e}",
            )
    
    async def _execute_image_save(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute image save to specified location."""
        src_path = action.params.get("src_path")
        dst_path = action.params.get("dst_path")
        
        if not src_path:
            return ActionResult(
                action_type=ActionType.IMAGE_SAVE,
                timestamp=time.time(),
                success=False,
                error="Missing src_path parameter",
            )
        
        if not dst_path:
            return ActionResult(
                action_type=ActionType.IMAGE_SAVE,
                timestamp=time.time(),
                success=False,
                error="Missing dst_path parameter",
            )
        
        try:
            # Expand paths
            src = Path(src_path)
            
            # Check if source exists
            if not src.exists():
                return ActionResult(
                    action_type=ActionType.IMAGE_SAVE,
                    timestamp=time.time(),
                    success=False,
                    error=f"Source image not found: {src_path}",
                )
            
            dst = PathExpander.expand(dst_path, context.working_directory)
            
            # If dst is a directory or looks like one, generate filename
            if dst.is_dir() or dst_path.endswith("/") or not dst.suffix:
                # Make sure directory exists
                dst.mkdir(parents=True, exist_ok=True)
                # Generate filename based on source
                filename = src.name if src.name else f"neuralux_image_{int(time.time())}.png"
                dst = dst / filename
            else:
                # Make sure parent directory exists
                dst.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy image
            success, error = FileOperations.copy_file(src, dst, overwrite=True)
            
            return ActionResult(
                action_type=ActionType.IMAGE_SAVE,
                timestamp=time.time(),
                success=success,
                details={"saved_path": str(dst), "original_path": str(src)},
                error=error,
            )
        except Exception as e:
            return ActionResult(
                action_type=ActionType.IMAGE_SAVE,
                timestamp=time.time(),
                success=False,
                error=f"Failed to save image: {str(e)}",
            )
    
    async def _execute_ocr_capture(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute OCR capture."""
        image_path = action.params.get("image_path")
        region = action.params.get("region")
        language = action.params.get("language")
        
        try:
            request = {}
            if image_path:
                request["image_path"] = image_path
            if region:
                request["region"] = region
            if language:
                request["language"] = language
            
            response = await self.message_bus.request("ai.vision.ocr.request", request, timeout=20.0)
            
            if response.get("error"):
                return ActionResult(
                    action_type=ActionType.OCR_CAPTURE,
                    timestamp=time.time(),
                    success=False,
                    error=response["error"],
                )
            
            ocr_text = response.get("text", "")
            
            return ActionResult(
                action_type=ActionType.OCR_CAPTURE,
                timestamp=time.time(),
                success=True,
                details={"text": ocr_text},
            )
            
        except Exception as e:
            return ActionResult(
                action_type=ActionType.OCR_CAPTURE,
                timestamp=time.time(),
                success=False,
                error=f"OCR failed: {e}",
            )
    
    async def _execute_llm_generate(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute LLM text generation."""
        prompt = action.params.get("prompt")
        system_prompt = action.params.get("system_prompt", "")
        temperature = action.params.get("temperature", 0.3)
        max_tokens = action.params.get("max_tokens", 256)
        use_history = action.params.get("use_history", False)
        
        if not prompt:
            return ActionResult(
                action_type=ActionType.LLM_GENERATE,
                timestamp=time.time(),
                success=False,
                error="Missing prompt parameter",
            )
        
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Include conversation history if requested
            if use_history:
                history = context.get_chat_history(limit=10)
                messages.extend(history)
            
            messages.append({"role": "user", "content": prompt})
            
            request = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            response = await self.message_bus.request("ai.llm.request", request, timeout=30.0)
            
            if response.get("error"):
                return ActionResult(
                    action_type=ActionType.LLM_GENERATE,
                    timestamp=time.time(),
                    success=False,
                    error=response["error"],
                )
            
            content = response.get("content", "")
            
            return ActionResult(
                action_type=ActionType.LLM_GENERATE,
                timestamp=time.time(),
                success=True,
                details={"content": content, "prompt": prompt},
            )
            
        except Exception as e:
            return ActionResult(
                action_type=ActionType.LLM_GENERATE,
                timestamp=time.time(),
                success=False,
                error=f"LLM generation failed: {e}",
            )
    
    async def _execute_command(self, action: Action, context: ConversationContext) -> ActionResult:
        """Execute shell command."""
        command = action.params.get("command")
        stdin_content = action.params.get("stdin")  # Optional stdin content
        
        if not command:
            return ActionResult(
                action_type=ActionType.COMMAND_EXECUTE,
                timestamp=time.time(),
                success=False,
                error="Missing command parameter",
            )
        
        try:
            # Execute command via subprocess
            import subprocess
            
            # If we have stdin content (e.g., for cat > file), provide it
            if stdin_content:
                result = subprocess.run(
                    command,
                    shell=True,
                    input=stdin_content,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=context.working_directory or None,
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=context.working_directory or None,
                )
            
            success = result.returncode == 0
            
            return ActionResult(
                action_type=ActionType.COMMAND_EXECUTE,
                timestamp=time.time(),
                success=success,
                details={
                    "command": command,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                error=result.stderr if not success else None,
            )
            
        except Exception as e:
            return ActionResult(
                action_type=ActionType.COMMAND_EXECUTE,
                timestamp=time.time(),
                success=False,
                error=f"Command execution failed: {e}",
            )

