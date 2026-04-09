from vkbottle import BaseStateGroup


class BotStates(BaseStateGroup):
    """States for multi-step dialog scenarios."""

    # S-ASK: free-text question (Block 4, section 4.4)
    ASK_QUESTION = "ask_question"
