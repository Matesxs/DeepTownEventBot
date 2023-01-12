import asyncio
import disnake
from disnake.ext import commands
from Levenshtein import ratio

from utils import message_utils, string_manipulation, permission_helper
from database import questions_and_answers_repo
from config import config, cooldowns
from utils.logger import setup_custom_logger
from features.base_cog import Base_Cog
from features.modals.question_and_answer import CreateQuestionAndAnswer
from features.views.paginator import EmbedView
from config.strings import Strings

logger = setup_custom_logger(__name__)

def getApproximateAnswer(q):
  max_score = 0
  answer_id = None
  ref_question = None

  questions = questions_and_answers_repo.all_questions_iterator()

  for ans_id, question in questions:
    score = ratio(question, q)
    if score >= 0.9:
      return question, questions_and_answers_repo.get_answer_by_id(ans_id), score
    elif score > max_score:
      max_score = score
      answer_id = ans_id
      ref_question = question

  if answer_id is not None and (max_score * 100) > config.questions_and_answers.score_limit:
    return ref_question, questions_and_answers_repo.get_answer_by_id(answer_id), max_score
  return None

class AutoHelp(Base_Cog):
  def __init__(self, bot):
    super(AutoHelp, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    if message.guild is None: return
    if message.author.bot or message.author.system: return
    if message.content == "" or message.content.startswith(config.base.command_prefix): return
    if not "?" in message.content: return
    if not questions_and_answers_repo.is_on_whitelist(message.guild.id, message.channel.id): return

    answer_object = getApproximateAnswer(message.content)
    if answer_object is None: return

    ref_question, answer, score = answer_object

    # logger.info(f"Found answer for users question: `{message.content}`\nReference question: `{ref_question}`\nAnswer: `{answer}` with score `{score}`")

    final_reply_string_lines = str(Strings.questions_and_answers_repond_format(question=ref_question, answer=answer)).split("\n")
    while final_reply_string_lines:
      reply_string, final_reply_string_lines = string_manipulation.add_string_until_length(final_reply_string_lines, 1900, "\n")
      await message.reply(reply_string)
      await asyncio.sleep(0.01)

  @commands.slash_command(name="question_and_answer")
  async def question_and_answer(self, inter: disnake.CommandInteraction):
    pass

  @question_and_answer.sub_command(name="add", description=Strings.questions_and_answers_add_description)
  @commands.is_owner()
  async def add_question_and_answer(self, inter: disnake.CommandInteraction):
    await inter.response.send_modal(modal=CreateQuestionAndAnswer())

  @question_and_answer.sub_command(name="modify", description=Strings.questions_and_answers_modify_description)
  @commands.is_owner()
  async def modify_question_and_answer(self, inter: disnake.CommandInteraction,
                                       question_id: int=commands.Param(description=Strings.questions_and_answers_id_param_description)):
    question_and_answer = questions_and_answers_repo.get_question_and_answer(question_id)
    if question_and_answer is None:
      return await message_utils.generate_error_message(inter, Strings.questions_and_answers_not_found)
    await inter.response.send_modal(modal=CreateQuestionAndAnswer(question_and_answer.question, question_and_answer.answer))

  @question_and_answer.sub_command(name="remove", description=Strings.questions_and_answers_remove_description)
  @commands.is_owner()
  async def remove_question_and_answer(self, inter: disnake.CommandInteraction,
                                       question_id: int=commands.Param(description=Strings.questions_and_answers_id_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)
    if questions_and_answers_repo.remove_question(question_id):
      await message_utils.generate_success_message(inter, Strings.questions_and_answers_remove_removed)
    else:
      await message_utils.generate_error_message(inter, Strings.questions_and_answers_not_found)

  @remove_question_and_answer.autocomplete("question_id")
  async def remove_question_and_answer_question_id_autocomplete(self, _, string: str):
    question_ids = questions_and_answers_repo.get_all_ids()
    if string is None or not string:
      return question_ids[:25]
    return [id_ for id_ in question_ids if string.lower() in str(id_)][:25]

  @question_and_answer.sub_command(name="list", description=Strings.questions_and_answers_list_description)
  @cooldowns.default_cooldown
  async def question_and_answer_list(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)
    question_objects = questions_and_answers_repo.get_all()

    question_answer_pairs = [f"**ID:** {question_object.id}\n**Question:** {question_object.question}\n**Answer:** {question_object.answer}\n" for question_object in question_objects]

    pages = []
    while question_answer_pairs:
      embed = disnake.Embed(title="Q&A List", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      output, question_answer_pairs = string_manipulation.add_string_until_length(question_answer_pairs, 4000, "\n")
      embed.description = output.strip()
      pages.append(embed)

    if pages:
      await EmbedView(inter.author, pages).run(inter)
    else:
      await message_utils.generate_error_message(inter, Strings.questions_and_answers_list_no_results)

  @question_and_answer.sub_command_group(name="whitelist")
  @commands.guild_only()
  @commands.check(permission_helper.is_discord_guild_owner)
  @cooldowns.default_cooldown
  async def question_and_answer_whitelist(self, inter: disnake.CommandInteraction):
    pass

  @question_and_answer_whitelist.sub_command(name="add", description=Strings.questions_and_answers_whitelist_add_description)
  async def whitelist_add(self, inter: disnake.CommandInteraction,
                          channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if questions_and_answers_repo.add_to_whitelist(inter.guild, channel.id):
      return await message_utils.generate_success_message(inter, Strings.questions_and_answers_whitelist_add_success(channel=channel.name))
    await message_utils.generate_error_message(inter, Strings.questions_and_answers_whitelist_add_failed(channel=channel.name))

  @question_and_answer_whitelist.sub_command(name="remove", description=Strings.questions_and_answers_whitelist_remove_description)
  async def whitelist_remove(self, inter: disnake.CommandInteraction,
                             channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if questions_and_answers_repo.remove_from_whitelist(inter.guild_id, channel.id):
      return await message_utils.generate_success_message(inter, Strings.questions_and_answers_whitelist_remove_success(channel=channel.name))
    await message_utils.generate_error_message(inter, Strings.questions_and_answers_whitelist_remove_failed(channel=channel.name))

def setup(bot):
  bot.add_cog(AutoHelp(bot))
