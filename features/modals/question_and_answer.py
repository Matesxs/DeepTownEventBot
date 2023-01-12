import disnake
from typing import Optional

from utils import message_utils
from database import questions_and_answers_repo
from config.strings import Strings

class CreateQuestionAndAnswer(disnake.ui.Modal):
  def __init__(self, default_question: Optional[str]=None, default_answer: Optional[str]=None):
    components = [
      disnake.ui.TextInput(label="Question", custom_id="q_and_a:question", value=default_question, required=True, max_length=5000, placeholder="Place here your question", style=disnake.TextInputStyle.multi_line),
      disnake.ui.TextInput(label="Answer", custom_id="q_and_a:answer", value=default_answer, required=True, max_length=5000, placeholder="Place here your answer", style=disnake.TextInputStyle.multi_line)
    ]
    super(CreateQuestionAndAnswer, self).__init__(title="Create Question and Answer", custom_id="q_and_a_create", timeout=600, components=components)

  async def callback(self, interaction: disnake.ModalInteraction) -> None:
    if questions_and_answers_repo.create_question_and_answer(interaction.text_values["q_and_a:question"], interaction.text_values["q_and_a:answer"]) is None:
      return await message_utils.generate_error_message(interaction, Strings.questions_and_answers_add_failed)
    await message_utils.generate_success_message(interaction, Strings.questions_and_answers_add_added)
