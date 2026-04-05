from vkbottle import BaseStateGroup


class BotStates(BaseStateGroup):
    """States for multi-step dialog scenarios."""

    # S-70: HR request — 6-step dialog
    HR_REQUEST_NAME = "hr_name"
    HR_REQUEST_TOPIC = "hr_topic"
    HR_REQUEST_DETAILS = "hr_details"
    HR_REQUEST_ENTITY = "hr_entity"
    HR_REQUEST_URGENCY = "hr_urgency"
    HR_REQUEST_CONFIRM = "hr_confirm"

    # S-ASK: free-text question (Block 4, section 4.4)
    ASK_QUESTION = "ask_question"
