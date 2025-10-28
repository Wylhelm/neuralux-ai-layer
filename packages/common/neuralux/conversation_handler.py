"""Integrated conversation handler that orchestrates multi-step workflows."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Callable
import structlog

from .conversation import ConversationContext, ConversationManager, ActionType
from .orchestrator import ActionOrchestrator, Action, ActionStatus
from .action_planner import ActionPlanner
from .messaging import MessageBusClient

logger = structlog.get_logger(__name__)


class ConversationHandler:
    """
    High-level conversation handler that integrates:
    - Conversation context management
    - Action planning
    - Action orchestration
    - Approval management
    """
    
    def __init__(
        self,
        message_bus: MessageBusClient,
        session_id: str = "default",
        user_id: str = "default",
        approval_callback: Optional[Callable[[Action], bool]] = None,
    ):
        """
        Initialize conversation handler.
        
        Args:
            message_bus: NATS message bus client
            session_id: Session identifier
            user_id: User identifier
            approval_callback: Optional callback for approval requests
        """
        self.message_bus = message_bus
        self.session_id = session_id
        self.user_id = user_id
        
        # Initialize components
        self.conversation_manager = ConversationManager()
        self.action_planner = ActionPlanner(message_bus)
        self.orchestrator = ActionOrchestrator(
            message_bus,
            self.conversation_manager,
            approval_callback,
        )
        
        # Load or create context
        self.context = self.conversation_manager.load(session_id, user_id)
        
        logger.info(
            "conversation_handler_initialized",
            session_id=session_id,
            user_id=user_id,
            turns=len(self.context.turns),
        )
    
    async def process_message(
        self,
        user_input: str,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a user message and execute planned actions.
        
        Args:
            user_input: User's message
            auto_approve: If True, auto-approve all actions (use with caution)
            
        Returns:
            Response dictionary with:
            - type: "success" | "needs_approval" | "error"
            - message: Response message
            - actions: List of action details
            - context_updates: Updated context variables
        """
        logger.info("processing_message", input=user_input[:100])
        
        try:
            # Add user message to context
            self.context.add_turn("user", user_input)
            
            # Plan actions
            actions, explanation = await self.action_planner.plan_actions(
                user_input,
                self.context,
            )
            
            if not actions:
                # No actions planned - just conversation
                response_msg = explanation or "I'm not sure how to help with that."
                self.context.add_turn("assistant", response_msg)
                self.conversation_manager.save(self.context)
                
                return {
                    "type": "success",
                    "message": response_msg,
                    "actions": [],
                    "context_updates": {},
                }
            
            # Check if any actions need approval
            needs_approval_actions = [a for a in actions if a.needs_approval and not auto_approve]
            
            if needs_approval_actions and not auto_approve:
                # Return for approval
                return {
                    "type": "needs_approval",
                    "message": explanation,
                    "actions": [a.to_dict() for a in actions],
                    "pending_actions": actions,  # Store for later execution
                }
            
            # Execute actions
            results = await self._execute_actions(actions, explanation)
            
            return results
            
        except Exception as e:
            logger.error("message_processing_failed", error=str(e))
            return {
                "type": "error",
                "message": f"Failed to process message: {e}",
                "actions": [],
            }
    
    async def approve_and_execute(
        self,
        pending_actions: List[Action],
        approved_indices: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Execute previously planned actions after approval.
        
        Args:
            pending_actions: List of actions awaiting execution
            approved_indices: Indices of approved actions (None = approve all)
            
        Returns:
            Response dictionary
        """
        if approved_indices is None:
            # Approve all
            actions_to_execute = pending_actions
        else:
            # Execute only approved actions
            actions_to_execute = [pending_actions[i] for i in approved_indices if i < len(pending_actions)]
        
        if not actions_to_execute:
            return {
                "type": "cancelled",
                "message": "No actions were approved for execution.",
                "actions": [],
            }
        
        explanation = f"Executing {len(actions_to_execute)} approved action(s)"
        return await self._execute_actions(actions_to_execute, explanation)
    
    async def _execute_actions(
        self,
        actions: List[Action],
        explanation: str,
    ) -> Dict[str, Any]:
        """Execute a list of actions."""
        
        executed_actions = []
        context_updates = {}
        output_chain = {}  # Store outputs for chaining
        
        for i, action in enumerate(actions):
            logger.info(f"executing_action_{i+1}_of_{len(actions)}", action_type=action.action_type.value)
            
            # Handle action chaining - replace placeholders with context variables
            params_str = str(action.params)
            
            # Check for any placeholders (single or double braces)
            if "{" in params_str and "}" in params_str:
                # Replace placeholders in all params
                for key, value in list(action.params.items()):
                    if isinstance(value, str):
                        original_value = value
                        
                        # Replace double-brace placeholders {{var}}
                        if "{{llm_output}}" in value:
                            last_llm_result = None
                            for prev_action in reversed(executed_actions):
                                if prev_action.get("action_type") == ActionType.LLM_GENERATE.value:
                                    last_llm_result = prev_action.get("details", {}).get("content", "")
                                    break
                            if last_llm_result:
                                value = value.replace("{{llm_output}}", last_llm_result)
                        
                        # Replace single-brace placeholders {var} with context variables
                        import re
                        placeholders = re.findall(r'\{([^}]+)\}', value)
                        for placeholder in placeholders:
                            # Check context variables
                            context_value = self.context.get_variable(placeholder)
                            if context_value:
                                value = value.replace(f"{{{placeholder}}}", str(context_value))
                            # Check output chain
                            elif placeholder in output_chain:
                                value = value.replace(f"{{{placeholder}}}", str(output_chain[placeholder]))
                        
                        # Update param if changed
                        if value != original_value:
                            action.params[key] = value
            
            # Special handling for command_execute that needs to write generated content
            if action.action_type == ActionType.COMMAND_EXECUTE:
                command = action.params.get("command", "")
                # If this command writes to a file and we have LLM output, provide it via stdin
                if (">" in command or "cat" in command.lower()) and "llm_output" in output_chain:
                    # Remove the hardcoded content from echo commands
                    import re
                    if command.startswith("echo "):
                        # Replace echo with cat for stdin piping
                        # Extract the filename after >
                        filename_match = re.search(r'>\s*(.+)$', command)
                        if filename_match:
                            filename = filename_match.group(1).strip()
                            action.params["command"] = f"cat > {filename}"
                            action.params["stdin"] = output_chain["llm_output"]
                    elif "cat >" in command:
                        # Already using cat, just add stdin
                        action.params["stdin"] = output_chain["llm_output"]
            
            # Execute action
            result = await self.orchestrator.execute_action(action, self.context)
            
            # Store result
            executed_action = {
                "action_type": action.action_type.value,
                "description": action.description,
                "success": result.success,
                "details": result.details,
                "error": result.error,
            }
            executed_actions.append(executed_action)
            
            # Track outputs for chaining
            if result.success:
                if action.action_type == ActionType.LLM_GENERATE:
                    output_chain["llm_output"] = result.details.get("content", "")
                elif action.action_type == ActionType.IMAGE_GENERATE:
                    output_chain["image_path"] = result.details.get("image_path", "")
            
            # Update context updates dict for response
            context_updates.update(self.context.variables)
            
            # If action failed and it's critical, stop execution
            if not result.success and action.needs_approval:
                logger.warning("critical_action_failed", action_type=action.action_type.value)
                break
        
        # Build response message
        success_count = sum(1 for a in executed_actions if a["success"])
        
        if success_count == 0:
            response_message = f"Failed to execute actions: {executed_actions[0].get('error', 'Unknown error')}"
            response_type = "error"
        elif success_count < len(actions):
            response_message = f"Partially completed: {success_count}/{len(actions)} actions succeeded."
            response_type = "partial_success"
        else:
            # For LLM_GENERATE actions, use the actual generated content as the message
            if len(executed_actions) == 1 and executed_actions[0].get("action_type") == "llm_generate":
                # Get the actual LLM response content
                response_message = executed_actions[0].get("details", {}).get("content", "")
                if not response_message:
                    response_message = self.context.get_variable("last_generated_text", "Response generated successfully.")
            else:
                # Build detailed success message for other actions
                if len(executed_actions) == 1:
                    action_desc = executed_actions[0].get("description", "Action")
                    response_message = f"{action_desc} completed successfully."
                else:
                    response_message = f"Completed {len(executed_actions)} actions successfully."
            
            response_type = "success"
        
        # Add assistant response to context
        self.context.add_turn("assistant", response_message)
        
        # Save context
        self.conversation_manager.save(self.context)
        
        return {
            "type": response_type,
            "message": response_message,
            "actions": executed_actions,
            "context_updates": context_updates,
        }
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history."""
        turns = self.context.turns[-limit:] if limit else self.context.turns
        
        history = []
        for turn in turns:
            item = {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp,
            }
            
            if turn.action_result:
                item["action"] = {
                    "type": turn.action_result.action_type.value,
                    "success": turn.action_result.success,
                    "details": turn.action_result.details,
                }
            
            history.append(item)
        
        return history
    
    def reset_conversation(self):
        """Reset the conversation context."""
        self.conversation_manager.reset(self.session_id)
        self.context = self.conversation_manager.load(self.session_id, self.user_id)
        logger.info("conversation_reset", session_id=self.session_id)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current context."""
        return {
            "session_id": self.context.session_id,
            "turn_count": len(self.context.turns),
            "variables": dict(self.context.variables),
            "working_directory": self.context.working_directory,
            "last_updated": self.context.updated_at,
        }

