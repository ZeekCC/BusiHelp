"""会话存储：进程内历史 + token 预算裁剪。"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages


class SessionStore:
    def __init__(self, token_budget: int) -> None:
        self._token_budget = token_budget
        self._sessions: dict[str, list[BaseMessage]] = {}

    def history(self, session_id: str) -> list[BaseMessage]:
        return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, user_text: str, ai_text: str) -> None:
        messages = self._sessions.setdefault(session_id, [])
        messages.append(HumanMessage(content=user_text))
        messages.append(AIMessage(content=ai_text))
        self._sessions[session_id] = self._trim(messages)

    def _trim(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        return trim_messages(
            messages,
            max_tokens=self._token_budget,
            token_counter=count_tokens_approximately,
            strategy="last",
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
