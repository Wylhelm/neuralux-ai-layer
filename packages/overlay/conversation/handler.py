"""Overlay-specific conversation handler wrapper."""

import asyncio
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import structlog
import threading

from gi.repository import GLib

from neuralux.conversation_handler import ConversationHandler
from neuralux.messaging import MessageBusClient
from neuralux.config import NeuraluxConfig
from neuralux.memory import default_session_id

logger = structlog.get_logger(__name__)

# Global event loop for async operations (shared across all handler instances)
_async_loop = None
_loop_thread = None
_loop_lock = threading.Lock()


class OverlayConversationHandler:
    """
    GTK-friendly wrapper around ConversationHandler.
    
    Handles async operations in a way that's compatible with GTK's event loop
    and provides callbacks for UI updates.
    """
    
    def __init__(
        self,
        message_bus: MessageBusClient,
        session_id: Optional[str] = None,
        user_id: str = "overlay_user",
        on_approval_needed: Optional[Callable] = None,
        on_action_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        """
        Initialize the overlay conversation handler.
        
        Args:
            message_bus: Connected message bus client
            session_id: Session identifier (defaults to user@hostname:overlay)
            user_id: User identifier
            on_approval_needed: Callback when actions need approval
            on_action_complete: Callback when an action completes
            on_error: Callback for errors
        """
        self.message_bus = message_bus
        self.session_id = session_id or f"{default_session_id()}:overlay"
        self.user_id = user_id
        
        # UI callbacks
        self.on_approval_needed = on_approval_needed
        self.on_action_complete = on_action_complete
        self.on_error = on_error
        
        # Pending approval actions
        self._pending_actions = None
        self._approval_future = None
        
        # Core conversation handler (will be created lazily in async context)
        # We ALWAYS create the handler lazily to ensure message bus is created
        # in the correct event loop (the dedicated async thread, not the main GTK loop)
        self.handler = None
        
        logger.info("Overlay conversation handler will create own message bus in async context", session_id=self.session_id)
    
    async def _ensure_handler_initialized(self):
        """
        Ensure conversation handler is initialized in the async context.
        
        This creates a new message bus in the current event loop if needed.
        """
        if self.handler is None:
            logger.info("Creating message bus in async context")
            from neuralux import MessageBusClient, NeuraluxConfig
            
            # Create fresh message bus in this event loop
            bus = MessageBusClient(NeuraluxConfig())
            await bus.connect()
            
            # Create conversation handler with the new bus
            self.handler = ConversationHandler(
                message_bus=bus,
                session_id=self.session_id,
                user_id=self.user_id,
                approval_callback=self._handle_approval_request,
            )
            logger.info("Conversation handler created in async context", session_id=self.session_id)
    
    def _handle_approval_request(self, action) -> bool:
        """
        Handle approval request from conversation handler.
        
        This is called from async context, so we need to coordinate with GTK.
        For now, we'll use a simple synchronous approach.
        """
        # For synchronous flow, we return True by default
        # The overlay will show approval UI and user can approve/deny
        return True
    
    @staticmethod
    def _get_event_loop():
        """Get or create the shared event loop for async operations."""
        global _async_loop, _loop_thread
        
        with _loop_lock:
            if _async_loop is None or _loop_thread is None or not _loop_thread.is_alive():
                # Create new event loop in dedicated thread
                loop_ready = threading.Event()
                
                def _run_loop():
                    global _async_loop
                    _async_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(_async_loop)
                    loop_ready.set()
                    try:
                        _async_loop.run_forever()
                    finally:
                        try:
                            _async_loop.close()
                        except:
                            pass
                        _async_loop = None
                
                _loop_thread = threading.Thread(target=_run_loop, daemon=True)
                _loop_thread.start()
                loop_ready.wait(timeout=5.0)
                
            return _async_loop

    @staticmethod
    def _reset_event_loop():
        """Stop and clear the shared event loop to recover from stuck state."""
        global _async_loop, _loop_thread
        with _loop_lock:
            try:
                if _async_loop is not None:
                    try:
                        _async_loop.call_soon_threadsafe(_async_loop.stop)
                    except Exception:
                        pass
            finally:
                # Best-effort join
                try:
                    if _loop_thread is not None and _loop_thread.is_alive():
                        _loop_thread.join(timeout=2.0)
                except Exception:
                    pass
                _async_loop = None
                _loop_thread = None
    
    def _run_async(self, coro):
        """
        Run an async coroutine and return the result.
        
        Uses a dedicated event loop thread to avoid conflicts with GTK.
        """
        loop = self._get_event_loop()
        if loop is None:
            raise RuntimeError("Could not get event loop")
        
        # Use asyncio.run_coroutine_threadsafe to execute in the loop thread
        future = asyncio.run_coroutine_threadsafe(
            asyncio.wait_for(coro, timeout=25.0),
            loop
        )
        
        try:
            # Wait for result with timeout
            return future.result(timeout=30.0)
        except TimeoutError:
            logger.error("Async operation timed out - resetting conversational event loop")
            future.cancel()
            # Force-reset loop to recover on next call
            self._reset_event_loop()
            raise TimeoutError("Operation timed out")
    
    async def _process_message_internal(self, user_input: str):
        """Internal coroutine that ensures handler is initialized before processing."""
        await self._ensure_handler_initialized()
        return await self.handler.process_message(user_input)
    
    def process_message_async(self, user_input: str, callback: Callable):
        """
        Process a user message asynchronously and call callback with result.
        
        This runs in a background thread to avoid blocking the GTK main loop.
        
        Args:
            user_input: The user's message
            callback: Function to call with (result_dict, error) when complete
        """
        import threading
        
        def _worker():
            try:
                logger.info("Processing message", input=user_input[:50])
                
                # Run with lazy initialization
                result = self._run_async(self._process_message_internal(user_input))
                logger.info("Message processed successfully", result_type=result.get("type"))
                # Call callback in main thread
                GLib.idle_add(lambda r=result: callback(r, None) or False)
                        
            except TimeoutError as timeout_err:
                logger.error("Message processing timed out", error=str(timeout_err))
                GLib.idle_add(lambda err=timeout_err: callback(None, err) or False)
            except Exception as exc:
                logger.error("Error processing message", error=str(exc), exc_info=True)
                GLib.idle_add(lambda err=exc: callback(None, err) or False)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
    
    async def _approve_and_execute_internal(self):
        """Internal coroutine that ensures handler is initialized before executing."""
        await self._ensure_handler_initialized()
        
        # Use the pending actions that were stored
        if self._pending_actions is None:
            raise ValueError("No pending actions to execute")
        
        # Convert dict actions to Action objects if needed
        from neuralux.orchestrator import Action, ActionStatus
        from neuralux.conversation import ActionType
        
        actions_list = []
        for action_data in self._pending_actions:
            if isinstance(action_data, dict):
                # Convert dict to Action object
                action_type_str = action_data.get("action_type", "")
                action_type = ActionType(action_type_str) if action_type_str else ActionType.LLM_GENERATE
                
                action = Action(
                    action_type=action_type,
                    params=action_data.get("params", {}),
                    status=ActionStatus.APPROVED,
                    needs_approval=action_data.get("needs_approval", True),
                    description=action_data.get("description", ""),
                )
                actions_list.append(action)
            else:
                # Already an Action object
                actions_list.append(action_data)
        
        return await self.handler.approve_and_execute(
            pending_actions=actions_list
        )
    
    def approve_and_execute_async(self, callback: Callable):
        """
        Approve and execute pending actions asynchronously.
        
        Args:
            callback: Function to call with (result_dict, error) when complete
        """
        import threading
        
        def _worker():
            try:
                logger.info("Executing approved actions")
                
                # Run with lazy initialization
                result = self._run_async(self._approve_and_execute_internal())
                logger.info("Actions executed successfully")
                GLib.idle_add(lambda r=result: callback(r, None) or False)
                        
            except TimeoutError as timeout_err:
                logger.error("Action execution timed out", error=str(timeout_err))
                GLib.idle_add(lambda err=timeout_err: callback(None, err) or False)
            except Exception as exc:
                logger.error("Error executing actions", error=str(exc), exc_info=True)
                GLib.idle_add(lambda err=exc: callback(None, err) or False)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
    
    def cancel_pending_actions(self):
        """Cancel any pending actions awaiting approval."""
        try:
            # Clear handler's pending actions
            if self.handler:
                self.handler._pending_actions = None
            self._pending_actions = None
            logger.info("Cancelled pending actions")
        except Exception as e:
            logger.error("Error cancelling actions", error=str(e))
    
    def get_conversation_history(self) -> list:
        """
        Get conversation history.
        
        Returns:
            List of conversation turns with role, content, and timestamp
        """
        if self.handler is None:
            return []
        
        try:
            # Access the handler's conversation context directly
            return self.handler.conversation.turns if self.handler.conversation else []
        except Exception as e:
            logger.error("Error getting history", error=str(e))
            return []
    
    def get_context_variables(self) -> Dict[str, Any]:
        """
        Get current context variables.
        
        Returns:
            Dictionary of context variable names to values
        """
        if self.handler is None:
            return {}
        
        try:
            # Access the handler's conversation context directly
            return self.handler.conversation.variables if self.handler.conversation else {}
        except Exception as e:
            logger.error("Error getting context", error=str(e))
            return {}
    
    def reset_conversation(self):
        """Reset the conversation context."""
        try:
            if self.handler is None:
                # Handler not initialized yet - just log and return
                logger.info("Conversation reset (handler not yet initialized)")
                return
            
            # reset_conversation() is synchronous, not async - just call it directly
            self.handler.reset_conversation()
            logger.info("Conversation reset")

            # Cleanly disconnect handler bus (async) and drop handler, then reset loop
            try:
                async def _shutdown_internal():
                    try:
                        bus = getattr(self.handler, "message_bus", None)
                        if bus is not None and getattr(bus, "nc", None) is not None:
                            await bus.disconnect()
                    except Exception:
                        pass
                try:
                    self._run_async(_shutdown_internal())
                except Exception:
                    pass
            finally:
                self._pending_actions = None
                self._approval_future = None
                self.handler = None
                # Ensure subsequent calls start with a fresh loop if needed
                self._reset_event_loop()
        except Exception as e:
            logger.error("Error resetting conversation", error=str(e), exc_info=True)
    
    def format_result_for_display(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a result dictionary for display in the UI.
        
        Args:
            result: Result from conversation handler
            
        Returns:
            Formatted result with display-friendly fields
        """
        result_type = result.get("type", "unknown")
        
        if result_type == "needs_approval":
            actions = result.get("actions", [])
            return {
                "type": "needs_approval",
                "message": result.get("message", "Actions need approval"),
                "actions": actions,
                "approval_count": len([a for a in actions if a.get("needs_approval", False)]),
                "total_count": len(actions),
            }
        
        elif result_type == "response":
            return {
                "type": "response",
                "message": result.get("message", result.get("content", "")),
                # Normalize to actions_executed for the UI
                "actions_executed": result.get("actions_executed") or result.get("actions", []),
                "success": result.get("success", True),
            }
        
        elif result_type == "error":
            return {
                "type": "error",
                "message": result.get("message", "An error occurred"),
                "error": result.get("error", "Unknown error"),
            }
        
        return result
    
    @property
    def session_info(self) -> Dict[str, Any]:
        """Get session information for display."""
        try:
            # Avoid awaiting None. Use handler context directly if available.
            if self.handler and getattr(self.handler, "context", None) is not None:
                ctx = self.handler.context
                return {
                    "session_id": self.session_id,
                    "turn_count": len(getattr(ctx, "turns", []) or []),
                    "variables": len(getattr(ctx, "variables", {}) or {}),
                    "has_context": bool(getattr(ctx, "variables", {}) or {}),
                }
        except Exception:
            pass

        return {
            "session_id": self.session_id,
            "turn_count": 0,
            "variables": 0,
            "has_context": False,
        }

